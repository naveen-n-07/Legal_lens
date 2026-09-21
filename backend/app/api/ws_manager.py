"""
ws_manager.py - Shared WebSocket Connection Manager for METRIX-LM Real-Time Push

This module holds a singleton ConnectionManager that any route can import
to broadcast JSON events to all connected browser clients.

Usage (in any route file):
    from app.api.ws_manager import ws_manager
    await ws_manager.broadcast({"event": "NEW_INSPECTION", "data": {...}})
"""

import asyncio
import json
import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("metrix_ws")


class ConnectionManager:
    """Thread-safe async WebSocket connection pool."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"[WS] Client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"[WS] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a JSON-serialisable dict to all connected clients."""
        if not self.active_connections:
            return

        payload = json.dumps(message, default=str)

        # Collect dead sockets so we can prune them after the loop
        dead: List[WebSocket] = []

        async with self._lock:
            snapshot = list(self.active_connections)

        for ws in snapshot:
            try:
                await ws.send_text(payload)
            except Exception as exc:
                logger.warning(f"[WS] Send failed ({exc}), marking for removal.")
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self.active_connections:
                        self.active_connections.remove(ws)


# Module-level singleton — import this everywhere
ws_manager = ConnectionManager()
