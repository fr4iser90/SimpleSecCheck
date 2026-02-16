"""
Services Package
Exports all service modules
"""
from .container_service import stop_running_containers
from .shutdown_service import (
    update_activity,
    schedule_shutdown,
    idle_timeout_checker,
    create_signal_handler,
    register_signal_handlers,
    AUTO_SHUTDOWN_ENABLED,
    SHUTDOWN_AFTER_SCAN,
    SHUTDOWN_DELAY,
    IDLE_TIMEOUT
)
from .step_service import extract_steps_for_frontend, write_step_to_log
from .log_worker import log_worker_thread_func
from .message_queue import log_queue, active_websockets, log_worker_running, log_worker_thread
from .scan_service import (
    ScanRequest,
    ScanStatus,
    start_scan,
    get_scan_status,
    stop_scan,
    monitor_scan,
    capture_process_output
)
from .websocket_service import websocket_logs

__all__ = [
    "stop_running_containers",
    "update_activity",
    "schedule_shutdown",
    "idle_timeout_checker",
    "create_signal_handler",
    "register_signal_handlers",
    "AUTO_SHUTDOWN_ENABLED",
    "SHUTDOWN_AFTER_SCAN",
    "SHUTDOWN_DELAY",
    "IDLE_TIMEOUT",
    "extract_steps_for_frontend",
    "write_step_to_log",
    "log_worker_thread_func",
    "log_queue",
    "active_websockets",
    "log_worker_running",
    "log_worker_thread",
    "ScanRequest",
    "ScanStatus",
    "start_scan",
    "get_scan_status",
    "stop_scan",
    "monitor_scan",
    "capture_process_output",
    "websocket_logs",
]
