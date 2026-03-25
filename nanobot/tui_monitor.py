"""
tui_monitor.py — Live TUI dashboard for the multi-agent pipeline

Subscribes to the PipelineOrchestrator's status events and renders a
real-time Rich dashboard split into four panes:
  - Left panel:   Scrolling event log (all agents)
  - Right top:    Current @architect output
  - Right middle: Current @coder output
  - Right bottom: Current @qa verdicts

Usage (run alongside the orchestrator in the same process):
    python -m nanobot.tui_monitor --config ~/.nanobot/config.json

Or use as a library — pass it to PipelineOrchestrator(on_status=tui.on_event).
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque

from rich.columns import Columns
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# ---------------------------------------------------------------------------
# Shared event store
# ---------------------------------------------------------------------------

MAX_LOG_LINES = 200

class EventStore:
    """Thread-safe(ish) ring-buffer of pipeline events consumed by the TUI."""

    def __init__(self) -> None:
        self.log: Deque[tuple[str, str, str, str]] = deque(maxlen=MAX_LOG_LINES)
        self.by_agent: dict[str, list[tuple[str, str, str]]] = {
            "@architect": [],
            "@coder": [],
            "@qa": [],
            "orchestrator": [],
        }
        self._lock = asyncio.Lock()

    async def push(self, agent: str, event_type: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        async with self._lock:
            self.log.append((ts, agent, event_type, message))
            bucket = self.by_agent.setdefault(agent, [])
            bucket.append((ts, event_type, message))
            # Keep per-agent history bounded
            if len(bucket) > 50:
                bucket.pop(0)


# ---------------------------------------------------------------------------
# Rich renderers
# ---------------------------------------------------------------------------

_AGENT_STYLES: dict[str, str] = {
    "@architect": "magenta",
    "@coder": "cyan",
    "@qa": "green",
    "orchestrator": "yellow",
}

_EVENT_ICONS: dict[str, str] = {
    "start": "▶",
    "progress": "↳",
    "done": "✓",
    "approved": "✅",
    "rejected": "❌",
    "escalated": "⚠",
    "ready": "◉",
    "ambiguous": "?",
}


def _render_log(store: EventStore) -> Panel:
    """Render the scrolling event log for the left panel."""
    lines = Text()
    for ts, agent, event_type, message in list(store.log)[-40:]:
        color = _AGENT_STYLES.get(agent, "white")
        icon = _EVENT_ICONS.get(event_type, "·")
        lines.append(f"[{ts}] ", style="dim")
        lines.append(f"{icon} ", style=color)
        lines.append(f"{agent:<14}", style=f"bold {color}")
        lines.append(f" {message[:80]}\n", style="white")
    return Panel(lines, title="[bold]📡 Event Log[/bold]", border_style="bright_black", padding=(0, 1))


def _render_agent_panel(store: EventStore, agent: str) -> Panel:
    """Render the most recent activity panel for one agent."""
    color = _AGENT_STYLES.get(agent, "white")
    events = store.by_agent.get(agent, [])

    if not events:
        body = Text("Idle…", style="dim")
    else:
        body = Text()
        for ts, event_type, message in events[-8:]:
            icon = _EVENT_ICONS.get(event_type, "·")
            body.append(f"[{ts}] {icon} ", style="dim")
            body.append(f"{message[:100]}\n", style="white")

    title = f"[bold {color}]{agent}[/bold {color}]"
    return Panel(body, title=title, border_style=color, padding=(0, 1))


def _render_verdict_panel(store: EventStore) -> Panel:
    """Render the @qa verdict history."""
    events = [e for e in store.by_agent.get("@qa", []) if e[1] in ("approved", "rejected", "done")]
    if not events:
        body = Text("Awaiting first build…", style="dim")
    else:
        body = Text()
        for ts, event_type, message in events[-6:]:
            icon = _EVENT_ICONS.get(event_type, "·")
            style = "bold green" if event_type == "approved" else "bold red" if event_type == "rejected" else "white"
            body.append(f"[{ts}] {icon} ", style="dim")
            body.append(f"{message[:120]}\n", style=style)
    return Panel(body, title="[bold green]@qa Verdicts[/bold green]", border_style="green", padding=(0, 1))


def _build_layout(store: EventStore) -> Layout:
    layout = Layout()
    layout.split_row(
        Layout(name="left", ratio=2),
        Layout(name="right", ratio=3),
    )
    layout["left"].update(_render_log(store))
    layout["right"].split_column(
        Layout(name="architect"),
        Layout(name="coder"),
        Layout(name="qa"),
    )
    layout["right"]["architect"].update(_render_agent_panel(store, "@architect"))
    layout["right"]["coder"].update(_render_agent_panel(store, "@coder"))
    layout["right"]["qa"].update(_render_verdict_panel(store))
    return layout


# ---------------------------------------------------------------------------
# TUI Monitor class
# ---------------------------------------------------------------------------

class TUIMonitor:
    """
    Wraps the EventStore and Rich Live display.

    Wire it up via:
        monitor = TUIMonitor()
        orchestrator = PipelineOrchestrator(..., on_status=monitor.on_event)
        await asyncio.gather(orchestrator.run(), monitor.run())
    """

    def __init__(self, refresh_rate: float = 4.0) -> None:
        self.store = EventStore()
        self._refresh_rate = refresh_rate
        self._console = Console()

    async def on_event(self, agent: str, event_type: str, message: str) -> None:
        """Status callback — passed to PipelineOrchestrator(on_status=...)."""
        await self.store.push(agent, event_type, message)

    async def run(self) -> None:
        """Start the live TUI. Runs until cancelled."""
        with Live(
            _build_layout(self.store),
            console=self._console,
            refresh_per_second=self._refresh_rate,
            screen=True,
        ) as live:
            while True:
                live.update(_build_layout(self.store))
                await asyncio.sleep(1.0 / self._refresh_rate)


# ---------------------------------------------------------------------------
# Standalone entry-point (runs orchestrator + TUI together)
# ---------------------------------------------------------------------------

async def _main(config_path: str) -> None:
    from nanobot.orchestrator import PipelineOrchestrator

    repo_root = Path(__file__).parent.parent.resolve()
    monitor = TUIMonitor()
    orchestrator = PipelineOrchestrator(
        base_config_path=Path(config_path),
        repo_root=repo_root,
        on_status=monitor.on_event,
    )

    await asyncio.gather(
        orchestrator.run(),
        monitor.run(),
    )


if __name__ == "__main__":
    import sys
    cfg = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / ".nanobot" / "config.json")
    try:
        asyncio.run(_main(cfg))
    except KeyboardInterrupt:
        pass
