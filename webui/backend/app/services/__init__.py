"""
Services Package
Exports all service modules
"""
from .container_service import stop_running_containers
from .shutdown_service import (
    update_activity,
    schedule_shutdown,
    cancel_shutdown,
    shutdown_now,
    toggle_auto_shutdown,
    get_shutdown_status,
    idle_timeout_checker,
    create_signal_handler,
    register_signal_handlers,
    AUTO_SHUTDOWN_ENABLED,
    SHUTDOWN_AFTER_SCAN,
    SHUTDOWN_DELAY,
    IDLE_TIMEOUT
)
from .step_service import extract_steps_for_frontend, write_step_to_log
from .scan_service import (
    ScanRequest,
    ScanStatus,
    start_scan,
    get_scan_status,
    stop_scan,
    monitor_scan,
    capture_process_output
)
from .owasp_update_service import (
    UpdateStatus,
    start_update,
    get_update_status,
    get_update_logs,
    stop_update,
)

__all__ = [
    "stop_running_containers",
    "update_activity",
    "schedule_shutdown",
    "cancel_shutdown",
    "shutdown_now",
    "toggle_auto_shutdown",
    "get_shutdown_status",
    "idle_timeout_checker",
    "create_signal_handler",
    "register_signal_handlers",
    "AUTO_SHUTDOWN_ENABLED",
    "SHUTDOWN_AFTER_SCAN",
    "SHUTDOWN_DELAY",
    "IDLE_TIMEOUT",
    "extract_steps_for_frontend",
    "write_step_to_log",
    "ScanRequest",
    "ScanStatus",
    "start_scan",
    "get_scan_status",
    "stop_scan",
    "monitor_scan",
    "capture_process_output",
    "UpdateStatus",
    "start_update",
    "get_update_status",
    "get_update_logs",
    "stop_update",
]
