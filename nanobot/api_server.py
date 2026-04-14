"""
api_server.py — FastAPI bridge between the React frontend and the PipelineOrchestrator.

Exposes:
  REST  /api/system/check-opencode        — check if opencode CLI is installed
  REST  /api/system/install-opencode      — streaming install via npm
  REST  /api/config/                      — read ~/.nanobot/config.json
  REST  /api/config/save                  — write ~/.nanobot/config.json
  WS    /ws/chat                          — bidirectional chat with @architect
  WS    /ws/events                        — read-only pipeline event stream (TUI data)

Usage:
    pip install fastapi uvicorn[standard]
    python -m nanobot.api_server [~/.nanobot/config.json]
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.orchestrator import PipelineOrchestrator

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

app = FastAPI(title="Nanobot Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

_CONFIG_PATH = Path.home() / ".nanobot" / "config.json"
_REPO_ROOT   = Path(__file__).parent.parent.resolve()

# ---------------------------------------------------------------------------
# Global orchestrator & event fan-out state
# ---------------------------------------------------------------------------

_orchestrator: PipelineOrchestrator | None = None

# Active WebSocket connections for chat and events
_chat_sockets:  list[WebSocket] = []
_event_sockets: list[WebSocket] = []


def get_orchestrator() -> PipelineOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PipelineOrchestrator(
            base_config_path=_CONFIG_PATH,
            repo_root=_REPO_ROOT,
            on_status=_broadcast_event,
        )
    return _orchestrator


async def _broadcast_event(agent: str, event_type: str, message: str) -> None:
    """Push a pipeline status event to all connected /ws/events clients."""
    payload = json.dumps({"agent": agent, "type": event_type, "message": message})
    dead: list[WebSocket] = []
    for ws in list(_event_sockets):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _event_sockets.remove(ws)


# ---------------------------------------------------------------------------
# Startup: run orchestrator event loop as a background task
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _startup() -> None:
    orch = get_orchestrator()

    # Drain orchestrator outbound → broadcast to all connected chat sockets
    async def _outbound_pump() -> None:
        while True:
            try:
                msg: OutboundMessage = await asyncio.wait_for(
                    orch.user_bus.consume_outbound(), timeout=1.0
                )
                payload = json.dumps({"role": "architect", "content": msg.content})
                dead: list[WebSocket] = []
                for ws in list(_chat_sockets):
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    _chat_sockets.remove(ws)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    asyncio.create_task(orch.run(),          name="orchestrator")
    asyncio.create_task(_outbound_pump(),    name="outbound_pump")


# ---------------------------------------------------------------------------
# /api/system
# ---------------------------------------------------------------------------

@app.get("/api/system/check-opencode")
async def check_opencode() -> dict[str, Any]:
    """Check whether the opencode CLI is available on PATH or in standard fallback locations."""
    import shutil
    import sys
    import os

    opencode_path: str | None = None

    if sys.platform == "win32":
        # On Windows, shutil.which("opencode") returns the extensionless Unix
        # shell script which cannot be executed.  Look for .cmd explicitly.
        opencode_path = shutil.which("opencode.cmd")

        # Fallback: check npm global bin directory directly
        if not opencode_path:
            npm_global = Path(os.environ.get("APPDATA", "")) / "npm"
            for candidate in ["opencode.cmd", "opencode.ps1"]:
                p = npm_global / candidate
                if p.exists():
                    opencode_path = str(p)
                    break
    else:
        opencode_path = shutil.which("opencode")
        if not opencode_path:
            alt_path = Path.home() / ".local" / "share" / "opencode" / "bin" / "opencode"
            if alt_path.exists():
                opencode_path = str(alt_path)

    if not opencode_path:
        return {"available": False, "version": ""}

    try:
        result = subprocess.run(
            [opencode_path, "--version"],
            capture_output=True, text=True, timeout=10,
            shell=(sys.platform == "win32"),  # shell=True needed for .cmd files
        )
        available = result.returncode == 0
        version   = result.stdout.strip() or result.stderr.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        available = False
        version   = ""

    return {"available": available, "version": version}


@app.post("/api/system/install-opencode")
async def install_opencode() -> StreamingResponse:
    """
    Stream the output of `npm install -g opencode` back to the client
    so the frontend can render a live installation log.
    """
    async def _stream():
        proc = await asyncio.create_subprocess_exec(
            "npm", "install", "-g", "opencode",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        async for line in proc.stdout:
            yield line.decode(errors="replace")
        await proc.wait()
        exit_code = proc.returncode
        yield f"\n[exit code: {exit_code}]\n"

    return StreamingResponse(_stream(), media_type="text/plain")


# ---------------------------------------------------------------------------
# /api/config
# ---------------------------------------------------------------------------

@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    """Return the current config.json as parsed JSON."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


class ConfigSaveRequest(BaseModel):
    config: dict[str, Any]


@app.post("/api/config/save")
async def save_config(body: ConfigSaveRequest) -> dict[str, str]:
    """Persist a JSON payload to ~/.nanobot/config.json."""
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(body.config, f, indent=2, ensure_ascii=False)
    return {"status": "saved"}


# ---------------------------------------------------------------------------
# /ws/chat  — bidirectional architect chat
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """
    Bidirectional WebSocket bridge to the @architect planning session.

    Inbound  (client → server): JSON { "content": "..." }
    Outbound (server → client): JSON { "role": "architect", "content": "..." }
    """
    await websocket.accept()
    _chat_sockets.append(websocket)
    orch = get_orchestrator()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                content = data.get("content", "").strip()
            except (json.JSONDecodeError, AttributeError):
                content = raw.strip()

            if not content:
                continue

            # Inject the user message into the orchestrator's user bus
            await orch.user_bus.publish_inbound(
                InboundMessage(
                    channel="web",
                    sender_id="web_user",
                    chat_id="web_session",
                    content=content,
                )
            )
            # The outbound response is pumped back by _outbound_pump in startup
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _chat_sockets:
            _chat_sockets.remove(websocket)


# ---------------------------------------------------------------------------
# /ws/events  — read-only pipeline event stream
# ---------------------------------------------------------------------------

@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    """
    Read-only stream of internal pipeline events (agent, type, message).
    Used by the frontend's Live Event Ticker component.
    """
    await websocket.accept()
    _event_sockets.append(websocket)
    try:
        # Keep the socket alive; all data is pushed from _broadcast_event
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if websocket in _event_sockets:
            _event_sockets.remove(websocket)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    config_arg = sys.argv[1] if len(sys.argv) > 1 else str(_CONFIG_PATH)
    _CONFIG_PATH = Path(config_arg).expanduser().resolve()
    uvicorn.run(
        "nanobot.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
