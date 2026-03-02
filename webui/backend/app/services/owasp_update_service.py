"""
OWASP Dependency Check Update Service
Handles database updates with live log streaming
"""
import os
import subprocess  # nosec B404 - Used safely with hardcoded commands, shell=False
import asyncio
import re
import threading
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from fastapi import HTTPException
from pydantic import BaseModel


class UpdateStatus(BaseModel):
    status: str  # idle, running, done, error
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    database_age_days: Optional[int] = None  # Age of database files in days
    database_exists: Optional[bool] = None  # Whether database directory exists


# Global state for OWASP update (similar to scan state)
current_update = {
    "process": None,
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "error_code": None,
    "error_message": None,
    "process_output": [],
    "process_output_lock": threading.Lock(),
    "update_log_file": None,  # Path to update log file
}


async def start_update(
    base_dir: Path,
    owasp_data_dir: Path,
):
    """
    Start OWASP Dependency Check database update
    """
    # Check if update is already running
    if current_update["status"] == "running":
        raise HTTPException(status_code=409, detail="Update already in progress")
    
    # Check if Docker or docker-compose is available
    docker_available = False
    docker_compose_available = False
    
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True, timeout=5)  # nosec B603, B607
        docker_available = True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    try:
        subprocess.run(["docker-compose", "--version"], check=True, capture_output=True, timeout=5)  # nosec B603, B607
        docker_compose_available = True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    if not docker_available and not docker_compose_available:
        raise HTTPException(status_code=500, detail="Neither docker nor docker-compose is available")
    
    # Get host project root for volume mounting (when running in container)
    host_project_root = os.getenv("HOST_PROJECT_ROOT", "")
    if host_project_root:
        # We're in a container, use host path for volume mounting
        # Don't try to create it - it's on the host, not in the container
        # Docker/docker-compose will create it automatically when mounting
        host_owasp_dir = Path(host_project_root) / "owasp-dependency-check-data"
    else:
        # Running on host, use provided path directly
        host_owasp_dir = owasp_data_dir
        # Only create directory if running on host (not in container)
        try:
            host_owasp_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            # If we can't create it, that's okay - docker/docker-compose will handle it
            print(f"[OWASP Update] Warning: Could not create directory {host_owasp_dir}: {e}")
    
    # Prepare update
    current_update["status"] = "running"
    current_update["started_at"] = datetime.now().isoformat()
    current_update["finished_at"] = None
    current_update["error_code"] = None
    current_update["error_message"] = None
    current_update["process_output"] = []
    
    # Create log file - use tempfile.mkstemp() for secure temp file creation
    # Logs are stored in memory anyway (process_output), so file is just for backup
    fd, temp_path = tempfile.mkstemp(prefix='owasp-update-', suffix='.log', dir='/tmp')
    os.close(fd)  # Close file descriptor, we'll open it later if needed
    update_log_file = Path(temp_path)
    current_update["update_log_file"] = update_log_file
    
    # Get NVD API key from environment
    nvd_api_key = os.getenv("NVD_API_KEY", "")
    docker_image = os.getenv("DOCKER_IMAGE", "fr4iser/simpleseccheck:latest")
    
    # Add initial status message about API key
    api_key_status = "with NVD API key (faster)" if nvd_api_key else "without NVD API key (slower, using public rate limits)"
    initial_message = f"[OWASP Update] Starting database update {api_key_status}..."
    with current_update["process_output_lock"]:
        current_update["process_output"].append(initial_message)
    print(initial_message)
    
    # Build command - prefer docker-compose if available (for WebUI container)
    if docker_compose_available:
        # Use docker-compose run (works in WebUI container)
        # Use central function from path_setup (handles dev/prod automatically)
        import sys
        sys.path.insert(0, "/app/scanner")
        from core.path_setup import get_docker_compose_file, get_docker_compose_context
        docker_compose_file = get_docker_compose_file()
        docker_compose_context = get_docker_compose_context()
        
        docker_cmd = [
            "docker-compose",
            "-f", docker_compose_file,
            "run", "--rm",
            "-v", f"{host_owasp_dir}:/SimpleSecCheck/owasp-dependency-check-data",
        ]
        
        # Add NVD_API_KEY as environment variable if provided
        if nvd_api_key:
            docker_cmd.extend(["-e", f"NVD_API_KEY={nvd_api_key}"])
        
        docker_cmd.extend([
            "scanner",
            "dependency-check",
            "--updateonly",
            "--data", "/SimpleSecCheck/owasp-dependency-check-data",
        ])
        
        # Add nvdApiKey flag to dependency-check command if provided
        if nvd_api_key:
            docker_cmd.extend(["--nvdApiKey", nvd_api_key])
    else:
        # Fallback to docker run (if docker CLI is available)
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{host_owasp_dir}:/SimpleSecCheck/owasp-dependency-check-data",
        ]
        
        if nvd_api_key:
            docker_cmd.extend(["-e", f"NVD_API_KEY={nvd_api_key}"])
        
        docker_cmd.extend([
            docker_image,
            "dependency-check",
            "--updateonly",
            "--data", "/SimpleSecCheck/owasp-dependency-check-data",
        ])
        
        if nvd_api_key:
            docker_cmd.extend(["--nvdApiKey", nvd_api_key])
    
    try:
        # Start update process
        process = subprocess.Popen(  # nosec B603, B607
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(base_dir),
        )
        
        current_update["process"] = process
        
        # Start capturing output in background
        asyncio.create_task(capture_update_output(process, update_log_file))
        
        # Start monitoring in background
        asyncio.create_task(monitor_update(process))
        
        return UpdateStatus(
            status="running",
            started_at=current_update["started_at"],
        )
        
    except Exception as e:
        current_update["status"] = "error"
        current_update["error_message"] = str(e)
        raise HTTPException(status_code=500, detail=f"Failed to start update: {str(e)}")


async def capture_update_output(process: subprocess.Popen, log_file: Path):
    """Capture stdout/stderr from update process and store for streaming"""
    try:
        print(f"[OWASP Update] Starting to capture output, PID={process.pid}")
        loop = asyncio.get_event_loop()
        
        # Open log file for writing
        with open(log_file, "w", encoding="utf-8") as log_f:
            while True:
                # Run readline() in thread pool to avoid blocking event loop
                line = await loop.run_in_executor(None, process.stdout.readline)
                
                if not line:
                    # Check if process is done (non-blocking poll)
                    return_code = await loop.run_in_executor(None, process.poll)
                    if return_code is not None:
                        # Process finished
                        print(f"[OWASP Update] Process finished with return code {return_code}")
                        break
                    await asyncio.sleep(0.1)
                    continue
                
                # Clean the line (remove ANSI codes, strip)
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
                if clean_line:
                    # Write to log file
                    log_f.write(clean_line + "\n")
                    log_f.flush()
                    
                    # Store ALL lines in memory for API access (not just filtered ones)
                    with current_update["process_output_lock"]:
                        current_update["process_output"].append(clean_line)
                        # Keep only last 1000 lines to avoid memory issues
                        if len(current_update["process_output"]) > 1000:
                            current_update["process_output"] = current_update["process_output"][-1000:]
                    
                    # Log all lines to console (dependency-check can be quiet, so we want to see everything)
                    print(f"[OWASP Update] {clean_line}")
                        
    except Exception as e:
        print(f"[OWASP Update Error] {e}")
        import traceback
        traceback.print_exc()


async def monitor_update(process: subprocess.Popen):
    """Monitor update process and update status when done"""
    loop = asyncio.get_event_loop()
    return_code = await loop.run_in_executor(None, process.wait)
    
    current_update["finished_at"] = datetime.now().isoformat()
    current_update["process"] = None
    
    if return_code == 0:
        current_update["status"] = "done"
        print(f"[OWASP Update] Update completed successfully")
    else:
        current_update["status"] = "error"
        current_update["error_code"] = return_code
        current_update["error_message"] = f"Update failed with exit code {return_code}"
        print(f"[OWASP Update] Update failed with exit code {return_code}")


def check_database_age(owasp_data_dir: Path) -> Tuple[Optional[int], bool]:
    """
    Check the age of OWASP database files
    Returns: (age_in_days, database_exists)
    """
    if not owasp_data_dir or not owasp_data_dir.exists():
        return None, False
    
    if not any(owasp_data_dir.iterdir()):
        return None, False
    
    try:
        # Find the most recent file in the database directory
        # Look for H2 database files first (most common)
        latest_file = None
        for pattern in ["*.mv.db", "*.h2.db", "*.lock"]:
            files = list(owasp_data_dir.glob(pattern))
            if files:
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                break
        
        # Fallback: find any file
        if latest_file is None:
            all_files = [f for f in owasp_data_dir.rglob("*") if f.is_file()]
            if all_files:
                latest_file = max(all_files, key=lambda f: f.stat().st_mtime)
        
        if latest_file and latest_file.exists():
            # Get file modification time
            file_time = latest_file.stat().st_mtime
            current_time = datetime.now().timestamp()
            age_seconds = int(current_time - file_time)
            age_days = age_seconds // 86400
            return age_days, True
        
        return None, True  # Directory exists but no files found
    except Exception as e:
        print(f"[OWASP Update] Error checking database age: {e}")
        return None, True  # Assume exists but can't determine age


def get_update_status(owasp_data_dir: Optional[Path] = None) -> UpdateStatus:
    """Get current update status"""
    # Check database age if directory is provided
    database_age_days = None
    database_exists = None
    if owasp_data_dir:
        database_age_days, database_exists = check_database_age(owasp_data_dir)
    
    return UpdateStatus(
        status=current_update["status"],
        started_at=current_update.get("started_at"),
        finished_at=current_update.get("finished_at"),
        error_code=current_update.get("error_code"),
        error_message=current_update.get("error_message"),
        database_age_days=database_age_days,
        database_exists=database_exists,
    )


def get_update_logs() -> dict:
    """Get update logs (last 1000 lines)"""
    with current_update["process_output_lock"]:
        lines = current_update["process_output"].copy()
    
    return {
        "lines": lines,
        "count": len(lines),
    }


def stop_update():
    """Stop the currently running update"""
    if current_update["status"] != "running" or current_update["process"] is None:
        return UpdateStatus(status=current_update["status"])
    
    try:
        process = current_update["process"]
        if process and process.poll() is None:
            process.terminate()
            # Wait a bit for graceful shutdown
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            current_update["status"] = "error"
            current_update["error_message"] = "Update stopped by user"
            current_update["finished_at"] = datetime.now().isoformat()
            current_update["process"] = None
            
    except Exception as e:
        current_update["error_message"] = f"Error stopping update: {str(e)}"
    
    return get_update_status()
