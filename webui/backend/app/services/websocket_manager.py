"""
WebSocket Manager
Manages WebSocket connections for real-time scan updates
Hybrid approach: Log file for persistence + direct WebSocket for real-time
"""
import asyncio
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket
from pathlib import Path


class WebSocketManager:
    """Manages WebSocket connections per scan_id"""
    
    def __init__(self):
        # {scan_id: Set[WebSocket]}
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, scan_id: str):
        """Add WebSocket connection for a scan_id"""
        async with self.lock:
            if scan_id not in self.connections:
                self.connections[scan_id] = set()
            self.connections[scan_id].add(websocket)
            print(f"[WebSocket Manager] Connected: scan_id={scan_id}, total connections: {len(self.connections[scan_id])}")
    
    async def disconnect(self, websocket: WebSocket, scan_id: str):
        """Remove WebSocket connection for a scan_id"""
        async with self.lock:
            if scan_id in self.connections:
                self.connections[scan_id].discard(websocket)
                if not self.connections[scan_id]:
                    del self.connections[scan_id]
                print(f"[WebSocket Manager] Disconnected: scan_id={scan_id}, remaining connections: {len(self.connections.get(scan_id, set()))}")
    
    async def send_to_scan(self, scan_id: str, data: dict):
        """Send data to all WebSocket connections for a scan_id"""
        async with self.lock:
            connections = self.connections.get(scan_id, set()).copy()
        
        if not connections:
            return
        
        message = json.dumps(data)
        disconnected = set()
        
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"[WebSocket Manager] Error sending to {scan_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected connections
        if disconnected:
            async with self.lock:
                if scan_id in self.connections:
                    self.connections[scan_id] -= disconnected
                    if not self.connections[scan_id]:
                        del self.connections[scan_id]
    
    async def send_step_update(self, scan_id: str, step_data: dict):
        """Send step update to all connections for a scan_id"""
        data = {
            "type": "step_update",
            "steps": step_data.get("steps", []),
            "scan_id": scan_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_to_scan(scan_id, data)
    
    def get_connection_count(self, scan_id: str) -> int:
        """Get number of connections for a scan_id"""
        return len(self.connections.get(scan_id, set()))


# Global WebSocket manager instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create WebSocket manager instance"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
