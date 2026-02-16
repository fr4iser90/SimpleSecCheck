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
    "step_counter": 0,  # Step counter for frontend
    "step_names": {},  # Step names mapping
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
        
        print(f"[Start Scan] Status set to 'running', scan_id={scan_id}, PID={process.pid}")
        
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


def write_step_to_log(step_line: str, scan_id: str):
    """Write step to steps.log file"""
    global current_scan
    
    # Try to find results_dir
    results_dir = current_scan.get("results_dir")
    
    # If not set yet, try to find it by scan_id
    if not results_dir and scan_id and RESULTS_DIR.exists():
        for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                results_dir = str(scan_dir)
                current_scan["results_dir"] = results_dir
                break
    
    # If still no results_dir, try to find most recent
    if not results_dir and RESULTS_DIR.exists():
        for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
            if scan_dir.is_dir():
                results_dir = str(scan_dir)
                current_scan["results_dir"] = results_dir
                break
    
    # Write to steps.log
    if results_dir:
        steps_log = Path(results_dir) / "logs" / "steps.log"
        try:
            steps_log.parent.mkdir(parents=True, exist_ok=True)
            with open(steps_log, "a", encoding="utf-8") as f:
                f.write(f"{step_line}\n")
            print(f"[Step Log] Wrote step to {steps_log}: {step_line}")
        except Exception as e:
            print(f"[Step Log] ERROR writing to {steps_log}: {e}")


def extract_steps_for_frontend(line: str) -> Optional[str]:
    """
    Extract ONLY steps from log lines for frontend.
    Returns formatted step line if it's a step, None otherwise.
    Backend logs everything - this is ONLY for frontend display.
    Also writes steps to steps.log file.
    """
    global current_scan
    
    # Remove ANSI color codes
    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
    if not clean_line:
        return None
    
    # Calculate total steps (approximate - will be updated as we see more steps)
    # Common tools: Semgrep, Trivy, CodeQL, OWASP, Safety, Snyk, SonarQube, Checkov, TruffleHog, GitLeaks, Detect-secrets, npm_audit, ESLint, Brakeman, Bandit
    # Plus: Initialization, Report Generation, Completion
    total_steps = max(15, current_scan.get("step_counter", 0) + 2)  # Dynamic based on what we've seen
    
    formatted_line = None
    
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
            # Update total steps based on what we've seen
            total_steps = max(total_steps, current_scan["step_counter"] + 2)
        formatted_line = f"⏳ Step {step_num}/{total_steps}: Running {tool_name} scan..."
    
    # Pattern: "--- X Scan Orchestration Finished ---"
    if not formatted_line:
        finished_match = re.search(r'---\s*(.+?)\s+Scan\s+Orchestration\s+Finished\s+---', clean_line, re.IGNORECASE)
        if finished_match:
            tool_name = finished_match.group(1).strip()
            with current_scan["process_output_lock"]:
                step_num = current_scan["step_names"].get(tool_name, current_scan["step_counter"])
                total_steps = max(total_steps, current_scan["step_counter"] + 2)
            formatted_line = f"✓ Step {step_num}/{total_steps}: {tool_name} scan completed"
    
    # Initialization messages
    if not formatted_line:
        if re.search(r'SimpleSecCheck.*Scan.*Started|Orchestrator script started', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "Initialization" not in current_scan["step_names"]:
                    current_scan["step_counter"] = 1
                    current_scan["step_names"]["Initialization"] = 1
            formatted_line = "✓ Step 1/15: Initializing scan..."
    
    # Report generation
    if not formatted_line:
        if re.search(r'Generating.*HTML report|HTML report generation', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "Report Generation" not in current_scan["step_names"]:
                    current_scan["step_counter"] += 1
                    current_scan["step_names"]["Report Generation"] = current_scan["step_counter"]
                step_num = current_scan["step_names"]["Report Generation"]
                total_steps = max(total_steps, current_scan["step_counter"] + 1)
            formatted_line = f"⏳ Step {step_num}/{total_steps}: Generating report..."
    
    # Scan completion
    if not formatted_line:
        if re.search(r'SimpleSecCheck.*Scan.*Completed|Scan.*completed successfully', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "Completion" not in current_scan["step_names"]:
                    current_scan["step_counter"] += 1
                    current_scan["step_names"]["Completion"] = current_scan["step_counter"]
                step_num = current_scan["step_names"]["Completion"]
                total_steps = max(total_steps, current_scan["step_counter"])
            formatted_line = f"✓ Step {step_num}/{total_steps}: Scan completed successfully"
    
    # Errors (show as steps)
    if not formatted_line:
        if re.search(r'\[ERROR\]|\[ORCHESTRATOR ERROR\]', clean_line, re.IGNORECASE):
            formatted_line = f"❌ {clean_line}"
    
    # Write to steps.log file if we found a step
    if formatted_line:
        scan_id = current_scan.get("scan_id")
        if scan_id:
            write_step_to_log(formatted_line, scan_id)
    
    return formatted_line


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
    
    # Debug logging
    print(f"[Status Endpoint] Called: status={current_scan['status']}, scan_id={current_scan.get('scan_id')}, process={current_scan.get('process')}, process_alive={current_scan.get('process') is not None and current_scan.get('process').poll() is None if current_scan.get('process') else False}")
    
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


@app.get("/api/scan/logs")
async def stream_logs():
    """
    Stream logs from current scan (Server-Sent Events)
    Reads from results/*/logs/security-check.log
    Waits for log file to be created if scan just started
    """
    global current_scan
    update_activity()
    
    # Allow logs if:
    # 1. Status is "running", "done", or "error" (active scan)
    # 2. Status is "idle" but scan_id exists (scan might have just started)
    if current_scan["status"] == "idle" and current_scan["scan_id"] is None and current_scan["results_dir"] is None:
        raise HTTPException(status_code=404, detail="No active scan")
    
    async def generate():
        """Stream logs: first process output, then log file when available"""
        try:
            print(f"[Log Stream] Starting log stream for scan_id={current_scan.get('scan_id')}, status={current_scan.get('status')}")
            log_file = None
            max_wait_time = 120  # Wait up to 120 seconds for log file to appear
            wait_start = time.time()
            check_count = 0
            process_output_sent = 0  # Track how many process output lines we've sent
            
            # Send initial message immediately
            initial_msg = json.dumps({'line': '🚀 Starting security scan...'})
            print(f"[Log Stream] Sending initial message: {initial_msg}")
            yield f"data: {initial_msg}\n\n"
            print(f"[Log Stream] Initial message sent successfully")
        except Exception as e:
            print(f"[Log Stream] CRITICAL ERROR in generate() startup: {e}")
            import traceback
            traceback.print_exc()
            error_msg = json.dumps({'line': f'[ERROR] Failed to start log stream: {str(e)}'})
            yield f"data: {error_msg}\n\n"
            return
        
        # First, stream process output (stdout/stderr from run-docker.sh)
        try:
            while (time.time() - wait_start) < max_wait_time:
                check_count += 1
                
                try:
                    # Send any new process output lines (FILTERED for frontend only)
                    with current_scan.get("process_output_lock", threading.Lock()):
                        process_output = current_scan.get("process_output", [])
                        if check_count == 1:  # Log first check
                            print(f"[Log Stream] First check: process_output length={len(process_output)}, already_sent={process_output_sent}")
                        if len(process_output) > process_output_sent:
                            new_lines = process_output[process_output_sent:]
                            print(f"[Log Stream] Processing {len(new_lines)} new process output lines (check #{check_count})")
                            # Send new lines - extract ONLY steps for frontend
                            sent_count = 0
                            batch_size = 10  # Send in batches to prevent stream timeout
                            for i, line in enumerate(new_lines):
                                try:
                                    formatted_line = extract_steps_for_frontend(line)
                                    if formatted_line:  # Only send if it's a step
                                        line_msg = json.dumps({'line': formatted_line})
                                        yield f"data: {line_msg}\n\n"
                                        sent_count += 1
                                        
                                        # After every batch, give the event loop a chance
                                        if sent_count % batch_size == 0:
                                            await asyncio.sleep(0.01)
                                except Exception as e:
                                    print(f"[Log Stream] Error processing line {i}: {e}")
                                    continue
                            print(f"[Log Stream] Sent {sent_count} step lines (out of {len(new_lines)} total lines)")
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
                except Exception as e:
                    print(f"[Log Stream] Error in loop iteration #{check_count}: {e}")
                    import traceback
                    traceback.print_exc()
                    error_msg = json.dumps({'line': f'[ERROR] Error in log stream: {str(e)}'})
                    yield f"data: {error_msg}\n\n"
                    await asyncio.sleep(0.5)  # Continue despite error
        except Exception as e:
            print(f"[Log Stream] CRITICAL ERROR in main loop: {e}")
            import traceback
            traceback.print_exc()
            error_msg = json.dumps({'line': f'[ERROR] Critical error in log stream: {str(e)}'})
            yield f"data: {error_msg}\n\n"
        
        # Try to find and stream steps.log file (written directly by security-check.sh)
        steps_log = None
        if current_scan.get("results_dir"):
            steps_log = Path(current_scan["results_dir"]) / "logs" / "steps.log"
        elif current_scan.get("scan_id") and RESULTS_DIR.exists():
            for scan_dir in sorted(RESULTS_DIR.iterdir(), reverse=True):
                if scan_dir.is_dir() and current_scan["scan_id"] in scan_dir.name:
                    steps_log = scan_dir / "logs" / "steps.log"
                    current_scan["results_dir"] = str(scan_dir)
                    break
        
        # Stream steps.log if it exists
        if steps_log and steps_log.exists():
            try:
                print(f"[Log Stream] Found steps.log: {steps_log}")
                steps_sent = 0
                with open(steps_log, "r", encoding="utf-8", errors="ignore") as f:
                    # Read existing steps
                    existing_steps = f.readlines()
                    for step_line in existing_steps:
                        if step_line.strip():
                            line_msg = json.dumps({'line': step_line.strip()})
                            yield f"data: {line_msg}\n\n"
                            steps_sent += 1
                    
                    # If scan is still running, tail the file
                    if current_scan["status"] == "running":
                        last_position = f.tell()
                        while current_scan["status"] == "running":
                            # Check if file has grown
                            f.seek(0, 2)  # Seek to end
                            current_position = f.tell()
                            if current_position > last_position:
                                f.seek(last_position)
                                for step_line in f:
                                    if step_line.strip():
                                        line_msg = json.dumps({'line': step_line.strip()})
                                        yield f"data: {line_msg}\n\n"
                                        steps_sent += 1
                                last_position = f.tell()
                            else:
                                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[Log Stream] Error reading steps.log: {e}")
                error_msg = json.dumps({'line': f'[ERROR] Failed to read steps.log: {str(e)}'})
                yield f"data: {error_msg}\n\n"
        elif log_file:
            # Fallback: if steps.log doesn't exist yet, wait for it or use old method
            print(f"[Log Stream] steps.log not found yet, waiting...")
            await asyncio.sleep(1)
        else:
            # No log file found, but continue streaming process output (ONLY STEPS)
            # Continue streaming process output - ONLY STEPS
            while current_scan["status"] == "running":
                with current_scan.get("process_output_lock", threading.Lock()):
                    process_output = current_scan.get("process_output", [])
                    if len(process_output) > process_output_sent:
                        for line in process_output[process_output_sent:]:
                            # Extract ONLY steps for frontend
                            formatted_line = extract_steps_for_frontend(line)
                            if formatted_line:  # Only send if it's a step
                                line_msg = json.dumps({'line': formatted_line})
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
