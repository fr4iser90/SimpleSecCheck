"""
Message Queue Service
Manages the log message queue and WebSocket connections
"""
import asyncio
from typing import Set
from fastapi import WebSocket


# Message Queue for logs
log_queue = asyncio.Queue()
active_websockets: Set[WebSocket] = set()  # Track active WebSocket connections
log_worker_running = False
log_worker_thread = None
