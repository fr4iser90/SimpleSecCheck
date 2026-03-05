#!/usr/bin/env python3
"""
Scanner Worker Main Entry Point
Runs the scanner worker that processes jobs from the queue
"""

import asyncio
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from app.services.scanner_worker import get_scanner_worker


async def main():
    """Main entry point for scanner worker"""
    print("[Scanner Worker] Starting scanner worker...")
    
    worker = await get_scanner_worker()
    
    try:
        await worker.start()
        print("[Scanner Worker] Worker started, waiting for jobs...")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("[Scanner Worker] Received interrupt signal, shutting down...")
    except Exception as e:
        print(f"[Scanner Worker] Error: {e}")
        raise
    finally:
        await worker.stop()
        print("[Scanner Worker] Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
