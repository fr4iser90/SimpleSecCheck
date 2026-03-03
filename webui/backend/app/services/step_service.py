"""
Step Service
Modern approach: Reads steps.log directly (written by Step Registry)
No more log parsing - Step Registry handles all step tracking!
"""
import re
import threading
from pathlib import Path
from typing import Optional, List, Dict


def initialize_step_tracking(current_scan: dict) -> None:
    """Initialize step tracking structures - kept for compatibility"""
    current_scan["process_output_lock"] = threading.Lock()
    current_scan["step_counter"] = 0
    current_scan["step_names"] = {}


def reset_step_tracking(current_scan: dict, preserve_git_clone: bool = False) -> None:
    """Reset step tracking - kept for compatibility"""
    if preserve_git_clone and "Git Clone" in current_scan.get("step_names", {}):
        git_clone_num = current_scan["step_names"]["Git Clone"]
        current_scan["step_counter"] = git_clone_num
        git_clone_name = "Git Clone"
        current_scan["step_names"] = {git_clone_name: git_clone_num}
    else:
        current_scan["step_counter"] = 0
        current_scan["step_names"] = {}


def register_step(step_name: str, current_scan: dict) -> int:
    """Register a new step - kept for compatibility"""
    lock = current_scan["process_output_lock"]
    with lock:
        if step_name not in current_scan["step_names"]:
            current_scan["step_counter"] += 1
            current_scan["step_names"][step_name] = current_scan["step_counter"]
        return current_scan["step_names"][step_name]


def log_step(step_name: str, step_message: str, current_scan: dict, results_dir: Path, scan_id: str) -> None:
    """Log a step message - kept for compatibility (Git Clone, etc.)"""
    step_num = current_scan["step_names"].get(step_name)
    if step_num:
        write_step_to_log(step_message, scan_id, current_scan, results_dir)


def derive_project_name(target: str) -> str:
    """Derive PROJECT_NAME from target"""
    import os
    if not target:
        return "scan"
    
    if target.startswith(("http://", "https://")):
        if "github.com" in target or "gitlab.com" in target:
            parts = target.rstrip("/").split("/")
            return parts[-1].replace(".git", "") if len(parts) >= 2 else "scan"
        else:
            domain = target.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
            return domain or "scan"
    else:
        return os.path.basename(target.rstrip("/")) or "target"


def initialize_steps_log(scan_id: str, results_dir_path: str, current_scan: dict, target: str) -> None:
    """
    Initialize steps.log file for a new scan.
    Step Registry will take over from here!
    """
    scan_dir = Path(results_dir_path)
    scan_dir.mkdir(parents=True, exist_ok=True)
    (scan_dir / "logs").mkdir(parents=True, exist_ok=True)
    
    current_scan["results_dir"] = str(scan_dir)
    print(f"[Step Service] Created scan directory: {scan_dir}")
    
    # Create/clear steps.log (Step Registry will write to it)
    steps_log = scan_dir / "logs" / "steps.log"
    from datetime import datetime
    with open(steps_log, "w", encoding="utf-8") as f:
        f.write(f"----- SimpleSecCheck Steps Log Initialized: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -----\n")


def write_step_to_log(step_line: str, scan_id: str, current_scan: dict, results_dir: Path):
    """Write step to steps.log file - kept for compatibility (Git Clone, etc.)"""
    results_dir_path = current_scan.get("results_dir")
    
    if not results_dir_path:
        return
    
    steps_log = Path(results_dir_path) / "logs" / "steps.log"
    with open(steps_log, "a", encoding="utf-8") as f:
        f.write(f"{step_line}\n")


def read_steps_from_log(results_dir: Path) -> List[Dict[str, any]]:
    """
    Read steps from steps.log file (written by Step Registry)
    
    Args:
        results_dir: Path to scan results directory
    
    Returns:
        List of step dictionaries
    """
    steps_log = results_dir / "logs" / "steps.log"
    
    if not steps_log.exists():
        return []
    
    steps = []
    step_map = {}  # {step_number: step_dict}
    
    try:
        with open(steps_log, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("-----"):
                    continue
                
                # Parse step line: "⏳ Step 1: Running Semgrep scan..."
                # Format: [icon] Step [number]: [message]
                step_match = re.match(r'([⏳✓❌⊘]?)\s*Step\s+(\d+):\s*(.+)', line, re.IGNORECASE)
                if step_match:
                    status_icon, step_num_str, message = step_match.groups()
                    step_number = int(step_num_str)
                    
                    # Determine status from icon
                    status = 'pending'
                    if status_icon == '✓':
                        status = 'completed'
                    elif status_icon == '⏳':
                        status = 'running'
                    elif status_icon == '❌':
                        status = 'failed'
                    elif status_icon == '⊘':
                        status = 'skipped'
                    
                    # Extract step name from message
                    # Examples: "Running Semgrep scan..." -> "Semgrep"
                    #           "Semgrep scan completed" -> "Semgrep"
                    name_match = re.match(r'^(.+?)(?:\s+scan|\s+\.\.\.|\s+completed|\s+failed|\s+skipped|$)', message, re.IGNORECASE)
                    step_name = name_match.group(1).strip() if name_match else message.strip()
                    
                    # Update or create step
                    if step_number not in step_map:
                        step_map[step_number] = {
                            "number": step_number,
                            "name": step_name,
                            "status": status,
                            "message": message.strip()
                        }
                    else:
                        # Update existing step (status might change)
                        step_map[step_number]["status"] = status
                        step_map[step_number]["message"] = message.strip()
                        # Update name if it's more specific
                        if len(step_name) > len(step_map[step_number]["name"]):
                            step_map[step_number]["name"] = step_name
        
        # Convert to sorted list
        steps = sorted(step_map.values(), key=lambda s: s["number"])
        
    except Exception as e:
        print(f"[Step Service] Error reading steps.log: {e}")
    
    return steps


# extract_steps_for_frontend REMOVED - Step Registry handles all step tracking now!
# Steps are written directly by Step Registry in orchestrator.py
# No log parsing needed - read_steps_from_log() reads structured data from steps.log
