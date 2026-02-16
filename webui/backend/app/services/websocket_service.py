"""
WebSocket Service
Handles WebSocket connections for real-time log streaming
"""
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, status
from .message_queue import log_queue, active_websockets


async def websocket_logs(websocket: WebSocket):
    """
    WebSocket endpoint for streaming logs.
    Uses message queue - separate worker thread reads steps.log and puts logs into queue.
    """
    # Accept WebSocket connection with CORS support
    try:
        # Check origin if needed (for security, but allow all in dev)
        origin = websocket.headers.get("origin")
        if origin:
            print(f"[WebSocket] Connection from origin: {origin}")
        
        await websocket.accept()
    except Exception as e:
        print(f"[WebSocket] Error accepting connection: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        except:
            pass
        return
    
    active_websockets.add(websocket)
    print(f"[WebSocket] Client connected. Total connections: {len(active_websockets)}")
    
    # Send initial message
    try:
        await websocket.send_json({"type": "log", "data": " Starting security scan..."})
    except Exception as e:
        print(f"[WebSocket] Error sending initial message: {e}")
        active_websockets.discard(websocket)
        return
    
    try:
        # Continuously read from message queue and send to client
        while True:
            try:
                # Get log from queue (with timeout to allow checking connection)
                log_message = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                
                # Send to all connected clients
                if log_message:
                    try:
                        await websocket.send_json(log_message)
                    except Exception as e:
                        print(f"[WebSocket] Error sending message: {e}")
                        break
            except asyncio.TimeoutError:
                # Timeout is normal - just check if connection is still alive
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    # Connection closed
                    break
            except Exception as e:
                print(f"[WebSocket] Error in message loop: {e}")
                break
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        active_websockets.discard(websocket)
        print(f"[WebSocket] Client removed. Total connections: {len(active_websockets)}")
