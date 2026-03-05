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

from .scan_service import (
    ScanRequest,
    ScanStatus,
    start_scan,
    get_scan_status,
    stop_scan,
    monitor_scan,
    capture_process_output
)
from .session_service import (
    SessionService,
    get_session_service,
    session_middleware,
)
from .queue_service import (
    QueueService,
    get_queue_service,
)
from .scanner_worker import (
    ScannerWorker,
    get_scanner_worker,
    start_scanner_worker,
    stop_scanner_worker,
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
    "ScanRequest",
    "ScanStatus",
    "start_scan",
    "get_scan_status",
    "stop_scan",
    "monitor_scan",
    "capture_process_output",
    "SessionService",
    "get_session_service",
    "session_middleware",
    "QueueService",
    "get_queue_service",
    "ScannerWorker",
    "get_scanner_worker",
    "start_scanner_worker",
    "stop_scanner_worker",
]
