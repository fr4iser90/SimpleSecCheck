"""
Scanner Worker Service
Pulls jobs from queue and executes scans
"""

import os
import asyncio
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.database import get_database
from app.services.queue_service import get_queue_service
from app.services.step_service import initialize_step_tracking, initialize_steps_log, derive_project_name, write_step_to_log


class ScannerWorker:
    """Worker that processes scan jobs from queue"""
    
    def __init__(self):
        self.db = get_database()
        self.max_concurrent_scans = int(os.getenv("MAX_CONCURRENT_SCANS", "1"))
        self.running_scans: Dict[str, asyncio.Task] = {}
        self.running_runners: Dict[str, Any] = {}  # {scan_id: DockerRunner} - track runners for cleanup
        self.is_running = False
        self.worker_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize database connection (idempotent - uses shared connection pool)"""
        # Database is already initialized by Session/Queue services in startup event
        # This is just to ensure it's ready (idempotent call)
        await self.db.initialize()
    
    async def close(self):
        """Stop worker and close database connection"""
        await self.stop()
        await self.db.close()
    
    async def start(self):
        """Start the worker"""
        if self.is_running:
            return
        
        # Database is already initialized by Session/Queue services in startup event
        # Just ensure it's ready (idempotent call)
        await self.db.initialize()
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        print("[Scanner Worker] Worker loop started")
    
    async def stop(self):
        """Stop the worker"""
        self.is_running = False
        
        # Stop all running docker-compose processes
        print(f"[Scanner Worker] Stopping {len(self.running_runners)} running scan(s)...")
        for scan_id, runner in self.running_runners.items():
            if runner and runner.process and runner.process.returncode is None:
                print(f"[Scanner Worker] Stopping docker-compose process for scan {scan_id}...")
                try:
                    runner.process.terminate()
                    await asyncio.wait_for(runner.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    print(f"[Scanner Worker] Force killing docker-compose process for scan {scan_id}...")
                    runner.process.kill()
                    await runner.process.wait()
                except Exception as e:
                    print(f"[Scanner Worker] Error stopping process for scan {scan_id}: {e}")
        
        # Stop all Docker containers from running scans
        from app.services.container_service import stop_running_containers
        for scan_id in list(self.running_scans.keys()):
            # Create dummy current_scan dict for stop_running_containers
            current_scan = {"container_ids": []}
            stopped = stop_running_containers(current_scan)
            if stopped:
                print(f"[Scanner Worker] Stopped {len(stopped)} container(s) for scan {scan_id}")
        
        # Cancel all running scan tasks
        if self.running_scans:
            for scan_id, task in self.running_scans.items():
                if not task.done():
                    print(f"[Scanner Worker] Cancelling scan task {scan_id}...")
                    task.cancel()
            # Wait for tasks to complete (with timeout)
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.running_scans.values(), return_exceptions=True),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                print("[Scanner Worker] Timeout waiting for scan tasks to complete")
        
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
    
    async def _check_and_reset_stuck_jobs(self):
        """Check for stuck jobs (running but no active task) and reset them to pending"""
        try:
            # Get all running jobs from database
            all_jobs = await self.db.get_queue(limit=1000)
            running_jobs = [job for job in all_jobs if job.get("status") == "running"]
            
            if not running_jobs:
                return
            
            # Check which running jobs are actually stuck (not in self.running_scans)
            stuck_jobs = []
            for job in running_jobs:
                queue_id = job.get("queue_id")
                if queue_id and queue_id not in self.running_scans:
                    # Check if job is older than 5 minutes (stuck)
                    started_at = job.get("started_at")
                    if started_at:
                        try:
                            if isinstance(started_at, str):
                                # PostgreSQL returns ISO format strings
                                started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                            # Remove timezone for comparison
                            if started_at.tzinfo:
                                started_at = started_at.replace(tzinfo=None)
                            age_minutes = (datetime.utcnow() - started_at).total_seconds() / 60
                            if age_minutes > 2:  # Stuck if older than 2 minutes (reduced from 5 for faster recovery)
                                stuck_jobs.append(job)
                        except (ValueError, AttributeError) as e:
                            print(f"[Scanner Worker] Error parsing started_at for job {queue_id}: {e}")
                    else:
                        # No started_at means it was set to running but never actually started
                        # Check created_at instead
                        created_at = job.get("created_at")
                        if created_at:
                            try:
                                if isinstance(created_at, str):
                                    # PostgreSQL returns ISO format strings
                                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                # Remove timezone for comparison
                                if created_at.tzinfo:
                                    created_at = created_at.replace(tzinfo=None)
                                age_minutes = (datetime.utcnow() - created_at).total_seconds() / 60
                                if age_minutes > 2:  # Stuck if older than 2 minutes (reduced from 5 for faster recovery)
                                    stuck_jobs.append(job)
                            except (ValueError, AttributeError) as e:
                                print(f"[Scanner Worker] Error parsing created_at for job {queue_id}: {e}")
            
            # Reset stuck jobs to pending
            if stuck_jobs:
                print(f"[Scanner Worker] Found {len(stuck_jobs)} stuck job(s), resetting to pending...")
                for job in stuck_jobs:
                    queue_id = job.get("queue_id")
                    print(f"[Scanner Worker] Resetting stuck job: queue_id={queue_id}, repository={job.get('repository_url', 'unknown')}")
                    await self.db.update_queue_status(
                        queue_id=queue_id,
                        status="pending",
                    )
        except Exception as e:
            print(f"[Scanner Worker] Error checking stuck jobs: {e}")
            import traceback
            traceback.print_exc()
    
    async def _worker_loop(self):
        """Main worker loop - continuously polls queue for jobs"""
        import time
        last_log_time = 0
        last_stuck_check = 0
        print("[Scanner Worker] Worker loop started and running")
        while self.is_running:
            try:
                # Check for stuck jobs every 15 seconds (more frequent for faster recovery)
                current_time = time.time()
                if current_time - last_stuck_check >= 15:
                    await self._check_and_reset_stuck_jobs()
                    last_stuck_check = current_time
                
                # Check if we can start more scans
                if len(self.running_scans) < self.max_concurrent_scans:
                    # Get next job from queue
                    job = await self.db.get_next_queue_item()
                    
                    if job:
                        print(f"[Scanner Worker] Found job: {job['queue_id']} for {job.get('repository_url', 'unknown')} (status: {job.get('status', 'unknown')})")
                        # Start scan task with error handling
                        async def process_with_error_handling(job):
                            try:
                                await self._process_scan_job(job)
                            except Exception as e:
                                print(f"[Scanner Worker] CRITICAL: Task failed for {job.get('queue_id', 'unknown')}: {e}")
                                import traceback
                                traceback.print_exc()
                                # Update status to failed
                                try:
                                    await self.db.update_queue_status(
                                        queue_id=job.get('queue_id'),
                                        status="failed",
                                        completed_at=datetime.utcnow(),
                                    )
                                except Exception as db_error:
                                    print(f"[Scanner Worker] Failed to update queue status: {db_error}")
                        
                        task = asyncio.create_task(process_with_error_handling(job))
                        self.running_scans[job["queue_id"]] = task
                    else:
                        # No jobs available, wait a bit
                        # Log every 10 seconds to avoid spam
                        if current_time - last_log_time >= 10:
                            queue_length = await self.db.get_queue_length()
                            pending_count = len([s for s in await self.db.get_queue(limit=1000) if s.get("status") == "pending"])
                            running_count = len([s for s in await self.db.get_queue(limit=1000) if s.get("status") == "running"])
                            print(f"[Scanner Worker] No pending jobs found (queue length: {queue_length}, pending: {pending_count}, running in DB: {running_count}, running tasks: {len(self.running_scans)})")
                            if len(self.running_scans) > 0:
                                for queue_id, task in self.running_scans.items():
                                    print(f"[Scanner Worker] Active task: queue_id={queue_id}, done={task.done()}")
                            last_log_time = current_time
                        await asyncio.sleep(1)
                else:
                    # Max concurrent scans reached, wait
                    await asyncio.sleep(1)
                
                # Clean up completed tasks
                completed = [
                    queue_id for queue_id, task in self.running_scans.items()
                    if task.done()
                ]
                for queue_id in completed:
                    print(f"[Scanner Worker] Scan {queue_id} completed, cleaning up")
                    del self.running_scans[queue_id]
                
            except Exception as e:
                print(f"[Scanner Worker] Error in worker loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_scan_job(self, job: Dict[str, Any]):
        """Process a single scan job"""
        # Add immediate logging and validation
        print(f"[Scanner Worker] _process_scan_job called with job: {job}")
        
        if not job:
            print(f"[Scanner Worker] ERROR: job is None or empty")
            raise ValueError("Job is None or empty")
        
        queue_id = job.get("queue_id")
        if not queue_id:
            print(f"[Scanner Worker] ERROR: No queue_id in job: {job}")
            raise ValueError(f"No queue_id in job: {job}")
        
        repository_url = job.get("repository_url")
        if not repository_url:
            print(f"[Scanner Worker] ERROR: No repository_url in job: {job}")
            raise ValueError(f"No repository_url in job: {job}")
        
        branch = job.get("branch")
        commit_hash = job.get("commit_hash")
        selected_scanners = job.get("selected_scanners")  # List of scanner names to run
        finding_policy = job.get("finding_policy")
        
        print(f"[Scanner Worker] Processing job {queue_id} for {repository_url}")
        if selected_scanners:
            print(f"[Scanner Worker] Selected scanners: {selected_scanners}")
        else:
            print(f"[Scanner Worker] No selected scanners - will run all scanners")
        
        try:
            # Generate scan_id BEFORE starting scan (so frontend can find logs immediately)
            from datetime import datetime
            scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Update status to running AND set scan_id immediately
            await self.db.update_queue_status(
                queue_id=queue_id,
                status="running",
                scan_id=scan_id,  # Set scan_id immediately so frontend can find logs
                started_at=datetime.utcnow(),
            )
            print(f"[Scanner Worker] Updated job {queue_id} status to running with scan_id={scan_id}")
            
            # Execute scan (uses the scan_id we just generated)
            print(f"[Scanner Worker] Starting scan execution for {queue_id} (scan_id={scan_id})")
            scan_result = await self._execute_scan(
                repository_url=repository_url,
                branch=branch,
                commit_hash=commit_hash,
                scan_id=scan_id,  # Pass scan_id to _execute_scan
                selected_scanners=selected_scanners,  # Pass selected scanners
                finding_policy=finding_policy,
            )
            actual_scan_id = scan_result["scan_id"]
            results_dir_name = scan_result["results_dir"]
            print(f"[Scanner Worker] Scan execution completed: scan_id={actual_scan_id}")
            
            # Update status to completed (scan_id should already be set, but update just in case)
            await self.db.update_queue_status(
                queue_id=queue_id,
                status="completed",
                scan_id=actual_scan_id or scan_id,  # Use actual_scan_id if different
                completed_at=datetime.utcnow(),
                results_dir=results_dir_name,
            )

            # Grant access to scan owner
            await self.db.add_scan_access(actual_scan_id or scan_id, job.get("session_id"))
            
        except Exception as e:
            print(f"[Scanner Worker] Error processing job {queue_id}: {e}")
            
            # Update status to failed
            await self.db.update_queue_status(
                queue_id=queue_id,
                status="failed",
                completed_at=datetime.utcnow(),
            )
    
    async def _execute_scan(
        self,
        repository_url: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        scan_id: Optional[str] = None,
        selected_scanners: Optional[List[str]] = None,
        finding_policy: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Execute scan using docker_runner.py
        Returns scan_id
        """
        import sys
        sys.path.insert(0, "/app/scanner")
        from core.path_setup import (
            get_webui_base_dir, 
            get_webui_results_dir, 
            get_results_dir_for_scan,
        )
        from app.services.git_service import clone_repository, is_git_url
        
        # Get paths - ALL FROM CENTRAL path_setup.py
        base_dir = get_webui_base_dir()
        results_dir = get_webui_results_dir()
        
        # Use provided scan_id or generate new one
        if not scan_id:
            scan_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Create a minimal current_scan dict for git_service and step tracking
        current_scan = {
            "scan_id": scan_id,
            "step_counter": 0,
            "step_names": {},
        }
        
        # Initialize step tracking for frontend display (sets process_output_lock)
        initialize_step_tracking(current_scan)
        
        # Get results directory path BEFORE cloning (needed for log_step in git_service)
        project_name = derive_project_name(repository_url)
        results_dir_path = get_results_dir_for_scan(project_name, scan_id)
        results_dir_path_obj = Path(results_dir_path)
        
        # Initialize steps.log BEFORE Git clone (so log_step can write to it)
        initialize_steps_log(scan_id, results_dir_path, current_scan, repository_url)
        
        # Clone repository if it's a Git URL
        temp_clone_path = None
        actual_commit_hash = commit_hash
        
        if is_git_url(repository_url):
            try:
                temp_clone_path = await clone_repository(
                    repository_url,
                    base_dir,
                    scan_id,
                    current_scan,
                    results_dir,
                    branch,
                )
                
                # Extract commit hash from cloned repository
                if not actual_commit_hash and temp_clone_path:
                    try:
                        result = await asyncio.create_subprocess_exec(
                            "git", "rev-parse", "HEAD",
                            cwd=str(temp_clone_path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        stdout, _ = await result.communicate()
                        if result.returncode == 0:
                            actual_commit_hash = stdout.decode().strip()
                            print(f"[Scanner Worker] Extracted commit hash: {actual_commit_hash}")
                    except Exception as e:
                        print(f"[Scanner Worker] Failed to extract commit hash: {e}")
                
                # Use cloned path for scan
                target_path = str(temp_clone_path)
            except Exception as e:
                raise Exception(f"Failed to clone repository: {str(e)}")
        else:
            target_path = repository_url
        
        # Extract project name from repository URL (not from target path)
        # This ensures we get the clean repo name without timestamps
        if is_git_url(repository_url):
            # Extract repo name from Git URL
            if "github.com" in repository_url or "gitlab.com" in repository_url:
                parts = repository_url.rstrip("/").split("/")
                if len(parts) >= 2:
                    project_name = parts[-1].replace(".git", "")
                else:
                    project_name = "repo"
            elif repository_url.startswith("git@"):
                parts = repository_url.split(":")[-1].replace(".git", "").split("/")
                if len(parts) >= 1:
                    project_name = parts[-1]
                else:
                    project_name = "repo"
            else:
                project_name = "repo"
            
            # Sanitize project name
            import re
            project_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)
            if not project_name:
                project_name = "repo"
        elif Path(target_path).is_dir():
            # For non-Git paths, use basename
            project_name = Path(target_path).name
        else:
            project_name = "scan"
        
        # results_dir_path already set before Git clone, no need to set again
        # Just ensure it's still valid
        if not results_dir_path_obj.exists():
            results_dir_path_obj.mkdir(parents=True, exist_ok=True)
        
        # Ensure logs directory exists
        logs_dir = results_dir_path_obj / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set environment variables for docker_runner
        os.environ["COLLECT_METADATA"] = "true"  # Always collect metadata
        os.environ["RESULTS_DIR"] = results_dir_path  # Use central function
        os.environ["ENVIRONMENT"] = os.getenv("ENVIRONMENT", "dev")
        # Set GIT_URL so docker_runner can extract correct project name
        if is_git_url(repository_url):
            os.environ["GIT_URL"] = repository_url
        # Set selected scanners (comma-separated list)
        if selected_scanners:
            import json
            os.environ["SELECTED_SCANNERS"] = json.dumps(selected_scanners)
        else:
            # Clear if not set
            os.environ.pop("SELECTED_SCANNERS", None)
        # Set finding policy (if provided)
        if finding_policy:
            os.environ["FINDING_POLICY_FILE"] = finding_policy
            os.environ["FINDING_POLICY_FILE_IN_CONTAINER"] = finding_policy
        else:
            os.environ.pop("FINDING_POLICY_FILE", None)
            os.environ.pop("FINDING_POLICY_FILE_IN_CONTAINER", None)
        
        # Use docker_runner (Python)
        from app.services.docker_runner import DockerRunner
        
        runner = DockerRunner(log_file=str(logs_dir / "orchestrator.log"))
        
        # Stream output and extract steps for frontend in real-time
        scan_log = results_dir_path_obj / "logs" / "scan.log"
        output_lines = []
        
        def output_callback(line_str: str):
            """Callback for each output line from docker-compose"""
            output_lines.append(line_str)
            print(f"[Scanner Worker] {line_str}")
            
            # Write ALL logs to scan.log (live, not buffered)
            try:
                with open(scan_log, "a", encoding="utf-8") as f:
                    f.write(f"{line_str}\n")
            except Exception as e:
                print(f"[Scanner Worker] Error writing to scan.log: {e}")
            
            # Step Registry writes directly to steps.log - read it periodically
            # Use a simple debounce mechanism to avoid reading too frequently
            import time
            last_step_check = getattr(output_callback, '_last_step_check', 0)
            current_time = time.time()
            
            # Check steps.log every 0.5 seconds
            if current_time - last_step_check > 0.5:
                output_callback._last_step_check = current_time
                
                # Read steps from steps.log and send to WebSocket
                try:
                    import asyncio
                    from app.services.websocket_manager import get_websocket_manager
                    from app.services.step_service import read_steps_from_log
                    
                    async def send_websocket_update():
                        try:
                            ws_manager = get_websocket_manager()
                            
                            # Read steps from steps.log (written by Step Registry)
                            steps = read_steps_from_log(results_dir_path_obj)
                            
                            if steps:
                                # Calculate total_steps and progress_percentage
                                total_steps = max([s["number"] for s in steps], default=0)
                                if total_steps == 0:
                                    progress_percentage = 0
                                else:
                                    completed = sum(1 for s in steps if s.get("status") == "completed")
                                    running = sum(1 for s in steps if s.get("status") == "running")
                                    failed = sum(1 for s in steps if s.get("status") == "failed")
                                    # Progress = (completed + failed + (running * 0.5)) / total_steps
                                    progress_percentage = round(((completed + failed + (running * 0.5)) / total_steps) * 100)
                                
                                # Send update to WebSocket clients
                                await ws_manager.send_step_update(scan_id, {
                                    "steps": steps,
                                    "total_steps": total_steps,
                                    "progress_percentage": progress_percentage
                                })
                        except Exception as e:
                            print(f"[Scanner Worker] Error sending to WebSocket: {e}")
                    
                    # Schedule async task (runs in background)
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(send_websocket_update())
                        else:
                            loop.run_until_complete(send_websocket_update())
                    except RuntimeError:
                        # No event loop, skip WebSocket update
                        pass
                except Exception as e:
                    print(f"[Scanner Worker] Error scheduling WebSocket update: {e}")
        
        # Execute scan using docker_runner
        print(f"[Scanner Worker] Starting scan: {scan_id} for {repository_url}")
        
        # Track runner for cleanup
        self.running_runners[scan_id] = runner
        
        try:
            success = await runner.run_scan_async(
                target=target_path,
                scan_id=scan_id,
                project_name=project_name,
                results_dir=results_dir_path,
                ci_mode=False,  # WebUI always does full scans
                finding_policy=finding_policy,
                collect_metadata=True,
                output_callback=output_callback,
            )
        finally:
            # Remove from tracking when done
            self.running_runners.pop(scan_id, None)
        
        if not success:
            error_output = "\n".join(output_lines[-20:]) if output_lines else "No output captured"
            raise Exception(f"Scan failed: {error_output}")
        
        # Mark Step 20 (Metadata Collection) as completed if scan was successful
        # This ensures the final step is always marked as completed, even if the metadata script failed
        if "Metadata Collection" in current_scan.get("step_names", {}):
            step_num = current_scan["step_names"]["Metadata Collection"]
            completed_key = "Metadata Collection_completed"
            if completed_key not in current_scan.get("completed_steps", set()):
                if "completed_steps" not in current_scan:
                    current_scan["completed_steps"] = set()
                current_scan["completed_steps"].add(completed_key)
                # Write step in JSON format (structured, no regex parsing!)
                write_step_to_log(
                    step_number=step_num,
                    step_name="Metadata Collection",
                    status="completed",
                    message="Metadata collection completed",
                    scan_id=scan_id,
                    current_scan=current_scan,
                    results_dir=results_dir_path_obj
                )
                print(f"[Scanner Worker] Marked Step {step_num} (Metadata Collection) as completed")
        
        # Try to find scan results directory
        # Results are typically in results/PROJECT_NAME_SCAN_ID/
        scan_results_dir = None
        if results_dir.exists():
            # Look for directory matching scan_id
            for result_dir in results_dir.iterdir():
                if result_dir.is_dir() and scan_id in result_dir.name:
                    scan_results_dir = result_dir
                    break

        # Persist AI prompts for each supported language
        if scan_results_dir:
            try:
                from app.services.ai_prompt_service import persist_ai_prompts, SUPPORTED_PROMPT_LANGUAGES
                persist_ai_prompts(
                    results_dir=scan_results_dir,
                    base_dir=base_dir,
                    policy_path="config/finding-policy.json",
                    languages=SUPPORTED_PROMPT_LANGUAGES,
                )
                print(f"[Scanner Worker] AI prompts saved in {scan_results_dir}")
            except Exception as e:
                print(f"[Scanner Worker] Failed to persist AI prompts: {e}")

        # Increment global statistics from results
        if scan_results_dir:
            try:
                from app.services.statistics_service import increment_statistics_for_results
                await increment_statistics_for_results(
                    results_dir=scan_results_dir,
                    base_dir=base_dir,
                )
                print(f"[Scanner Worker] Statistics updated for scan {scan_id}")
            except Exception as stats_error:
                print(f"[Scanner Worker] Failed to update statistics: {stats_error}")
        
        # Save metadata for deduplication
        try:
            # Extract branch from repository if not provided
            actual_branch = branch or "main"
            
            # Save metadata
            await self.db.save_scan_metadata(
                repository_url=repository_url,
                branch=actual_branch,
                commit_hash=actual_commit_hash or "unknown",
                scan_id=scan_id,
                findings_count=0,  # TODO: Parse from results
                metadata_file_path=str(scan_results_dir / "scan-metadata.json") if scan_results_dir else None,
            )
            print(f"[Scanner Worker] Metadata saved for scan {scan_id}")
        except Exception as e:
            print(f"[Scanner Worker] Failed to save metadata: {e}")
        
        # Cleanup temp clone if used
        if temp_clone_path and temp_clone_path.exists():
            try:
                import shutil
                shutil.rmtree(temp_clone_path)
                print(f"[Scanner Worker] Cleaned up temp clone: {temp_clone_path}")
            except Exception as e:
                print(f"[Scanner Worker] Failed to cleanup temp clone: {e}")
        
        # Send WebSocket notification that scan is completed
        try:
            from app.services.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()
            # Use the directory name (e.g., "SimpleSecCheck_20260303_203059")
            # This is what the frontend expects for results_dir
            results_dir_name = results_dir_path_obj.name
            await ws_manager.send_scan_completed(scan_id, results_dir_name)
            print(f"[Scanner Worker] Sent scan_completed WebSocket notification for {scan_id} with results_dir={results_dir_name}")
        except Exception as e:
            print(f"[Scanner Worker] Failed to send scan_completed notification: {e}")
        
        return {
            "scan_id": scan_id,
            "results_dir": results_dir_path_obj.name,
        }


# Global scanner worker instance
_scanner_worker: Optional[ScannerWorker] = None


async def get_scanner_worker() -> ScannerWorker:
    """Get or create scanner worker instance"""
    global _scanner_worker
    if _scanner_worker is None:
        _scanner_worker = ScannerWorker()
        # Database will be initialized in start() - no need to initialize here
        # as it's already done by Session/Queue services in startup event
    return _scanner_worker


async def start_scanner_worker():
    """Start the scanner worker (called on application startup)"""
    worker = await get_scanner_worker()
    await worker.start()


async def stop_scanner_worker():
    """Stop the scanner worker (called on application shutdown)"""
    worker = await get_scanner_worker()
    await worker.stop()
