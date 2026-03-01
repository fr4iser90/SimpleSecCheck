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
shutdown_scheduled_time = None  # Timestamp when shutdown was scheduled
shutdown_delay_seconds = 0  # Delay in seconds when shutdown was scheduled


def update_activity():
    """Update last activity timestamp"""
    global last_activity
    last_activity = time.time()


def schedule_shutdown(delay: int = 0, current_scan: dict = None):
    """Schedule graceful shutdown
    
    Args:
        delay: Delay in seconds before shutdown
        current_scan: Optional dict to check if scan is running (prevents shutdown during scan)
    """
    global shutdown_scheduled, shutdown_scheduled_time, shutdown_delay_seconds
    
    if shutdown_scheduled or not AUTO_SHUTDOWN_ENABLED:
        return
    
    shutdown_scheduled = True
    shutdown_scheduled_time = time.time()
    shutdown_delay_seconds = delay
    
    def shutdown():
        # Sleep in small increments to allow checking if scan started
        elapsed = 0
        check_interval = 5  # Check every 5 seconds
        while elapsed < delay:
            # Check if scan is running - if so, cancel shutdown
            if current_scan and current_scan.get("status") == "running":
                print(f"[Auto-Shutdown] Cancelled shutdown - scan is running")
                cancel_shutdown()
                return
            
            # Check if shutdown was cancelled
            if not shutdown_scheduled:
                return
            
            sleep_time = min(check_interval, delay - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time
        
        # Final check before shutting down
        if current_scan and current_scan.get("status") == "running":
            print(f"[Auto-Shutdown] Cancelled shutdown - scan is running")
            cancel_shutdown()
            return
        
        # Check if shutdown was cancelled
        if not shutdown_scheduled:
            return
        
        print(f"[Auto-Shutdown] Shutting down after {delay}s delay...")
        os.kill(os.getpid(), signal.SIGTERM)
    
    threading.Thread(target=shutdown, daemon=True).start()


def cancel_shutdown():
    """Cancel scheduled shutdown"""
    global shutdown_scheduled, shutdown_scheduled_time, shutdown_delay_seconds
    shutdown_scheduled = False
    shutdown_scheduled_time = None
    shutdown_delay_seconds = 0


def shutdown_now():
    """Shutdown immediately"""
    global shutdown_scheduled
    shutdown_scheduled = True
    print("[Manual Shutdown] Shutting down now...")
    os.kill(os.getpid(), signal.SIGTERM)


def toggle_auto_shutdown(enabled: bool):
    """Toggle auto-shutdown on/off"""
    global AUTO_SHUTDOWN_ENABLED
    # Note: This only affects runtime, not environment variable
    # Environment variable is read at startup, so this is a runtime toggle
    AUTO_SHUTDOWN_ENABLED = enabled
    if not enabled:
        cancel_shutdown()
    return AUTO_SHUTDOWN_ENABLED


def get_shutdown_status(current_scan: dict):
    """Get current shutdown status"""
    global shutdown_scheduled, shutdown_scheduled_time, shutdown_delay_seconds, last_activity
    
    shutdown_in_seconds = None
    if shutdown_scheduled and shutdown_scheduled_time:
        elapsed = time.time() - shutdown_scheduled_time
        remaining = max(0, shutdown_delay_seconds - elapsed)
        shutdown_in_seconds = int(remaining) if remaining > 0 else 0
    
    idle_time = time.time() - last_activity
    idle_timeout_remaining = None
    if AUTO_SHUTDOWN_ENABLED and IDLE_TIMEOUT > 0 and current_scan.get("status") != "running":
        idle_timeout_remaining = max(0, IDLE_TIMEOUT - idle_time)
    
    return {
        "auto_shutdown_enabled": AUTO_SHUTDOWN_ENABLED,
        "shutdown_after_scan": SHUTDOWN_AFTER_SCAN,
        "shutdown_delay": SHUTDOWN_DELAY,
        "idle_timeout": IDLE_TIMEOUT,
        "shutdown_scheduled": shutdown_scheduled,
        "shutdown_in_seconds": shutdown_in_seconds,
        "idle_timeout_remaining": int(idle_timeout_remaining) if idle_timeout_remaining is not None else None,
        "last_activity": last_activity,
    }


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
            schedule_shutdown(delay=10, current_scan=current_scan)  # 10 second grace period
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
                except Exception as e:
                    # Non-critical: Failed to kill process during shutdown
                    import logging
                    logging.debug(f"Could not kill process during shutdown: {e}")
            
            # Stop docker containers
            stop_containers_func(current_scan)
        
        # Exit gracefully
        os._exit(0)
    
    return signal_handler


def register_signal_handlers(handler):
    """Register signal handlers"""
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
