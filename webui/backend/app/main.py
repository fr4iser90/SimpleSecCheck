#!/usr/bin/env python3
"""
SimpleSecCheck WebUI Backend
Minimal FastAPI backend that wraps the CLI (bin/run-docker.sh)
Single-shot principle: No database, no state, just CLI wrapper
"""

import os
import subprocess
import asyncio
import signal
import time
import threading
import re
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configuration
# Try multiple paths for flexibility (dev vs production)
BASE_DIR = Path(__file__).parent.parent.parent.parent  # SimpleSecCheck root
if not (BASE_DIR / "bin" / "run-docker.sh").exists():
    # Try alternative path (when running in container)
    BASE_DIR = Path("/app")

CLI_SCRIPT = BASE_DIR / "bin" / "run-docker.sh"
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"

# Validate CLI script exists
if not CLI_SCRIPT.exists():
    raise RuntimeError(f"CLI script not found: {CLI_SCRIPT}")

# Auto-shutdown configuration
AUTO_SHUTDOWN_ENABLED = os.getenv("WEBUI_AUTO_SHUTDOWN", "true").lower() == "true"
SHUTDOWN_AFTER_SCAN = os.getenv("WEBUI_SHUTDOWN_AFTER_SCAN", "true").lower() == "true"
SHUTDOWN_DELAY = int(os.getenv("WEBUI_SHUTDOWN_DELAY", "300"))  # 5 minutes default
IDLE_TIMEOUT = int(os.getenv("WEBUI_IDLE_TIMEOUT", "1800"))  # 30 minutes default

# Track last activity for idle timeout
last_activity = time.time()
shutdown_scheduled = False

app = FastAPI(title="SimpleSecCheck WebUI", version="1.0.0")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for current scan (minimal, no DB)
current_scan = {
    "process": None,
    "status": "idle",  # idle, running, done, error
    "scan_id": None,
    "results_dir": None,
    "started_at": None,
    "error_code": None,
    "error_message": None,
    "process_output": [],  # Store process stdout/stderr lines for streaming
    "process_output_lock": threading.Lock(),  # Lock for thread-safe access
}


def update_activity():
    """Update last activity timestamp"""
    global last_activity
    last_activity = time.time()


def schedule_shutdown(delay: int = 0):
    """Schedule graceful shutdown"""
    global shutdown_scheduled
    
    if shutdown_scheduled or not AUTO_SHUTDOWN_ENABLED:
        return
    
    shutdown_scheduled = True
    
    def shutdown():
        time.sleep(delay)
        print(f"[Auto-Shutdown] Shutting down after {delay}s delay...")
        os.kill(os.getpid(), signal.SIGTERM)
    
    threading.Thread(target=shutdown, daemon=True).start()


def idle_timeout_checker():
    """Background thread to check idle timeout"""
    if not AUTO_SHUTDOWN_ENABLED or IDLE_TIMEOUT <= 0:
        return
    
    while True:
        time.sleep(60)  # Check every minute
        idle_time = time.time() - last_activity
        
        # Don't shutdown if a scan is running
        if current_scan["status"] == "running":
            continue
        
        if idle_time > IDLE_TIMEOUT and not shutdown_scheduled:
            print(f"[Auto-Shutdown] Idle timeout ({IDLE_TIMEOUT}s) reached, shutting down...")
            schedule_shutdown(delay=10)  # 10 second grace period
            break


# Start idle timeout checker
if AUTO_SHUTDOWN_ENABLED and IDLE_TIMEOUT > 0:
    threading.Thread(target=idle_timeout_checker, daemon=True).start()


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


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    update_activity()
    return {"status": "ok", "service": "SimpleSecCheck WebUI"}


@app.post("/api/scan/start", response_model=ScanStatus)
async def start_scan(request: ScanRequest):
    """
    Start a scan by calling bin/run-docker.sh
    Single-shot: Only one scan at a time
    """
    global current_scan
    update_activity()
    
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
    cmd = [str(CLI_SCRIPT)]
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
            cwd=str(BASE_DIR),
            env=os.environ.copy(),
            # Security: Run as current user (non-root), no shell
            shell=False,
            # Security: Don't allow process to gain privileges
            start_new_session=False,
            text=True,  # Text mode for easier error handling
            bufsize=1   # Line buffered
        )
        
        # Generate scan ID (timestamp-based)
        from datetime import datetime
        scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Update state
        current_scan = {
            "process": process,
            "status": "running",
            "scan_id": scan_id,
            "results_dir": None,  # Will be set when scan completes
            "started_at": datetime.now().isoformat(),
            "process_output": [],
            "process_output_lock": threading.Lock(),
            "step_counter": 0,  # Reset step counter
            "step_names": {},  # Reset step names
        }
        
        # Start background task to capture process output
        asyncio.create_task(capture_process_output(process, scan_id))
        
        # Start background task to monitor process
        asyncio.create_task(monitor_scan(process, scan_id))
        
        return ScanStatus(
            status="running",
            scan_id=scan_id,
            started_at=current_scan["started_at"]
        )
    except Exception as e:
        current_scan["status"] = "error"
        raise HTTPException(status_code=500, detail=f"Failed to start scan: {str(e)}")


def filter_and_format_log_line(line: str) -> Optional[str]:
    """
    Filter and format log lines to show only relevant scan steps.
    Returns None if line should be filtered out, or formatted line if it should be shown.
    """
    global current_scan
    
    # Remove ANSI color codes
    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
    if not clean_line:
        return None
    
    # Filter out Docker build logs
    docker_build_patterns = [
        r'^Building\s',
        r'^Step\s+\d+/\d+',
        r'^Image\s+',
        r'unable to prepare context',
        r'Docker Compose requires buildx',
        r'level=warning.*buildx',
        r'^\s*-->',
        r'^\s*RUN\s+',
        r'^\s*COPY\s+',
        r'^\s*FROM\s+',
    ]
    for pattern in docker_build_patterns:
        if re.search(pattern, clean_line, re.IGNORECASE):
            return None
    
    # Filter out verbose Docker Compose output
    if re.search(r'^Network\s+.*\s(Creating|Created|Removing|Removed)', clean_line):
        return None
    
    # Filter out CodeQL extraction logs (these are normal, not errors)
    # These come from unzip/tar extraction during CodeQL setup
    # Match patterns like "inflating: /opt/codeql/..." or "creating: /opt/codeql/..."
    if re.search(r'(inflating|creating|extracting):\s+/opt/codeql', clean_line, re.IGNORECASE):
        return None
    if re.search(r'^FINISHED\s+--', clean_line, re.IGNORECASE):
        return None
    
    # Extract scan steps from orchestrator messages
    # Pattern: "--- Orchestrating X Scan ---"
    orchestrating_match = re.search(r'---\s*Orchestrating\s+(.+?)\s+Scan\s+---', clean_line, re.IGNORECASE)
    if orchestrating_match:
        tool_name = orchestrating_match.group(1).strip()
        with current_scan["process_output_lock"]:
            if tool_name not in current_scan["step_names"]:
                current_scan["step_counter"] += 1
                current_scan["step_names"][tool_name] = current_scan["step_counter"]
            step_num = current_scan["step_names"][tool_name]
        return f"⏳ Step {step_num}: Running {tool_name} scan..."
    
    # Pattern: "--- X Scan Orchestration Finished ---"
    finished_match = re.search(r'---\s*(.+?)\s+Scan\s+Orchestration\s+Finished\s+---', clean_line, re.IGNORECASE)
    if finished_match:
        tool_name = finished_match.group(1).strip()
        with current_scan["process_output_lock"]:
            step_num = current_scan["step_names"].get(tool_name, current_scan["step_counter"])
        return f"✓ Step {step_num}: {tool_name} scan completed"
    
    # Pattern: "Executing .../run_X.sh..."
    executing_match = re.search(r'Executing\s+.*/run_(\w+)\.sh', clean_line, re.IGNORECASE)
    if executing_match:
        # This is already covered by "Orchestrating", so we can skip or show as in-progress
        return None
    
    # Pattern: "run_X.sh completed successfully"
    completed_match = re.search(r'run_(\w+)\.sh\s+completed\s+successfully', clean_line, re.IGNORECASE)
    if completed_match:
        # This is already covered by "Finished", so we can skip
        return None
    
    # Initialization messages
    if re.search(r'SimpleSecCheck.*Scan.*Started|Orchestrator script started', clean_line, re.IGNORECASE):
        with current_scan["process_output_lock"]:
            if "Initialization" not in current_scan["step_names"]:
                current_scan["step_counter"] = 1
                current_scan["step_names"]["Initialization"] = 1
        return "✓ Step 1: Initializing scan..."
    
    # Report generation
    if re.search(r'Generating.*HTML report|HTML report generation', clean_line, re.IGNORECASE):
        with current_scan["process_output_lock"]:
            if "Report Generation" not in current_scan["step_names"]:
                current_scan["step_counter"] += 1
                current_scan["step_names"]["Report Generation"] = current_scan["step_counter"]
            step_num = current_scan["step_names"]["Report Generation"]
        return f"⏳ Step {step_num}: Generating report..."
    
    # Scan completion
    if re.search(r'SimpleSecCheck.*Scan.*Completed|Scan.*completed successfully', clean_line, re.IGNORECASE):
        with current_scan["process_output_lock"]:
            if "Completion" not in current_scan["step_names"]:
                current_scan["step_counter"] += 1
                current_scan["step_names"]["Completion"] = current_scan["step_counter"]
            step_num = current_scan["step_names"]["Completion"]
        return f"✓ Step {step_num}: Scan completed successfully"
    
    # Error messages (always show) - but be careful not to match paths or normal output
    # Only match actual error indicators, not words that happen to contain "error"
    error_patterns = [
        r'\[ERROR\]',
        r'\[ORCHESTRATOR ERROR\]',
        r'\berror:\s+',  # "error: " at word boundary
        r'\bfailed\b',  # "failed" as whole word
        r'\bfailure\b',  # "failure" as whole word
        r'command not found',
        r'permission denied',
        r'cannot.*create|cannot.*access|cannot.*find',
    ]
    for pattern in error_patterns:
        if re.search(pattern, clean_line, re.IGNORECASE):
            return f"❌ {clean_line}"
    
    # Warnings (show but mark as warning)
    if re.search(r'\[WARNING\]|\[WARN\]|warning', clean_line, re.IGNORECASE):
        return f"⚠️  {clean_line}"
    
    # Skip other verbose output (tool-specific logs, etc.)
    # Only show high-level orchestrator messages
    if re.search(r'^\[SimpleSecCheck|^Orchestrating|^Executing|^completed|^Finished', clean_line, re.IGNORECASE):
        return clean_line
    
    # Filter out everything else (too verbose)
    return None


async def capture_process_output(process: subprocess.Popen, scan_id: str):
    """Capture stdout/stderr from run-docker.sh process and store for streaming"""
    global current_scan
    
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
    except Exception as e:
        print(f"[Process Output Error] {e}")
        import traceback
        traceback.print_exc()


async def monitor_scan(process: subprocess.Popen, scan_id: str):
    """Monitor scan process and update status when done"""
    global current_scan
    
    # Wait for process to complete
    return_code = process.wait()
    
    # After process exits, wait a bit and check if scan is really done
    # by looking for completion markers in the log file
    await asyncio.sleep(2)  # Give logs time to flush
    
    # Check if scan is really complete by looking at log file
    log_file = None
    results_dir = None
    if RESULTS_DIR.exists():
        # Look for scan directory matching pattern
        for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                results_dir = str(scan_dir)
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
                elif return_code == 0 and results_dir:
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
    if not results_dir and RESULTS_DIR.exists():
        for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                results_dir = str(scan_dir)
                break
    
    # Update state based on whether scan is really done
    if scan_really_done:
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
    else:
        # Scan process exited but scan might still be running (e.g., docker-compose in background)
        # Keep status as "running" and let status endpoint check log file
        current_scan["status"] = "running"
        current_scan["results_dir"] = results_dir
        # Schedule a re-check in a few seconds
        asyncio.create_task(recheck_scan_status(scan_id, results_dir, return_code, error_message))
    
    # Schedule shutdown after scan if enabled (only if really done)
    if scan_really_done and SHUTDOWN_AFTER_SCAN and AUTO_SHUTDOWN_ENABLED:
        print(f"[Auto-Shutdown] Scan completed, will shutdown in {SHUTDOWN_DELAY}s...")
        schedule_shutdown(delay=SHUTDOWN_DELAY)


async def recheck_scan_status(scan_id: str, results_dir: Optional[str], return_code: int, error_message: Optional[str]):
    """Re-check scan status after a delay to see if scan is really done"""
    global current_scan
    
    # Wait a bit for logs to be written
    await asyncio.sleep(5)
    
    # Check log file for completion
    log_file = None
    if results_dir:
        log_file = Path(results_dir) / "logs" / "security-check.log"
    elif RESULTS_DIR.exists():
        for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
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


@app.get("/api/scan/status", response_model=ScanStatus)
async def get_scan_status():
    """Get current scan status"""
    global current_scan
    update_activity()
    
    # If status is "running", check if scan is really done by looking at log file
    if current_scan["status"] == "running" and current_scan["scan_id"]:
        results_dir = current_scan.get("results_dir")
        if not results_dir and RESULTS_DIR.exists():
            # Try to find results directory
            for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
                if scan_dir.is_dir() and current_scan["scan_id"] in scan_dir.name:
                    results_dir = str(scan_dir)
                    break
        
        if results_dir:
            log_file = Path(results_dir) / "logs" / "security-check.log"
            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                        log_content = f.read()
                        if "SimpleSecCheck Docker Security Scan Completed" in log_content:
                            current_scan["status"] = "done"
                            current_scan["results_dir"] = results_dir
                except Exception:
                    pass
    
    return ScanStatus(
        status=current_scan["status"],
        scan_id=current_scan["scan_id"],
        results_dir=current_scan["results_dir"],
        started_at=current_scan["started_at"],
        error_code=current_scan.get("error_code"),
        error_message=current_scan.get("error_message")
    )


@app.get("/api/scan/logs")
async def stream_logs():
    """
    Stream logs from current scan (Server-Sent Events)
    Reads from results/*/logs/security-check.log
    Waits for log file to be created if scan just started
    """
    global current_scan
    update_activity()
    
    # Allow logs even if status is "done" but scan might still be running
    if current_scan["status"] == "idle" and current_scan["results_dir"] is None:
        raise HTTPException(status_code=404, detail="No active scan")
    
    async def generate():
        """Stream logs: first process output, then log file when available"""
        log_file = None
        max_wait_time = 120  # Wait up to 120 seconds for log file to appear
        wait_start = time.time()
        check_count = 0
        process_output_sent = 0  # Track how many process output lines we've sent
        
        # First, stream process output (stdout/stderr from run-docker.sh)
        while (time.time() - wait_start) < max_wait_time:
            check_count += 1
            
            # Send any new process output lines (FILTERED for frontend only)
            with current_scan.get("process_output_lock", threading.Lock()):
                process_output = current_scan.get("process_output", [])
                if len(process_output) > process_output_sent:
                    # Send new lines (filtered for frontend)
                    for line in process_output[process_output_sent:]:
                        formatted_line = filter_and_format_log_line(line)
                        if formatted_line:  # Only send if filter allows it
                            line_msg = json.dumps({'line': formatted_line})
                            yield f"data: {line_msg}\n\n"
                    process_output_sent = len(process_output)
            
            # Try to find log file
            if current_scan["results_dir"]:
                potential_log = Path(current_scan["results_dir"]) / "logs" / "security-check.log"
                if potential_log.exists():
                    log_file = potential_log
                    print(f"[Log Stream] Found log file via results_dir: {log_file}")
                    break
            
            # Try to find log file by scan_id
            if not log_file and current_scan["scan_id"] and RESULTS_DIR.exists():
                for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
                    if scan_dir.is_dir() and current_scan["scan_id"] in scan_dir.name:
                        potential_log = scan_dir / "logs" / "security-check.log"
                        if potential_log.exists():
                            log_file = potential_log
                            current_scan["results_dir"] = str(scan_dir)
                            print(f"[Log Stream] Found log file by scan_id: {log_file}")
                            break
            
            # Fallback: find most recent log file
            if not log_file and RESULTS_DIR.exists():
                for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
                    if scan_dir.is_dir():
                        potential_log = scan_dir / "logs" / "security-check.log"
                        if potential_log.exists():
                            try:
                                file_time = potential_log.stat().st_mtime
                                if time.time() - file_time < 300:  # 5 minutes
                                    log_file = potential_log
                                    current_scan["results_dir"] = str(scan_dir)
                                    print(f"[Log Stream] Found recent log file: {log_file}")
                                    break
                            except Exception:
                                pass
            
            # If we found the log file, break
            if log_file:
                break
            
            # If no new output and no log file, wait a bit
            await asyncio.sleep(0.5)
        
        # If log file found, stream it
        if log_file:
            try:
                # Read existing content from log file
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    existing_content = f.read()
                    if existing_content:
                        # Send existing log content (filtered)
                        for line in existing_content.split('\n'):
                            if line.strip():
                                formatted_line = filter_and_format_log_line(line)
                                if formatted_line:
                                    line_msg = json.dumps({'line': formatted_line})
                                    yield f"data: {line_msg}\n\n"
                    
                    # If scan is still running, tail the file
                    if current_scan["status"] == "running":
                        last_position = f.tell()
                        while current_scan["status"] == "running":
                            # Check if file has grown
                            f.seek(0, 2)  # Seek to end
                            current_position = f.tell()
                            if current_position > last_position:
                                f.seek(last_position)
                                for line in f:
                                    if line.strip():
                                        formatted_line = filter_and_format_log_line(line)
                                        if formatted_line:
                                            line_msg = json.dumps({'line': formatted_line})
                                            yield f"data: {line_msg}\n\n"
                                last_position = f.tell()
                            else:
                                await asyncio.sleep(0.5)
            except Exception as e:
                error_msg = json.dumps({'line': f'[ERROR] Failed to read log file: {str(e)}'})
                yield f"data: {error_msg}\n\n"
        else:
            # No log file found, but continue streaming process output
            error_msg = json.dumps({'line': '[WARNING] Log file not found, streaming process output only'})
            yield f"data: {error_msg}\n\n"
            
            # Continue streaming process output
            while current_scan["status"] == "running":
                with current_scan.get("process_output_lock", threading.Lock()):
                    process_output = current_scan.get("process_output", [])
                    if len(process_output) > process_output_sent:
                        for line in process_output[process_output_sent:]:
                            line_msg = json.dumps({'line': line})
                            yield f"data: {line_msg}\n\n"
                        process_output_sent = len(process_output)
                await asyncio.sleep(0.5)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/scan/report")
async def get_report():
    """Get HTML report from current scan"""
    global current_scan
    update_activity()
    
    if current_scan["results_dir"] is None:
        raise HTTPException(status_code=404, detail="No scan results available")
    
    report_file = Path(current_scan["results_dir"]) / "security-summary.html"
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        report_file,
        media_type="text/html",
        headers={"Content-Disposition": "inline"}
    )


@app.get("/api/results")
async def list_results():
    """
    List all scan results (file browser)
    No database - just reads results/ directory
    """
    update_activity()
    if not RESULTS_DIR.exists():
        return {"scans": []}
    
    scans = []
    for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
        if scan_dir.is_dir():
            report_file = scan_dir / "security-summary.html"
            scans.append({
                "id": scan_dir.name,
                "timestamp": scan_dir.name,
                "has_report": report_file.exists(),
                "report_path": f"/api/results/{scan_dir.name}/report" if report_file.exists() else None
            })
    
    return {"scans": scans}


@app.get("/api/results/{scan_id}/report")
async def get_result_report(scan_id: str):
    """Get HTML report from specific scan"""
    report_file = RESULTS_DIR / scan_id / "security-summary.html"
    
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        report_file,
        media_type="text/html",
        headers={"Content-Disposition": "inline"}
    )


# Serve frontend static files (after API routes)
# Try multiple paths (dev vs production)
frontend_paths = [
    BASE_DIR / "webui" / "frontend" / "dist",
    BASE_DIR / "static",  # For docker-compose build
    Path("/app/static"),   # For docker container
]

for frontend_dir in frontend_paths:
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
        break


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
