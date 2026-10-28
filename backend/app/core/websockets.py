"""
WebSocket Connection Manager for live workflow execution event streaming.
Maintains active connections by execution_id and broadcasts structured lifecycle events.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Set
from fastapi import WebSocket


class ExecutionWebSocketManager:
    """Manages active WebSockets subscribed to workflow executions."""

    def __init__(self):
        # Map execution_id (int) -> Set of active WebSocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, execution_id: int, websocket: WebSocket):
        """Accepts and registers a new WebSocket connection for an execution."""
        await websocket.accept()
        async with self._lock:
            if execution_id not in self._connections:
                self._connections[execution_id] = set()
            self._connections[execution_id].add(websocket)

    async def disconnect(self, execution_id: int, websocket: WebSocket):
        """Safely removes a disconnected WebSocket."""
        async with self._lock:
            if execution_id in self._connections:
                self._connections[execution_id].discard(websocket)
                if not self._connections[execution_id]:
                    del self._connections[execution_id]

    async def broadcast_event(
        self,
        execution_id: int,
        event: str,
        data: Dict[str, Any],
    ):
        """
        Broadcasts a structured JSON event to all clients monitoring the execution.
        Safely captures disconnections and drops dead sockets without throwing.
        """
        message = {
            "event": event,
            "execution_id": execution_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        async with self._lock:
            sockets = list(self._connections.get(execution_id, []))

        if not sockets:
            return

        dead_sockets: List[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for dead in dead_sockets:
                    if execution_id in self._connections:
                        self._connections[execution_id].discard(dead)


# Global singleton connection manager
ws_manager = ExecutionWebSocketManager()
