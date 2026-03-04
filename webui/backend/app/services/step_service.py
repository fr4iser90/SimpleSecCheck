"""
Step Service
Modern approach: Reads steps.log directly (JSON Lines format - structured, no regex parsing!)
Step Registry handles all step tracking!
"""
import threading
from pathlib import Path
from typing import Optional, List, Dict

from app.database import get_database


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
    """Log a step message in JSON format (structured, no regex parsing!)"""
    step_num = current_scan["step_names"].get(step_name)
    if step_num:
        # Parse status from message (old format: "⏳ Step 1: ..." or "✓ Step 1: ...")
        status = "running"
        if "✓" in step_message or "completed" in step_message.lower():
            status = "completed"
        elif "⏳" in step_message or "running" in step_message.lower():
            status = "running"
        elif "❌" in step_message or "failed" in step_message.lower():
            status = "failed"
        elif "⊘" in step_message or "skipped" in step_message.lower():
            status = "skipped"
        
        # Extract message (remove icon and "Step X:" prefix)
        import re
        message_match = re.match(r'[⏳✓❌⊘]?\s*Step\s+\d+:\s*(.+)', step_message)
        clean_message = message_match.group(1) if message_match else step_message
        
        # Write in JSON format (same as StepRegistry)
        write_step_to_log(step_num, step_name, status, clean_message, scan_id, current_scan, results_dir)


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
    
    # Create/clear steps.log (JSON Lines format - one JSON object per line)
    steps_log = scan_dir / "logs" / "steps.log"
    from datetime import datetime
    with open(steps_log, "w", encoding="utf-8") as f:
        f.write(f'{{"init": "SimpleSecCheck Steps Log", "timestamp": "{datetime.now().isoformat()}"}}\n')

def write_step_to_log(step_number: int, step_name: str, status: str, message: str, scan_id: str, current_scan: dict, results_dir: Path):
    """Write step to steps.log file in JSON format (structured, no regex parsing!) and send WebSocket update"""
    results_dir_path = current_scan.get("results_dir")
    
    if not results_dir_path:
        return
    
    steps_log = Path(results_dir_path) / "logs" / "steps.log"
    
    # Ensure steps.log exists (initialize if needed)
    if not steps_log.exists():
        from datetime import datetime
        with open(steps_log, "w", encoding="utf-8") as f:
            f.write(f'{{"init": "SimpleSecCheck Steps Log", "timestamp": "{datetime.now().isoformat()}"}}\n')
    
    # Write step as JSON line (same format as StepRegistry)
    import json
    from datetime import datetime
    step_dict = {
        "number": step_number,
        "name": step_name,
        "status": status,  # 'pending', 'running', 'completed', 'failed', 'skipped'
        "message": message,
        "started_at": datetime.now().isoformat() if status in ["running", "completed", "failed", "skipped"] else None,
        "completed_at": datetime.now().isoformat() if status in ["completed", "failed", "skipped"] else None,
        "timestamp": datetime.now().isoformat()
    }
    with open(steps_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(step_dict) + "\n")
    
    # Persist step into DB (async fire-and-forget)
    try:
        import asyncio

        async def upsert_step():
            try:
                db = get_database()
                await db.upsert_scan_step(
                    scan_id=scan_id,
                    step_number=step_number,
                    step_name=step_name,
                    status=status,
                    message=message,
                    started_at=None,
                    completed_at=None,
                )
            except Exception as e:
                print(f"[Step Service] Error upserting step to DB: {e}")

        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(upsert_step())
        else:
            loop.run_until_complete(upsert_step())
    except RuntimeError:
        pass

    # Send WebSocket update (read all steps from DB and send update)
    try:
        import asyncio
        from app.services.websocket_manager import get_websocket_manager
        
        async def send_websocket_update():
            try:
                ws_manager = get_websocket_manager()
                
                # Read all steps from DB (source of truth)
                steps = await read_steps_from_db(scan_id)
                
                if steps:
                    # Calculate total_steps and progress_percentage
                    total_steps = max([s["number"] for s in steps], default=0)
                    if total_steps == 0:
                        progress_percentage = 0
                    else:
                        completed = sum(1 for s in steps if s.get("status") == "completed")
                        running = sum(1 for s in steps if s.get("status") == "running")
                        failed = sum(1 for s in steps if s.get("status") == "failed")
                        progress_percentage = round(((completed + failed + (running * 0.5)) / total_steps) * 100)
                    
                    # Send update to WebSocket clients
                    await ws_manager.send_step_update(scan_id, {
                        "steps": steps,
                        "total_steps": total_steps,
                        "progress_percentage": progress_percentage
                    })
            except Exception as e:
                print(f"[Step Service] Error sending WebSocket update: {e}")
        
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
        print(f"[Step Service] Error scheduling WebSocket update: {e}")


def read_steps_from_log(results_dir: Path) -> List[Dict[str, any]]:
    """
    Read steps from steps.log file (JSON Lines format - structured, no regex parsing!)
    
    Args:
        results_dir: Path to scan results directory
    
    Returns:
        List of step dictionaries
    """
    steps_log = results_dir / "logs" / "steps.log"
    
    if not steps_log.exists():
        return []
    
    steps = []
    step_map = {}  # {step_number: step_dict} - keep latest status per step
    
    try:
        import json
        with open(steps_log, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse JSON line (structured format - no regex needed!)
                    step_data = json.loads(line)
                    
                    # Skip init line
                    if "init" in step_data:
                        continue
                    
                    # Extract step data directly from JSON
                    step_number = step_data.get("number")
                    step_name = step_data.get("name")
                    status = step_data.get("status", "pending")
                    message = step_data.get("message", "")
                    
                    if not step_number or not step_name:
                        continue
                    
                    # Use step_number as key (one entry per step, latest status wins)
                    step_map[step_number] = {
                        "number": step_number,
                        "name": step_name,
                        "status": status,  # Already in correct format: 'pending', 'running', 'completed', 'failed', 'skipped'
                        "message": message
                    }
                except json.JSONDecodeError:
                    # Skip invalid JSON lines (e.g., old format lines)
                    continue
        
        # Convert to sorted list
        steps = sorted(step_map.values(), key=lambda s: s["number"])
        
    except Exception as e:
        print(f"[Step Service] Error reading steps.log: {e}")
    
    return steps


async def read_steps_from_db(scan_id: str) -> List[Dict[str, any]]:
    """Read steps for a scan from DB (ordered)"""
    try:
        db = get_database()
        return await db.get_scan_steps(scan_id)
    except Exception as e:
        print(f"[Step Service] Error reading steps from DB: {e}")
        return []


async def upsert_steps_from_log(scan_id: str, results_dir: Path) -> List[Dict[str, any]]:
    """Hydrate DB from steps.log and return steps list"""
    steps = read_steps_from_log(results_dir)
    if not steps:
        return []
    try:
        db = get_database()
        for step in steps:
            await db.upsert_scan_step(
                scan_id=scan_id,
                step_number=step.get("number"),
                step_name=step.get("name"),
                status=step.get("status"),
                message=step.get("message"),
                started_at=None,
                completed_at=None,
            )
    except Exception as e:
        print(f"[Step Service] Error hydrating steps into DB: {e}")
    return steps


# extract_steps_for_frontend REMOVED - Step Registry handles all step tracking now!
# Steps are written directly by Step Registry in orchestrator.py
# No log parsing needed - read_steps_from_log() reads structured data from steps.log
