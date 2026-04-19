#!/usr/bin/env python3
"""
main.py

FastAPI application — AGV Dashboard backend.

Endpoints:
    GET  /           → health check
    GET  /status     → current AGV state (JSON, one-shot)
    WS   /ws         → WebSocket stream, pushes state every 200 ms

Run:
    cd ~/agv_ws/agv_dashboard/backend
    source ~/agv_ws/install/setup.zsh
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ros_bridge import ROSBridge

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("agv_dashboard")

# ---------------------------------------------------------------------------
# ROS bridge — singleton, started on app startup
# ---------------------------------------------------------------------------

bridge = ROSBridge()

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Tracks active WebSocket connections and broadcasts to all of them."""

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        log.info(f"[WS] Client connected. Total: {len(self._connections)}")

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)
        log.info(f"[WS] Client disconnected. Total: {len(self._connections)}")

    async def broadcast(self, payload: str) -> None:
        """Send payload to all connected clients, drop dead connections."""
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)

    @property
    def count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Background task — broadcast loop
# ---------------------------------------------------------------------------

async def broadcast_loop() -> None:
    """
    Runs as a FastAPI background task.
    Reads AGV state from the ROS bridge every 200 ms
    and broadcasts it to all WebSocket clients.
    """
    log.info("[broadcast_loop] Started — pushing state every 200 ms.")
    while True:
        if manager.count > 0:
            state = bridge.get_state()
            payload = json.dumps(state)
            await manager.broadcast(payload)
        await asyncio.sleep(0.2)

# ---------------------------------------------------------------------------
# App lifespan — start/stop ROS bridge and broadcast loop
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("[startup] Starting ROS bridge...")
    bridge.start()
    log.info("[startup] ROS bridge running.")

    task = asyncio.create_task(broadcast_loop())

    yield   # app is running

    log.info("[shutdown] Stopping broadcast loop and ROS bridge...")
    task.cancel()
    bridge.stop()
    log.info("[shutdown] Clean shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AGV Dashboard API",
    description="Real-time AGV telemetry bridge — ROS 2 → FastAPI → React",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "service": "AGV Dashboard API",
        "version": "1.0.0",
        "status":  "running",
        "clients": manager.count,
    }


@app.get("/status")
async def get_status():
    """
    One-shot REST endpoint — returns current AGV state.
    Used by the React frontend on initial load before
    the WebSocket connection is established.
    """
    return bridge.get_state()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint — maintains a persistent connection
    with each dashboard client.

    The broadcast_loop() pushes state every 200 ms.
    This handler keeps the connection alive and handles
    graceful disconnects.
    """
    await manager.connect(ws)

    # Send initial state immediately on connect
    initial = json.dumps(bridge.get_state())
    await ws.send_text(initial)

    try:
        while True:
            # Keep connection alive — client can optionally send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as exc:
        log.warning(f"[WS] Unexpected error: {exc}")
        manager.disconnect(ws)
