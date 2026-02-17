"""
Shutdown Service
Handles auto-shutdown and idle timeout functionality
"""
import os
import signal
import time
import threading


# Auto-shutdown configuration
AUTO_SHUTDOWN_ENABLED = os.getenv("WEBUI_AUTO_SHUTDOWN", "true").lower() == "true"
SHUTDOWN_AFTER_SCAN = os.getenv("WEBUI_SHUTDOWN_AFTER_SCAN", "true").lower() == "true"
SHUTDOWN_DELAY = int(os.getenv("WEBUI_SHUTDOWN_DELAY", "300"))  # 5 minutes default
IDLE_TIMEOUT = int(os.getenv("WEBUI_IDLE_TIMEOUT", "1800"))  # 30 minutes default

# Track last activity for idle timeout
last_activity = time.time()
shutdown_scheduled = False


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


def idle_timeout_checker(current_scan: dict):
    """Background thread to check idle timeout"""
    global last_activity, shutdown_scheduled
    
    if not AUTO_SHUTDOWN_ENABLED or IDLE_TIMEOUT <= 0:
        return
    
    while True:
        time.sleep(60)  # Check every minute
        idle_time = time.time() - last_activity
        
        # Don't shutdown if a scan is running
        if current_scan["status"] == "running":
            continue
        
        if idle_time > IDLE_TIMEOUT and not shutdown_scheduled:
            schedule_shutdown(delay=10)  # 10 second grace period
            break


def create_signal_handler(current_scan: dict, stop_containers_func):
    """Create signal handler for shutdown signals"""
    def signal_handler(signum, frame):
        """Handle shutdown signals and stop running scans"""
        if current_scan["status"] == "running":
            process = current_scan.get("process")
            if process and process.poll() is None:
                try:
                    process.terminate()
                    # Wait a bit for graceful shutdown
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        # Force kill if it doesn't terminate
                        process.kill()
                except Exception:
                    pass
            
            # Stop docker containers
            stop_containers_func(current_scan)
        
        # Exit gracefully
        os._exit(0)
    
    return signal_handler


def register_signal_handlers(handler):
    """Register signal handlers"""
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
