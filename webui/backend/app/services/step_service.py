"""
Step Service
Handles step extraction and logging for frontend display
"""
import re
from pathlib import Path
from typing import Optional


def write_step_to_log(step_line: str, scan_id: str, current_scan: dict, results_dir: Path):
    """Write step to steps.log file"""
    # Try to find results_dir
    results_dir_path = current_scan.get("results_dir")
    
    # If not set yet, try to find it by scan_id
    if not results_dir_path and scan_id and results_dir.exists():
        for scan_dir in sorted(results_dir.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                results_dir_path = str(scan_dir)
                current_scan["results_dir"] = results_dir_path
                break
    
    # If still no results_dir, try to find most recent
    if not results_dir_path and results_dir.exists():
        for scan_dir in sorted(results_dir.iterdir(), reverse=True):
            if scan_dir.is_dir():
                results_dir_path = str(scan_dir)
                current_scan["results_dir"] = results_dir_path
                break
    
    # Write to steps.log
    if results_dir_path:
        steps_log = Path(results_dir_path) / "logs" / "steps.log"
        try:
            steps_log.parent.mkdir(parents=True, exist_ok=True)
            with open(steps_log, "a", encoding="utf-8") as f:
                f.write(f"{step_line}\n")
            print(f"[Step Log] Wrote step to {steps_log}: {step_line}")
        except Exception as e:
            print(f"[Step Log] ERROR writing to {steps_log}: {e}")


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
            write_step_to_log(formatted_line, scan_id, current_scan, results_dir)
    
    return formatted_line
