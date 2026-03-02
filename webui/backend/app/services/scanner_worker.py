"""
Scanner Worker Service
Pulls jobs from queue and executes scans
"""

import os
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from app.database import get_database
from app.services.queue_service import get_queue_service


class ScannerWorker:
    """Worker that processes scan jobs from queue"""
    
    def __init__(self):
        self.db = get_database()
        self.max_concurrent_scans = int(os.getenv("MAX_CONCURRENT_SCANS", "1"))
        self.running_scans: Dict[str, asyncio.Task] = {}
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
        
        # Wait for running scans to complete
        if self.running_scans:
            await asyncio.gather(*self.running_scans.values(), return_exceptions=True)
        
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
    
    async def _worker_loop(self):
        """Main worker loop - continuously polls queue for jobs"""
        while self.is_running:
            try:
                # Check if we can start more scans
                if len(self.running_scans) < self.max_concurrent_scans:
                    # Get next job from queue
                    job = await self.db.get_next_queue_item()
                    
                    if job:
                        # Start scan task
                        task = asyncio.create_task(self._process_scan_job(job))
                        self.running_scans[job["queue_id"]] = task
                    else:
                        # No jobs available, wait a bit
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
                    del self.running_scans[queue_id]
                
            except Exception as e:
                print(f"[Scanner Worker] Error in worker loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_scan_job(self, job: Dict[str, Any]):
        """Process a single scan job"""
        queue_id = job["queue_id"]
        repository_url = job["repository_url"]
        branch = job.get("branch")
        commit_hash = job.get("commit_hash")
        
        try:
            # Update status to running
            await self.db.update_queue_status(
                queue_id=queue_id,
                status="running",
                started_at=datetime.utcnow(),
            )
            
            # Execute scan
            scan_id = await self._execute_scan(
                repository_url=repository_url,
                branch=branch,
                commit_hash=commit_hash,
            )
            
            # Update status to completed
            await self.db.update_queue_status(
                queue_id=queue_id,
                status="completed",
                scan_id=scan_id,
                completed_at=datetime.utcnow(),
            )
            
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
    ) -> str:
        """
        Execute scan using run-docker.sh
        Returns scan_id
        """
        import sys
        sys.path.insert(0, "/app/scanner")
        from core.path_setup import (
            get_webui_base_dir, 
            get_webui_results_dir, 
            get_webui_cli_script,
            get_results_dir_for_scan,
            get_docker_compose_file
        )
        from app.services.git_service import clone_repository, is_git_url
        
        # Get paths - ALL FROM CENTRAL path_setup.py
        base_dir = get_webui_base_dir()
        results_dir = get_webui_results_dir()
        cli_script = get_webui_cli_script()
        
        # Generate scan_id
        scan_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Create a minimal current_scan dict for git_service
        current_scan = {
            "scan_id": scan_id,
            "step_counter": 0,
            "step_names": {},
        }
        
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
        
        # Build command - use run-docker.sh with target path
        cmd = [str(cli_script), "--collect-metadata", target_path]
        
        # Extract project name from target path
        if Path(target_path).is_dir():
            # For temp clone paths like /app/results/tmp/PIDEA_20260302_160637/PIDEA
            # The last part (PIDEA) is the actual project name
            project_name = Path(target_path).name
        else:
            project_name = "scan"
        
        # Get results directory from central path_setup function
        results_dir_path = get_results_dir_for_scan(project_name, scan_id)
        
        # Set environment variables
        env = os.environ.copy()
        env["COLLECT_METADATA"] = "true"  # Always collect metadata in production
        env["SCAN_ID"] = scan_id  # Pass scan_id to run-docker.sh
        env["RESULTS_DIR"] = results_dir_path  # Use central function
        env["ENVIRONMENT"] = os.getenv("ENVIRONMENT", "dev")  # Pass ENVIRONMENT to run-docker.sh
        
        # Execute scan
        print(f"[Scanner Worker] Starting scan: {scan_id} for {repository_url}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(base_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # Combine stderr with stdout
        )
        
        # Stream output
        output_lines = []
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            line_str = line.decode('utf-8', errors='ignore').strip()
            output_lines.append(line_str)
            print(f"[Scanner Worker] {line_str}")
        
        await process.wait()
        
        if process.returncode != 0:
            error_output = "\n".join(output_lines[-20:])  # Last 20 lines
            raise Exception(f"Scan failed (exit code {process.returncode}): {error_output}")
        
        # Try to find scan results directory
        # Results are typically in results/PROJECT_NAME_SCAN_ID/
        scan_results_dir = None
        if results_dir.exists():
            # Look for directory matching scan_id
            for result_dir in results_dir.iterdir():
                if result_dir.is_dir() and scan_id in result_dir.name:
                    scan_results_dir = result_dir
                    break
        
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
        
        return scan_id


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
