"""
Step Service
Handles step extraction and logging for frontend display
"""
import re
import threading
from pathlib import Path
from typing import Optional


def initialize_step_tracking(current_scan: dict) -> None:
    """Initialize step tracking structures - STRAIGHT FORWARD"""
    current_scan["process_output_lock"] = threading.Lock()
    current_scan["step_counter"] = 0
    current_scan["step_names"] = {}


def reset_step_tracking(current_scan: dict, preserve_git_clone: bool = False) -> None:
    """Reset step tracking - STRAIGHT FORWARD"""
    if preserve_git_clone and "Git Clone" in current_scan.get("step_names", {}):
        # Git Clone is Step 1, keep it, next step will be 2
        git_clone_num = current_scan["step_names"]["Git Clone"]
        current_scan["step_counter"] = git_clone_num
        # Keep only Git Clone in step_names
        git_clone_name = "Git Clone"
        current_scan["step_names"] = {git_clone_name: git_clone_num}
    else:
        current_scan["step_counter"] = 0
        current_scan["step_names"] = {}


def register_step(step_name: str, current_scan: dict) -> int:
    """Register a new step and return its step number - STRAIGHT FORWARD"""
    lock = current_scan["process_output_lock"]
    with lock:
        if step_name not in current_scan["step_names"]:
            current_scan["step_counter"] += 1
            current_scan["step_names"][step_name] = current_scan["step_counter"]
        return current_scan["step_names"][step_name]


def log_step(step_name: str, step_message: str, current_scan: dict, results_dir: Path, scan_id: str) -> None:
    """Log a step message - STRAIGHT FORWARD"""
    step_num = current_scan["step_names"].get(step_name)
    if step_num:
        write_step_to_log(step_message, scan_id, current_scan, results_dir)


def derive_project_name(target: str) -> str:
    """Derive PROJECT_NAME from target (same logic as run-docker.sh line 114)"""
    import os
    if not target:
        return "scan"
    
    if target.startswith(("http://", "https://")):
        if "github.com" in target or "gitlab.com" in target:
            # Git URL: extract repo name
            parts = target.rstrip("/").split("/")
            return parts[-1].replace(".git", "") if len(parts) >= 2 else "scan"
        else:
            # Website URL: extract domain
            domain = target.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
            return domain or "scan"
    else:
        # Local path: use basename
        return os.path.basename(target.rstrip("/")) or "target"


def initialize_steps_log(scan_id: str, results_dir_path: str, current_scan: dict, target: str) -> None:
    """
    Initialize steps.log file for a new scan.
    STRAIGHT FORWARD: Create directory, create steps.log, done.
    
    Args:
        scan_id: Scan identifier
        results_dir_path: Full path to scan results directory (e.g., "/app/results/PROJECT_SCAN_ID")
        current_scan: Current scan dictionary
        target: Target URL/path being scanned
    """
    # results_dir_path is already the full path from get_results_dir_for_scan()
    scan_dir = Path(results_dir_path)
    scan_dir.mkdir(parents=True, exist_ok=True)
    (scan_dir / "logs").mkdir(parents=True, exist_ok=True)
    
    # Store in current_scan
    current_scan["results_dir"] = str(scan_dir)
    print(f"[Step Service] Created scan directory: {scan_dir}")
    
    # Create/clear steps.log
    steps_log = scan_dir / "logs" / "steps.log"
    from datetime import datetime
    with open(steps_log, "w", encoding="utf-8") as f:
        f.write(f"----- SimpleSecCheck Steps Log Initialized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -----\n")


def write_step_to_log(step_line: str, scan_id: str, current_scan: dict, results_dir: Path):
    """Write step to steps.log file - STRAIGHT FORWARD"""
    results_dir_path = current_scan.get("results_dir")
    
    # results_dir MUST be set by initialize_steps_log() - no fallbacks!
    if not results_dir_path:
        return  # Skip if not initialized
    
    steps_log = Path(results_dir_path) / "logs" / "steps.log"
    with open(steps_log, "a", encoding="utf-8") as f:
        f.write(f"{step_line}\n")


def extract_steps_for_frontend(line: str, current_scan: dict, results_dir: Path) -> Optional[str]:
    """
    Extract ONLY steps from log lines for frontend.
    Returns formatted step line if it's a step, None otherwise.
    Backend logs everything - this is ONLY for frontend display.
    Also writes steps to steps.log file.
    """
    # Remove ANSI color codes
    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
    if not clean_line:
        return None
    
    formatted_line = None
    
    # Initialization messages (Step 1 or Step 2 if Git Clone exists)
    if not formatted_line:
        if re.search(r'SimpleSecCheck.*Scan.*Started|Orchestrator script started', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "Initialization" not in current_scan["step_names"]:
                    # If Git Clone already exists as Step 1, make Initialization Step 2
                    if "Git Clone" in current_scan.get("step_names", {}):
                        current_scan["step_counter"] += 1
                        step_num = current_scan["step_counter"]
                    else:
                        current_scan["step_counter"] = 1
                        step_num = 1
                    current_scan["step_names"]["Initialization"] = step_num
                    formatted_line = f"✓ Step {step_num}: Initializing scan..."
    
    # Extract scan steps from orchestrator messages
    # Pattern: "--- Orchestrating X Scan ---" (only log when starting, not when finishing)
    if not formatted_line:
        orchestrating_match = re.search(r'---\s*Orchestrating\s+(.+?)\s+Scan\s+---', clean_line, re.IGNORECASE)
        if orchestrating_match:
            tool_name = orchestrating_match.group(1).strip()
            with current_scan["process_output_lock"]:
                # Only create step if not already seen
                if tool_name not in current_scan["step_names"]:
                    current_scan["step_counter"] += 1
                    current_scan["step_names"][tool_name] = current_scan["step_counter"]
                step_num = current_scan["step_names"][tool_name]
                formatted_line = f"⏳ Step {step_num}: Running {tool_name} scan..."
    
    # Pattern: "--- X Scan Orchestration Finished ---" (log completion)
    if not formatted_line:
        finished_match = re.search(r'---\s*(.+?)\s+Scan\s+Orchestration\s+Finished\s+---', clean_line, re.IGNORECASE)
        if finished_match:
            tool_name = finished_match.group(1).strip()
            with current_scan["process_output_lock"]:
                # Get step number (should already exist from "Orchestrating" message)
                step_num = current_scan["step_names"].get(tool_name)
                if step_num:  # Only log if we've seen the start
                    formatted_line = f"✓ Step {step_num}: {tool_name} scan completed"
    
    # OWASP Dependency Check database download (special case - can take 5-15 minutes)
    if not formatted_line:
        if re.search(r'Downloading vulnerability database.*may take|OWASP.*database.*not found.*Downloading', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "OWASP Database Download" not in current_scan["step_names"]:
                    # Find OWASP step number
                    owasp_step = current_scan["step_names"].get("OWASP Dependency Check")
                    if owasp_step:
                        current_scan["step_names"]["OWASP Database Download"] = owasp_step
                        step_num = owasp_step
                        formatted_line = f"⏳ Step {step_num}: Downloading OWASP vulnerability database (this may take 5-15 minutes)..."
    
    # OWASP database ready/using existing
    if not formatted_line:
        if re.search(r'Using existing.*OWASP.*database|OWASP.*database.*ready', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "OWASP Database Ready" not in current_scan["step_names"]:
                    owasp_step = current_scan["step_names"].get("OWASP Dependency Check")
                    if owasp_step:
                        current_scan["step_names"]["OWASP Database Ready"] = owasp_step
                        formatted_line = f"✓ Step {owasp_step}: OWASP database ready"
    
    # Metadata collection (only if enabled)
    if not formatted_line:
        if re.search(r'---\s*Collecting\s+Metadata\s+---|Collecting scan metadata|Collecting.*metadata.*enabled', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "Metadata Collection" not in current_scan["step_names"]:
                    current_scan["step_counter"] += 1
                    current_scan["step_names"]["Metadata Collection"] = current_scan["step_counter"]
                    step_num = current_scan["step_counter"]
                    formatted_line = f"⏳ Step {step_num}: Collecting metadata..."
    
    # Metadata collection completion (only show once)
    if not formatted_line:
        if re.search(r'---\s*Metadata\s+Collection\s+Finished\s+---|Metadata collection.*completed successfully|Metadata.*saved successfully', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                step_num = current_scan["step_names"].get("Metadata Collection")
                if step_num:
                    # Check if already completed to avoid duplicates
                    completed_key = "Metadata Collection_completed"
                    if completed_key not in current_scan.get("completed_steps", set()):
                        if "completed_steps" not in current_scan:
                            current_scan["completed_steps"] = set()
                        current_scan["completed_steps"].add(completed_key)
                        formatted_line = f"✓ Step {step_num}: Metadata collection completed"
    
    # Report generation (only show once)
    if not formatted_line:
        if re.search(r'Generating.*HTML report|HTML report generation', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "Report Generation" not in current_scan["step_names"]:
                    current_scan["step_counter"] += 1
                    current_scan["step_names"]["Report Generation"] = current_scan["step_counter"]
                    step_num = current_scan["step_counter"]
                    formatted_line = f"⏳ Step {step_num}: Generating report..."
    
    # Report completion
    if not formatted_line:
        if re.search(r'Report.*generated|HTML report.*created', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                step_num = current_scan["step_names"].get("Report Generation")
                if step_num:
                    formatted_line = f"✓ Step {step_num}: Report generation completed"
    
    # Scan completion (only show once, must be last step)
    if not formatted_line:
        if re.search(r'SimpleSecCheck.*Scan.*Completed|Scan.*completed successfully', clean_line, re.IGNORECASE):
            with current_scan["process_output_lock"]:
                if "Completion" not in current_scan["step_names"]:
                    current_scan["step_counter"] += 1
                    current_scan["step_names"]["Completion"] = current_scan["step_counter"]
                    step_num = current_scan["step_counter"]
                    formatted_line = f"✓ Step {step_num}: Scan completed successfully"
    
    # Errors (show as steps, but don't count as steps)
    if not formatted_line:
        if re.search(r'\[ERROR\]|\[ORCHESTRATOR ERROR\]', clean_line, re.IGNORECASE):
            formatted_line = f"❌ {clean_line}"
    
    # Write to steps.log file if we found a step
    if formatted_line:
        scan_id = current_scan.get("scan_id")
        if scan_id:
            write_step_to_log(formatted_line, scan_id, current_scan, results_dir)
    
    return formatted_line
