"""
Scan Service
Handles scan management, monitoring, and status tracking
"""
import os
import subprocess
import asyncio
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import HTTPException
from pydantic import BaseModel

from .container_service import stop_running_containers
from .shutdown_service import schedule_shutdown, SHUTDOWN_AFTER_SCAN, AUTO_SHUTDOWN_ENABLED, SHUTDOWN_DELAY
from .step_service import extract_steps_for_frontend


class ScanRequest(BaseModel):
    type: str  # code, website, network
    target: str
    ci_mode: bool = False
    finding_policy: Optional[str] = None


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
    log_worker_thread_func
):
    """
    Start a scan by calling bin/run-docker.sh
    Single-shot: Only one scan at a time
    """
    # Check if scan is already running
    if current_scan["status"] == "running":
        raise HTTPException(status_code=409, detail="Scan already running")
    
    # Validate scan type
    if request.type not in ["code", "website", "network"]:
        raise HTTPException(status_code=400, detail="Invalid scan type")
    
    # Clean and validate target (trim whitespace)
    clean_target = request.target.strip() if request.target else ""
    clean_finding_policy = request.finding_policy.strip() if request.finding_policy else None
    
    if request.type == "code":
        if not clean_target:
            raise HTTPException(status_code=400, detail="Target path is required")
        # Note: We don't validate path existence here because:
        # 1. The path is on the host, not in the container
        # 2. run-docker.sh will validate and provide better error messages
        # 3. The path will be mounted when docker-compose runs
    elif request.type == "website":
        if not clean_target:
            raise HTTPException(status_code=400, detail="Target URL is required")
        if not clean_target.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Target must be a valid URL (http:// or https://)")
    
    # Build command (exactly like CLI)
    cmd = [str(cli_script)]
    if request.ci_mode:
        cmd.append("--ci")
    if clean_finding_policy:
        cmd.extend(["--finding-policy", clean_finding_policy])
    cmd.append(clean_target if request.type != "network" else "network")
    
    # Start process (as non-root user, no shell injection)
    try:
        # Security: Use list for cmd, no shell=True
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout for better error messages
            cwd=str(base_dir),
            env=os.environ.copy(),
            # Security: Run as current user (non-root), no shell
            shell=False,
            # Security: Don't allow process to gain privileges
            start_new_session=False,
            text=True,  # Text mode for easier error handling
            bufsize=1   # Line buffered
        )
        
        # Generate scan ID (timestamp-based)
        scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Update GLOBAL state (CRITICAL: update dict, don't reassign!)
        current_scan["process"] = process
        current_scan["status"] = "running"
        current_scan["scan_id"] = scan_id
        current_scan["results_dir"] = None  # Will be set when scan completes
        current_scan["started_at"] = datetime.now().isoformat()
        current_scan["process_output"] = []
        current_scan["process_output_lock"] = threading.Lock()
        current_scan["step_counter"] = 0  # Reset step counter
        current_scan["step_names"] = {}  # Reset step names
        current_scan["error_code"] = None
        current_scan["error_message"] = None
        current_scan["container_ids"] = []  # Reset container IDs
        
        print(f"[Start Scan] Status set to 'running', scan_id={scan_id}, PID={process.pid}")
        
        # Start background task to capture process output
        asyncio.create_task(capture_process_output(process, scan_id, current_scan, results_dir))
        
        # Start background task to monitor process
        asyncio.create_task(monitor_scan(process, scan_id, current_scan, results_dir))
        
        # Get the current event loop to pass to the worker thread
        event_loop = asyncio.get_event_loop()
        
        # Create and start log worker thread - pass results_dir instead of None
        log_worker_thread = threading.Thread(
            target=log_worker_thread_func,
            args=(scan_id, results_dir, current_scan, event_loop),
            daemon=True
        )
        log_worker_thread.start()
        
        # Update the module-level variable
        import app.services.message_queue as mq
        mq.log_worker_thread = log_worker_thread
        
        print(f"[Start Scan] Started log worker thread for scan_id={scan_id}")
        
        return ScanStatus(
            status="running",
            scan_id=scan_id,
            started_at=current_scan["started_at"]
        )
    except Exception as e:
        current_scan["status"] = "error"
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


async def capture_process_output(process: subprocess.Popen, scan_id: str, current_scan: dict, results_dir: Path):
    """Capture stdout/stderr from run-docker.sh process and store for streaming"""
    try:
        print(f"[Process Output] Starting to capture output for scan {scan_id}, PID={process.pid}")
        # Read process output line by line
        while True:
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    # Process finished
                    return_code = process.poll()
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
                
                # Backend logs everything (no filtering)
                print(f"[Process Output] {clean_line}")
                
                # Extract steps for frontend (this also writes to steps.log)
                extract_steps_for_frontend(clean_line, current_scan, results_dir)
    except Exception as e:
        print(f"[Process Output Error] {e}")
        import traceback
        traceback.print_exc()


async def monitor_scan(process: subprocess.Popen, scan_id: str, current_scan: dict, results_dir: Path):
    """Monitor scan process and update status when done"""
    # Wait for process to complete
    return_code = process.wait()
    
    # If process exited unexpectedly (non-zero exit code that's not a normal scan error),
    # try to stop any orphaned containers
    if return_code != 0 and return_code not in [0, 1]:  # 1 might be a normal scan warning
        # Check if this looks like an unexpected termination (SIGTERM, SIGINT, etc.)
        if return_code in [130, 143, -15, -2]:  # SIGINT, SIGTERM
            print(f"[Monitor Scan] Process terminated unexpectedly (code {return_code}), cleaning up containers...")
            stop_running_containers(current_scan)
    
    # After process exits, wait a bit and check if scan is really done
    # by looking for completion markers in the log file
    await asyncio.sleep(2)  # Give logs time to flush
    
    # Check if scan is really complete by looking at log file
    log_file = None
    results_dir_path = None
    if results_dir.exists():
        # Look for scan directory matching pattern
        for scan_dir in sorted(results_dir.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                results_dir_path = str(scan_dir)
                log_file = scan_dir / "logs" / "security-check.log"
                break
    
    # If log file exists, check for completion markers
    scan_really_done = False
    if log_file and log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()
                # Check for completion markers
                if "SimpleSecCheck Docker Security Scan Completed" in log_content:
                    scan_really_done = True
                elif "Security scan completed" in log_content:
                    scan_really_done = True
                # If process exited with 0 and we have a results dir, assume done
                elif return_code == 0 and results_dir_path:
                    scan_really_done = True
        except Exception:
            # If we can't read the log, assume done if process exited successfully
            scan_really_done = (return_code == 0)
    else:
        # No log file yet - if process failed, it's done; if success, might still be running
        scan_really_done = (return_code != 0)
    
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
    
    # If results_dir wasn't found above, try again
    if not results_dir_path and results_dir.exists():
        for scan_dir in sorted(results_dir.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                results_dir_path = str(scan_dir)
                break
    
    # Update state based on whether scan is really done
    if scan_really_done:
        if return_code == 0:
            current_scan["status"] = "done"
            current_scan["results_dir"] = results_dir_path
            current_scan["error_code"] = None
            current_scan["error_message"] = None
        else:
            current_scan["status"] = "error"
            current_scan["results_dir"] = results_dir_path
            current_scan["error_code"] = return_code
            current_scan["error_message"] = error_message
    else:
        # Scan process exited but scan might still be running (e.g., docker-compose in background)
        # Keep status as "running" and let status endpoint check log file
        current_scan["status"] = "running"
        current_scan["results_dir"] = results_dir_path
        # Schedule a re-check in a few seconds
        asyncio.create_task(recheck_scan_status(scan_id, results_dir_path, return_code, error_message, current_scan, results_dir))
    
    # Schedule shutdown after scan if enabled (only if really done)
    if scan_really_done and SHUTDOWN_AFTER_SCAN and AUTO_SHUTDOWN_ENABLED:
        print(f"[Auto-Shutdown] Scan completed, will shutdown in {SHUTDOWN_DELAY}s...")
        schedule_shutdown(delay=SHUTDOWN_DELAY)


async def recheck_scan_status(scan_id: str, results_dir: Optional[str], return_code: int, error_message: Optional[str], current_scan: dict, results_dir_path: Path):
    """Re-check scan status after a delay to see if scan is really done"""
    # Wait a bit for logs to be written
    await asyncio.sleep(5)
    
    # Check log file for completion
    log_file = None
    if results_dir:
        log_file = Path(results_dir) / "logs" / "security-check.log"
    elif results_dir_path.exists():
        for scan_dir in sorted(results_dir_path.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                log_file = scan_dir / "logs" / "security-check.log"
                results_dir = str(scan_dir)
                break
    
    scan_done = False
    if log_file and log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()
                if "SimpleSecCheck Docker Security Scan Completed" in log_content:
                    scan_done = True
                elif "Security scan completed" in log_content:
                    scan_done = True
        except Exception:
            pass
    
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
        
        # Schedule shutdown if enabled
        if SHUTDOWN_AFTER_SCAN and AUTO_SHUTDOWN_ENABLED:
            print(f"[Auto-Shutdown] Scan completed, will shutdown in {SHUTDOWN_DELAY}s...")
            schedule_shutdown(delay=SHUTDOWN_DELAY)


async def get_scan_status(current_scan: dict, results_dir: Path) -> ScanStatus:
    """Get current scan status"""
    # Debug logging
    print(f"[Status Endpoint] Called: status={current_scan['status']}, scan_id={current_scan.get('scan_id')}, process={current_scan.get('process')}, process_alive={current_scan.get('process') is not None and current_scan.get('process').poll() is None if current_scan.get('process') else False}")
    
    # If status is "running", check if scan is really done by looking at log file
    if current_scan["status"] == "running" and current_scan["scan_id"]:
        results_dir_path = current_scan.get("results_dir")
        if not results_dir_path and results_dir.exists():
            # Try to find results directory
            for scan_dir in sorted(results_dir.iterdir(), reverse=True):
                if scan_dir.is_dir() and current_scan["scan_id"] in scan_dir.name:
                    results_dir_path = str(scan_dir)
                    break
        
        if results_dir_path:
            log_file = Path(results_dir_path) / "logs" / "security-check.log"
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        log_content = f.read()
                        if "SimpleSecCheck Docker Security Scan Completed" in log_content:
                            current_scan["status"] = "done"
                            current_scan["results_dir"] = results_dir_path
                except Exception:
                    pass
    
    status_response = ScanStatus(
        status=current_scan["status"],
        scan_id=current_scan["scan_id"],
        results_dir=current_scan["results_dir"],
        started_at=current_scan["started_at"],
        error_code=current_scan.get("error_code"),
        error_message=current_scan.get("error_message")
    )
    
    print(f"[Status Endpoint] Returning: status={status_response.status}, scan_id={status_response.scan_id}")
    
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
    
    return ScanStatus(
        status="error",
        scan_id=current_scan["scan_id"],
        results_dir=current_scan["results_dir"],
        started_at=current_scan["started_at"],
        error_code=130,
        error_message="Scan was stopped by user"
    )
