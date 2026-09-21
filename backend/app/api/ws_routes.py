"""
ws_routes.py - WebSocket endpoint for real-time METRIX-LM push notifications

Frontend connects to:
    ws://localhost:8000/ws/notifications?token=<jwt>

Events pushed (JSON):
    { "event": "NEW_INSPECTION", "data": { ...summary fields... } }
    { "event": "PING", "ts": "..." }
"""

import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.ws_manager import ws_manager

logger = logging.getLogger("metrix_ws")

router = APIRouter(tags=["WebSocket"])

PING_INTERVAL_SECONDS = 20


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str = Query(default="")):
    """
    Persistent WebSocket channel for reviewing officers / admins.
    Clients receive real-time push whenever a new inspection scan is committed.
    A PING frame is sent every 20 s to keep the connection alive through proxies.
    """
    await ws_manager.connect(websocket)
    logger.info(f"[WS] New reviewer client connected (token prefix: {token[:8]}...)")

    try:
        # Background ping task so the socket doesn't time-out
        async def _heartbeat():
            while True:
                await asyncio.sleep(PING_INTERVAL_SECONDS)
                try:
                    from datetime import datetime, timezone
                    await websocket.send_json({"event": "PING", "ts": datetime.now(timezone.utc).isoformat()})
                except Exception:
                    break

        heartbeat_task = asyncio.create_task(_heartbeat())

        # Keep alive – wait for any incoming message (or disconnect)
        while True:
            # We don't expect the client to send anything meaningful, but we
            # must await receive() to detect disconnection.
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected gracefully.")
    except Exception as exc:
        logger.warning(f"[WS] Unexpected WebSocket error: {exc}")
    finally:
        heartbeat_task.cancel()
        await ws_manager.disconnect(websocket)
