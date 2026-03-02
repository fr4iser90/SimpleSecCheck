"""
Scan Service
Handles scan management, monitoring, and status tracking
"""
import os
import subprocess  # nosec B404 - Used safely with hardcoded CLI script, shell=False, and proper security controls
import asyncio
import re
import threading
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel

from .container_service import stop_running_containers
from .shutdown_service import schedule_shutdown, cancel_shutdown, SHUTDOWN_AFTER_SCAN, AUTO_SHUTDOWN_ENABLED, SHUTDOWN_DELAY
from .step_service import extract_steps_for_frontend, initialize_step_tracking, reset_step_tracking, initialize_steps_log
from .git_service import is_git_url, clone_repository, cleanup_temp_repository

# Central path management - ALL paths come from path_setup.py
import sys
sys.path.insert(0, "/app/scanner")
from core.path_setup import (
    get_logs_dir_for_scan,
    get_scan_results_dir_host, 
    get_target_mount_path_host, 
    get_owasp_data_path_host, 
    get_config_path_host,
    get_finding_policy_check_path_for_git_clone,
    get_finding_policy_check_path_for_local_scan
)


class ScanRequest(BaseModel):
    type: str  # code, website, network
    target: str
    git_branch: Optional[str] = None  # Optional Git branch to clone
    ci_mode: bool = False
    finding_policy: Optional[str] = None
    collect_metadata: bool = False  # OPTIONAL: Only collect metadata if user explicitly enables it


class ScanStatus(BaseModel):
    status: str
    scan_id: Optional[str] = None
    results_dir: Optional[str] = None
    started_at: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None


async def start_scan(
    request: ScanRequest,
    current_scan: dict,
    cli_script: Path,
    base_dir: Path,
    results_dir: Path,
):
    """
    Start a scan by calling docker-compose run scanner directly
    Single-shot: Only one scan at a time
    """
    # Check if scan is already running
    if current_scan["status"] == "running":
        raise HTTPException(status_code=409, detail="Scan already running")
    
    # Cancel any scheduled shutdown when starting a new scan
    cancel_shutdown()
    print(f"[Scan Service] Cancelled scheduled shutdown - new scan starting")
    
    # Validate scan type
    if request.type not in ["code", "website", "network"]:
        raise HTTPException(status_code=400, detail="Invalid scan type")
    
    # Clean and validate target (trim whitespace)
    clean_target = request.target.strip() if request.target else ""
    clean_finding_policy = request.finding_policy.strip() if request.finding_policy else None
    
    # Log what Frontend sent to Backend
    print(f"[Scan Service] Frontend sent: type={request.type}, target={clean_target}, finding_policy={clean_finding_policy}, ci_mode={request.ci_mode}, collect_metadata={request.collect_metadata}")
    
    # STEP 1: Generate scan_id (ALWAYS FIRST)
    scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_scan["scan_id"] = scan_id
    
    # STEP 2: Save original target for directory name (before Git clone changes it)
    original_target = clean_target
    
    # STEP 3: Initialize step tracking and create scan directory (ALWAYS BEFORE ANYTHING ELSE)
    initialize_step_tracking(current_scan)
    initialize_steps_log(scan_id, results_dir, current_scan, original_target)
    
    # STEP 4: Handle Git repository URLs (if Git URL, clone it)
    temp_clone_path = None
    git_clone_used = False
    if request.type == "code" and is_git_url(clean_target):
        print(f"[Scan Service] Git repository URL detected: {clean_target}")
        git_branch = request.git_branch.strip() if request.git_branch else None
        temp_clone_path = await clone_repository(clean_target, base_dir, scan_id, current_scan, results_dir, git_branch)
        clean_target = str(temp_clone_path)  # Use cloned path for scan
        git_clone_used = True
        print(f"[Scan Service] Using cloned repository path: {clean_target}")
        # CI Mode is not needed for Git clones - the clone already contains only tracked files
        if request.ci_mode:
            print(f"[Scan Service] CI Mode disabled for Git clone (clone already contains only tracked files)")
    
    # STEP 5: Validate target
    if request.type == "code" and not clean_target:
        raise HTTPException(status_code=400, detail="Target path is required")
    elif request.type == "website":
        if not clean_target:
            raise HTTPException(status_code=400, detail="Target URL is required")
        if not clean_target.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Target must be a valid URL (http:// or https://)")
    
    # STEP 6: Get all paths from central path_setup (NO PATH CALCULATIONS HERE!)
    # IMPORTANT: This must happen AFTER Git clone (if used), so paths are correct
    scan_results_dir_container = current_scan["results_dir"]
    results_dir_host = get_scan_results_dir_host(scan_results_dir_container)
    logs_dir_host = get_logs_dir_for_scan(results_dir_host)
    target_mount_path_host = get_target_mount_path_host(clean_target)
    owasp_data_path_host = get_owasp_data_path_host()
    config_path_host = get_config_path_host()
    
    # OWASP volume mount
    owasp_volume = []
    if owasp_data_path_host:
        owasp_volume = ["-v", f"{owasp_data_path_host}:/SimpleSecCheck/owasp-dependency-check-data"]
        if os.path.exists(owasp_data_path_host):
            print(f"[Scan Service] Using OWASP data volume: {owasp_volume[1]} (exists)")
        else:
            print(f"[Scan Service] Using OWASP data volume: {owasp_volume[1]} (will be created)")
    else:
        print(f"[Scan Service] WARNING: Could not determine OWASP data path - relying on docker-compose.yml volumes")
    
    # Config volume mount
    config_volume = []
    if config_path_host:
        config_volume = ["-v", f"{config_path_host}:/SimpleSecCheck/config:ro"]
        if os.path.exists(config_path_host):
            print(f"[Scan Service] Using config volume: {config_volume[1]} (exists)")
        else:
            print(f"[Scan Service] WARNING: Config path does not exist: {config_path_host}")
    else:
        print(f"[Scan Service] WARNING: Could not determine config path - relying on docker-compose.yml volumes")
    
    # Build docker-compose command (use central function from path_setup)
    import sys
    sys.path.insert(0, "/app/scanner")
    from core.path_setup import get_docker_compose_file, get_docker_compose_context
    docker_compose_file = get_docker_compose_file()
    docker_compose_context = get_docker_compose_context()
    
    cmd = [
        "docker-compose",
        "-f", docker_compose_file,
        "--project-directory", docker_compose_context,
        "run", "--rm"
    ]
    
    # CI Mode: Create tracked snapshot for local scans (Git clones already contain only tracked files)
    # IMPORTANT: Save original target path for metadata collection (tracked snapshot has no .git)
    original_target_mount_path_host = target_mount_path_host
    
    # Environment variables
    env_vars = [
        "-e", f"SCAN_TYPE={request.type}",
        "-e", f"PROJECT_RESULTS_DIR={results_dir_host}",
        "-e", f"COLLECT_METADATA={'true' if request.collect_metadata else 'false'}",
        "-e", f"TARGET_PATH_HOST={original_target_mount_path_host}",
    ]
    
    if request.type == "website":
        env_vars.extend(["-e", f"ZAP_TARGET={clean_target}", "-e", f"TARGET_URL={clean_target}"])
    # CI Mode: For local scans, let the scanner container create the tracked snapshot
    # (The scanner container has access to /target mount, WebUI container does not)
    # For Git clones, CI mode is not needed (clone already contains only tracked files)
    if request.ci_mode and not git_clone_used and request.type == "code":
        # Set SCAN_SCOPE=tracked - scanner container will create snapshot from /target
        env_vars.extend(["-e", "SCAN_SCOPE=tracked"])
        env_vars.extend(["-e", "CI_MODE=true"])
        print(f"[Scan Service] CI Mode enabled - scanner will create tracked snapshot from /target")
    
    # Finding policy - CLEARLY SEPARATED: Git clones vs local scans
    # IMPORTANT: Git clones exist in WebUI container, local scans don't!
    # - Git clones: Can check file existence in WebUI container
    # - Local scans: Cannot check in WebUI container, scanner will check after mount
    finding_policy_file = None
    if clean_finding_policy:
        print(f"[Scan Service] Finding policy resolution:")
        print(f"[Scan Service]   clean_target: {clean_target}")
        print(f"[Scan Service]   target_mount_path_host (host): {target_mount_path_host}")
        print(f"[Scan Service]   clean_finding_policy: {clean_finding_policy}")
        print(f"[Scan Service]   git_clone_used: {git_clone_used}")
        
        if git_clone_used:
            # Git clone: Use dedicated function for Git clones (can check in container)
            policy_check_path = get_finding_policy_check_path_for_git_clone(clean_target, clean_finding_policy)
            if not policy_check_path or not os.path.exists(policy_check_path):
                # Finding policy is optional - warn but don't fail
                print(f"[Scan Service] ⚠️ Finding policy file not found: {clean_finding_policy} (checked at {policy_check_path or 'invalid path'})")
                print(f"[Scan Service] ⚠️ Continuing without finding policy - scanner will use default behavior")
                # Don't set finding_policy_file - scanner will auto-detect if available
            else:
                finding_policy_file = f"/target/{clean_finding_policy}"
                env_vars.extend(["-e", f"FINDING_POLICY_FILE={finding_policy_file}"])
                print(f"[Scan Service] ✓ Using finding policy: {finding_policy_file} (found at {policy_check_path})")
        else:
            # Local scan: Use dedicated function for local scans (cannot check in container)
            policy_check_path = get_finding_policy_check_path_for_local_scan(target_mount_path_host, clean_finding_policy)
            # For local scans, we can't check in WebUI container, but we pass the path
            # Scanner container will verify it exists at /target/{clean_finding_policy}
            finding_policy_file = f"/target/{clean_finding_policy}"
            env_vars.extend(["-e", f"FINDING_POLICY_FILE={finding_policy_file}"])
            print(f"[Scan Service] Passing finding policy path to scanner: {finding_policy_file}")
            print(f"[Scan Service] Note: Scanner container will verify file exists at mount point")
    
    cmd.extend(env_vars)
    
    # Volume mounts
    if request.type == "code":
        cmd.extend(["-v", f"{target_mount_path_host}:/target:ro"])
        # For CI mode, also mount original repository for metadata collection (scanner creates snapshot, but metadata needs .git)
        if request.ci_mode and not git_clone_used:
            cmd.extend(["-v", f"{original_target_mount_path_host}:/original-target:ro"])
            env_vars.extend(["-e", "ORIGINAL_TARGET_PATH=/original-target"])
    cmd.extend(["-v", f"{results_dir_host}:/SimpleSecCheck/results"])
    cmd.extend(["-v", f"{logs_dir_host}:/SimpleSecCheck/logs"])
    
    if config_volume:
        cmd.extend(config_volume)
    
    if owasp_volume:
        cmd.extend(owasp_volume)
    
    # Network scan needs docker socket
    if request.type == "network":
        cmd.extend(["-v", "/var/run/docker.sock:/var/run/docker.sock:ro"])
    
    # Scanner command
    cmd.extend(["scanner", "/SimpleSecCheck/scripts/security-check.sh"])
    
    print(f"[Scan Service] Executing docker-compose command: {' '.join(cmd)}")
    
    # Environment for subprocess (no special env vars needed, docker-compose handles it)
    env = os.environ.copy()
    
    # STEP 7: Start scan process
    try:
        process = subprocess.Popen(  # nosec B603, B607
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(base_dir),
            env=env,
            shell=False,
            start_new_session=False,
            text=True,
            bufsize=1
        )
        
        # STEP 8: Update scan state
        current_scan["process"] = process
        current_scan["status"] = "running"
        current_scan["started_at"] = datetime.now().isoformat()
        current_scan["process_output"] = []
        current_scan["error_code"] = None
        current_scan["error_message"] = None
        current_scan["container_ids"] = []
        current_scan["temp_clone_path"] = str(temp_clone_path) if temp_clone_path else None
        
        # Reset step tracking (preserve Git Clone steps if they exist)
        reset_step_tracking(current_scan, preserve_git_clone=True)
        
        print(f"[Start Scan] Status set to 'running', scan_id={scan_id}, PID={process.pid}")
        
        # Start background task to capture process output
        asyncio.create_task(capture_process_output(process, scan_id, current_scan, results_dir))
        
        # Start background task to monitor process
        asyncio.create_task(monitor_scan(process, scan_id, current_scan, results_dir))
        
        return ScanStatus(
            status="running",
            scan_id=scan_id,
            started_at=current_scan["started_at"]
        )
    except Exception as e:
        # Cleanup temp repository if scan failed to start
        if temp_clone_path:
            cleanup_temp_repository(temp_clone_path)
        current_scan["status"] = "error"
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


async def capture_process_output(process: subprocess.Popen, scan_id: str, current_scan: dict, results_dir: Path):
    """Capture stdout/stderr from run-docker.sh process and store for streaming"""
    try:
        print(f"[Process Output] Starting to capture output for scan {scan_id}, PID={process.pid}")
        loop = asyncio.get_event_loop()
        
        # Read process output line by line - run readline() in thread to avoid blocking event loop
        while True:
            # Run readline() in thread pool to avoid blocking event loop
            line = await loop.run_in_executor(None, process.stdout.readline)
            
            if not line:
                # Check if process is done (non-blocking poll)
                return_code = await loop.run_in_executor(None, process.poll)
                if return_code is not None:
                    # Process finished
                    print(f"[Process Output] Process finished with return code {return_code}")
                    break
                await asyncio.sleep(0.1)
                continue
            
            # Clean the line (remove ANSI codes, strip) - but DON'T filter for backend logging
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
            if clean_line:
                # Store ALL logs unfiltered in process_output (backend should log everything)
                with current_scan["process_output_lock"]:
                    current_scan["process_output"].append(clean_line)
                    # Keep only last 1000 lines to avoid memory issues
                    if len(current_scan["process_output"]) > 1000:
                        current_scan["process_output"] = current_scan["process_output"][-1000:]
                
                # Backend logs only important lines (not every line to reduce noise)
                # Log orchestrator messages, errors, and important steps
                if any(keyword in clean_line for keyword in [
                    "[SimpleSecCheck Orchestrator]",
                    "[SimpleSecCheck Docker]",
                    "[ERROR]",
                    "[WARNING]",
                    "[ORCHESTRATOR ERROR]",
                    "Scan completed",
                    "Scan failed",
                    "failed with exit code",
                    "Starting run-docker.sh",
                    "Converting container paths",
                    "Verifying host paths",
                    "Mounting volumes",
                    "Executing docker-compose",
                    "Target path does not exist",
                    "Target directory contains",
                    "Target directory is empty"
                ]):
                    print(f"[Process Output] {clean_line}")
                
                # Extract steps for frontend (this also writes to steps.log)
                extract_steps_for_frontend(clean_line, current_scan, results_dir)
    except Exception as e:
        print(f"[Process Output Error] {e}")
        import traceback
        traceback.print_exc()


async def monitor_scan(process: subprocess.Popen, scan_id: str, current_scan: dict, results_dir: Path):
    """Monitor scan process and update status when done"""
    # Wait for process to complete - run in thread to avoid blocking event loop
    loop = asyncio.get_event_loop()
    return_code = await loop.run_in_executor(None, process.wait)
    
    # If process exited unexpectedly (non-zero exit code that's not a normal scan error),
    # try to stop any orphaned containers
    if return_code != 0 and return_code not in [0, 1]:  # 1 might be a normal scan warning
        # Check if this looks like an unexpected termination (SIGTERM, SIGINT, etc.)
        if return_code in [130, 143, -15, -2]:  # SIGINT, SIGTERM
            print(f"[Monitor Scan] Process terminated unexpectedly (code {return_code}), cleaning up containers...")
            stop_running_containers(current_scan)
    
    # After process exits, wait a bit and check if scan is really done
    await asyncio.sleep(2)  # Give logs time to flush
    
    # Use results_dir from current_scan (set by initialize_steps_log)
    results_dir_path = current_scan["results_dir"]
    log_file = Path(results_dir_path) / "logs" / "security-check.log"
    
    # Determine if scan is completed
    # Priority order:
    # 1. Report file exists (most reliable - if report exists, scan succeeded)
    # 2. Process exit code == 0
    # 3. Completion marker in log file
    scan_completed = False
    report_file = None
    
    # Check 1: Report file exists (highest priority - if report exists, scan is done)
    if results_dir_path:
        report_file = Path(results_dir_path) / "security-summary.html"
        if report_file.exists():
            scan_completed = True
            print(f"[Monitor Scan] Report file exists: {report_file} - marking scan as completed")
            # If report exists, treat as success regardless of exit code
            return_code = 0
    
    # Check 2: Process exit code
    if not scan_completed and return_code == 0:
        scan_completed = True
    
    # Check 3: Completion marker in log file
    if not scan_completed and log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()
                if "SimpleSecCheck Security Scan Sequence Completed" in log_content:
                    scan_completed = True
                elif "SimpleSecCheck Docker Security Scan Completed" in log_content:
                    scan_completed = True
                elif "Security scan completed" in log_content:
                    scan_completed = True
        except Exception:
            pass  # Non-critical
    
    # Capture any error output for debugging and user feedback
    error_message = None
    if process.stdout:
        try:
            output = process.stdout.read()
            if output and return_code != 0:
                # Remove ANSI color codes first
                clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
                
                # Extract error message - look for various error patterns
                error_lines = []
                for line in clean_output.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    # Look for explicit error markers
                    if '[ERROR]' in line or 'ERROR' in line.upper():
                        error_lines.append(line)
                    # Look for common error patterns
                    elif 'cannot' in line.lower() and ('create' in line.lower() or 'access' in line.lower() or 'find' in line.lower()):
                        error_lines.append(line)
                    elif 'failed' in line.lower() or 'failure' in line.lower():
                        error_lines.append(line)
                    elif 'does not exist' in line.lower() or 'not found' in line.lower():
                        error_lines.append(line)
                    elif 'read-only' in line.lower() or 'permission denied' in line.lower():
                        error_lines.append(line)
                
                if error_lines:
                    # Use the most relevant error line (prefer [ERROR] lines, then others)
                    priority_errors = [line for line in error_lines if '[ERROR]' in line]
                    if priority_errors:
                        error_message = priority_errors[0]
                    else:
                        error_message = error_lines[0]
                else:
                    # Fallback: use last non-empty lines of output
                    output_lines = [line.strip() for line in clean_output.split('\n') if line.strip()]
                    if output_lines:
                        # Take last 2-3 lines as they often contain the actual error
                        error_message = '\n'.join(output_lines[-3:])
                
                # Log full error output for debugging
                error_preview = clean_output[:1000].replace('\n', ' | ')
                print(f"[Scan Error] Process failed with code {return_code}: {error_preview}")
        except Exception as e:
            print(f"[Scan Error] Failed to read error output: {e}")
            error_message = f"Failed to capture error details: {str(e)}"
    
    # Update state based on whether scan is completed
    if scan_completed:
        # If scan is completed (report exists or exit code 0), mark as done
        current_scan["status"] = "done"
        current_scan["error_code"] = None
        current_scan["error_message"] = None
        
        # Cleanup temporary repository after scan is done
        temp_clone_path_str = current_scan.get("temp_clone_path")
        if temp_clone_path_str:
            temp_clone_path = Path(temp_clone_path_str)
            cleanup_temp_repository(temp_clone_path)
            current_scan["temp_clone_path"] = None
        
    else:
        # Scan process exited but scan might still be running
        current_scan["status"] = "running"
        asyncio.create_task(recheck_scan_status(scan_id, results_dir_path, return_code, error_message, current_scan, results_dir))
    
    # Schedule shutdown after scan if enabled (only if completed)
    if scan_completed and SHUTDOWN_AFTER_SCAN and AUTO_SHUTDOWN_ENABLED:
        print(f"[Auto-Shutdown] Scan completed, will shutdown in {SHUTDOWN_DELAY}s...")
        schedule_shutdown(delay=SHUTDOWN_DELAY, current_scan=current_scan)


async def recheck_scan_status(scan_id: str, results_dir: Optional[str], return_code: int, error_message: Optional[str], current_scan: dict, results_dir_path: Path):
    """Re-check scan status after a delay to see if scan is really done"""
    await asyncio.sleep(5)
    
    # Use results_dir from current_scan (set by initialize_steps_log)
    results_dir_path_str = current_scan["results_dir"]
    log_file = Path(results_dir_path_str) / "logs" / "security-check.log"
    
    scan_done = False
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()
                if "SimpleSecCheck Security Scan Sequence Completed" in log_content:
                    scan_done = True
                elif "SimpleSecCheck Docker Security Scan Completed" in log_content:
                    scan_done = True
                elif "Security scan completed" in log_content:
                    scan_done = True
        except Exception as e:
            # Non-critical: Failed to check scan completion status
            import logging
            logging.debug(f"Could not check scan completion status: {e}")
    
    # If still not done after 30 seconds, assume done based on return code
    await asyncio.sleep(25)  # Total 30 seconds wait
    
    # Update status
    if scan_done or return_code != 0:
        if return_code == 0:
            current_scan["status"] = "done"
            current_scan["results_dir"] = results_dir
            current_scan["error_code"] = None
            current_scan["error_message"] = None
        else:
            current_scan["status"] = "error"
            current_scan["results_dir"] = results_dir
            current_scan["error_code"] = return_code
            current_scan["error_message"] = error_message
        
        # Cleanup temporary repository after scan is done
        temp_clone_path_str = current_scan.get("temp_clone_path")
        if temp_clone_path_str:
            temp_clone_path = Path(temp_clone_path_str)
            cleanup_temp_repository(temp_clone_path)
            current_scan["temp_clone_path"] = None
        
        # Schedule shutdown if enabled
        if SHUTDOWN_AFTER_SCAN and AUTO_SHUTDOWN_ENABLED:
            print(f"[Auto-Shutdown] Scan completed, will shutdown in {SHUTDOWN_DELAY}s...")
            schedule_shutdown(delay=SHUTDOWN_DELAY, current_scan=current_scan)


async def get_scan_status(current_scan: dict, results_dir: Path) -> ScanStatus:
    """Get current scan status"""
    old_status = current_scan["status"]
    
    # If status is "running", check if scan is really done by looking at log file
    if current_scan["status"] == "running" and current_scan["scan_id"]:
        results_dir_path = current_scan["results_dir"]
        log_file = Path(results_dir_path) / "logs" / "security-check.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    log_content = f.read()
                    if "SimpleSecCheck Security Scan Sequence Completed" in log_content:
                        current_scan["status"] = "done"
                    elif "SimpleSecCheck Docker Security Scan Completed" in log_content:
                        current_scan["status"] = "done"
            except Exception:
                pass  # Non-critical
    
    status_response = ScanStatus(
        status=current_scan["status"],
        scan_id=current_scan["scan_id"],
        results_dir=current_scan["results_dir"],
        started_at=current_scan["started_at"],
        error_code=current_scan.get("error_code"),
        error_message=current_scan.get("error_message")
    )
    
    # Log only on status change (reduced logging)
    if old_status != status_response.status:
        print(f"[Status] Changed: {old_status} -> {status_response.status}, scan_id={status_response.scan_id}")
    
    return status_response


async def stop_scan(current_scan: dict) -> ScanStatus:
    """Stop the currently running scan"""
    if current_scan["status"] != "running":
        raise HTTPException(status_code=400, detail="No scan is currently running")
    
    print("[Stop Scan] Stopping running scan...")
    
    # Stop the subprocess
    process = current_scan.get("process")
    if process and process.poll() is None:  # Process is still running
        try:
            print(f"[Stop Scan] Terminating process PID={process.pid}...")
            process.terminate()
            # Wait a bit for graceful shutdown
            try:
                process.wait(timeout=5)
                print("[Stop Scan] Process terminated gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                print("[Stop Scan] Process didn't terminate, force killing...")
                process.kill()
                process.wait(timeout=2)
                print("[Stop Scan] Process force killed")
        except Exception as e:
            print(f"[Stop Scan] Error stopping process: {e}")
    
    # Stop Docker containers
    print("[Stop Scan] Stopping Docker containers...")
    stopped_containers = stop_running_containers(current_scan)
    if stopped_containers:
        print(f"[Stop Scan] Stopped {len(stopped_containers)} container(s): {stopped_containers}")
    else:
        print("[Stop Scan] No containers found to stop")
    
    # Update status
    current_scan["status"] = "error"
    current_scan["error_code"] = 130  # SIGINT exit code
    current_scan["error_message"] = "Scan was stopped by user"
    current_scan["container_ids"] = []  # Clear container IDs
    
    # Cleanup temporary repository if scan was stopped
    temp_clone_path_str = current_scan.get("temp_clone_path")
    if temp_clone_path_str:
        temp_clone_path = Path(temp_clone_path_str)
        cleanup_temp_repository(temp_clone_path)
        current_scan["temp_clone_path"] = None
    
    return ScanStatus(
        status="error",
        scan_id=current_scan["scan_id"],
        results_dir=current_scan["results_dir"],
        started_at=current_scan["started_at"],
        error_code=130,
        error_message="Scan was stopped by user"
    )
