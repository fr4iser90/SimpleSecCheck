"""
Log Worker Service
Handles background thread that reads steps.log and puts logs into message queue
"""
import asyncio
import time
from pathlib import Path
from typing import Optional
from . import message_queue


def log_worker_thread_func(scan_id: str, results_dir: Optional[Path], current_scan: dict, event_loop=None):
    """
    Separate worker thread that reads steps.log and puts logs into the message queue.
    """
    message_queue.log_worker_running = True
    steps_log = None
    
    # Find steps.log file
    if results_dir and results_dir.exists():
        # Try to find scan directory in results_dir
        for scan_dir in sorted(results_dir.iterdir(), reverse=True):
            if scan_dir.is_dir() and scan_id in scan_dir.name:
                steps_log = scan_dir / "logs" / "steps.log"
                current_scan["results_dir"] = str(scan_dir)
                break
    
    # Wait for steps.log to appear (up to 30 seconds)
    search_start = time.time()
    max_search_time = 30
    
    while (time.time() - search_start) < max_search_time:
        if steps_log and steps_log.exists():
            break
        # Re-check path in case results_dir was updated
        if current_scan.get("results_dir"):
            steps_log = Path(current_scan["results_dir"]) / "logs" / "steps.log"
        elif scan_id and results_dir and results_dir.exists():
            # Re-search in results_dir
            for scan_dir in sorted(results_dir.iterdir(), reverse=True):
                if scan_dir.is_dir() and scan_id in scan_dir.name:
                    steps_log = scan_dir / "logs" / "steps.log"
                    current_scan["results_dir"] = str(scan_dir)
                    break
        time.sleep(0.5)
    
    if not steps_log or not steps_log.exists():
        print(f"[Log Worker] steps.log not found after {max_search_time}s")
        message_queue.log_worker_running = False
        return
    
    print(f"[Log Worker] Starting to read steps.log: {steps_log}")
    
    # Read and stream steps.log continuously
    try:
        with open(steps_log, "r", encoding="utf-8", errors="ignore") as f:
            # Read existing content first
            existing_lines = f.readlines()
            for line in existing_lines:
                if line.strip():
                    # Put log into queue (will be picked up by WebSocket)
                    if event_loop:
                        asyncio.run_coroutine_threadsafe(
                            message_queue.log_queue.put({"type": "log", "data": line.strip()}),
                            event_loop
                        )
            
            # Now tail the file continuously
            last_position = f.tell()
            last_update_time = time.time()
            max_idle_time = 10  # Stop after 10 seconds of no updates if scan is done
            
            while message_queue.log_worker_running:
                # Check if file has grown
                f.seek(0, 2)  # Seek to end
                current_position = f.tell()
                
                if current_position > last_position:
                    # File has new content
                    f.seek(last_position)
                    new_lines = []
                    for line in f:
                        if line.strip():
                            new_lines.append(line.strip())
                    
                    # Put new lines into queue
                    for line in new_lines:
                        if event_loop:
                            asyncio.run_coroutine_threadsafe(
                                message_queue.log_queue.put({"type": "log", "data": line}),
                                event_loop
                            )
                    
                    last_position = f.tell()
                    last_update_time = time.time()
                else:
                    # No new content
                    if current_scan["status"] in ["done", "error"]:
                        if time.time() - last_update_time > max_idle_time:
                            print(f"[Log Worker] Scan finished, no updates for {max_idle_time}s, stopping")
                            break
                
                time.sleep(0.1)  # Check every 100ms
                
    except Exception as e:
        print(f"[Log Worker] Error reading steps.log: {e}")
        import traceback
        traceback.print_exc()
    finally:
        message_queue.log_worker_running = False
        print(f"[Log Worker] Worker thread stopped")
