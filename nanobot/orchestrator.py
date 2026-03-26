"""
orchestrator.py — Intent-Centric Multi-Agent Pipeline Orchestrator

State machine:
  PLANNING  — @architect is in a live chat loop with the user.
  EXECUTING — <FINAL_SPEC> detected; @coder and @qa run in the background.

Each agent has its own isolated AgentLoop and MessageBus.
The @architect maintains conversation history via session_key, so it
remembers the full planning dialogue across multiple user messages.

Usage:
    python -m nanobot.orchestrator [~/.nanobot/config.json]
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Callable, Awaitable

from loguru import logger

from nanobot.agent.loop import AgentLoop
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.config.loader import load_config
from nanobot.config.schema import Config, ExecToolConfig


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_FINAL_SPEC_RE = re.compile(
    r"<FINAL_SPEC>(.*?)</FINAL_SPEC>", re.DOTALL | re.IGNORECASE
)
_APPROVE_RE = re.compile(r"\bVERDICT\s*:\s*APPROVE\b", re.IGNORECASE)
_REJECT_RE  = re.compile(r"\bVERDICT\s*:\s*REJECT\b",  re.IGNORECASE)

_MAX_QA_LOOPS = 3  # maximum coder→qa cycles before escalating to human


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def _build_agent(
    name: str,
    workspace_dir: Path,
    base_config: Config,
    bus: MessageBus,
    workspace_config_path: Path | None = None,
) -> AgentLoop:
    """Construct an AgentLoop for one pipeline agent."""
    cfg = base_config

    exec_cfg = cfg.tools.exec  # default
    if workspace_config_path and workspace_config_path.exists():
        with open(workspace_config_path, encoding="utf-8") as f:
            overrides = json.load(f)
        exec_overrides = overrides.get("tools", {}).get("exec", {})
        exec_cfg = ExecToolConfig(
            timeout=exec_overrides.get("timeout", cfg.tools.exec.timeout),
            path_append=exec_overrides.get(
                "pathAppend", exec_overrides.get("path_append", cfg.tools.exec.path_append)
            ),
        )

    from nanobot.cli.commands import _make_provider
    provider = _make_provider(cfg)

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=workspace_dir,
        model=cfg.agents.defaults.model,
        max_iterations=cfg.agents.defaults.max_tool_iterations,
        context_window_tokens=cfg.agents.defaults.context_window_tokens,
        web_search_config=cfg.tools.web.search,
        web_proxy=cfg.tools.web.proxy or None,
        exec_config=exec_cfg,
        restrict_to_workspace=cfg.tools.restrict_to_workspace,
        mcp_servers=cfg.tools.mcp_servers,
    )
    logger.info("Agent '{}' initialised (workspace={})", name, workspace_dir)
    return agent


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

class PipelineOrchestrator:
    """
    State-aware orchestrator for the @architect → @coder ↔ @qa pipeline.

    State per session:
        PLANNING   — messages are forwarded directly to @architect for
                     conversational refinement.  The architect's responses
                     are echoed back to the user.
        EXECUTING  — the <FINAL_SPEC> tag was detected; @coder and @qa are
                     running in the background.  Incoming user messages
                     during this phase receive a "working…" notice.

    Session keys are derived from the inbound message's channel + chat_id so
    that each unique user/conversation gets its own isolated architect thread.
    """

    def __init__(
        self,
        base_config_path: Path,
        repo_root: Path,
        on_status: Callable[[str, str, str], Awaitable[None]] | None = None,
    ) -> None:
        self.base_config_path = base_config_path
        self.repo_root = repo_root
        self.on_status = on_status

        # Per-session state: session_key → "planning" | "executing"
        self._session_state: dict[str, str] = {}

        # One bus per agent — no cross-agent message bleed
        self._user_bus  = MessageBus()
        self._arch_bus  = MessageBus()
        self._coder_bus = MessageBus()
        self._qa_bus    = MessageBus()

        cfg      = load_config(base_config_path)
        ws_root  = repo_root / "workspaces"

        self._architect = _build_agent(
            "architect",
            ws_root / "architect",
            cfg,
            self._arch_bus,
        )
        self._coder = _build_agent(
            "coder",
            ws_root / "coder",
            cfg,
            self._coder_bus,
            workspace_config_path=ws_root / "coder" / "config.json",
        )
        self._qa = _build_agent(
            "qa",
            ws_root / "qa",
            cfg,
            self._qa_bus,
            workspace_config_path=ws_root / "qa" / "config.json",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _emit(self, agent: str, event_type: str, message: str) -> None:
        """Fire the TUI / monitoring callback (swallows errors)."""
        if self.on_status:
            try:
                await self.on_status(agent, event_type, message)
            except Exception:
                pass

    async def _reply(self, channel: str, chat_id: str, content: str) -> None:
        """Publish a message back to the user's originating channel."""
        await self._user_bus.publish_outbound(
            OutboundMessage(channel=channel, chat_id=chat_id, content=content)
        )

    async def _call_agent(
        self,
        agent_loop: AgentLoop,
        agent_name: str,
        prompt: str,
        session_key: str,
    ) -> str:
        """Run one prompt through an agent and return the response string."""
        await self._emit(agent_name, "start", prompt[:120])
        response = await agent_loop.process_direct(
            content=prompt,
            session_key=session_key,
            channel="system",
            chat_id="pipeline",
            on_progress=lambda text, **_: self._emit(agent_name, "progress", text),
        )
        await self._emit(agent_name, "done", (response or "")[:200])
        return response or ""

    # ------------------------------------------------------------------
    # Stage: Architect (conversational)
    # ------------------------------------------------------------------

    async def _stage_architect(self, user_message: str, session_key: str) -> str:
        """
        Forward the user's message directly to @architect, preserving the
        full conversation history via session_key.

        The AGENTS.md persona handles all prompt logic — we pass the raw
        user message with no wrapper.
        """
        return await self._call_agent(
            self._architect,
            "@architect",
            user_message,
            session_key,          # ← real session key keeps history alive
        )

    # ------------------------------------------------------------------
    # Stages: Coder and QA (execution, non-interactive)
    # ------------------------------------------------------------------

    async def _stage_coder(self, spec: str, iteration: int) -> str:
        """Stage 2: Implement the finalised spec via OpenCode CLI."""
        prompt = (
            "Read `skills/opencode/SKILL.md` first. Then use the `exec` tool to "
            "invoke the appropriate `opencode` commands to implement the following "
            "architectural specification exactly as written. Report the generated "
            "file paths and exit status when done. Do not ask questions.\n\n"
            f"ARCHITECTURAL SPECIFICATION:\n{spec}"
        )
        result = await self._call_agent(
            self._coder, "@coder", prompt, f"pipeline:coder:{iteration}"
        )
        logger.info("@coder iteration {} done ({} chars)", iteration, len(result))
        return result

    async def _stage_qa(self, coder_output: str, spec: str, iteration: int) -> str:
        """Stage 3: Run QA gate against the coder output."""
        prompt = (
            "Read `skills/quality-assurance/SKILL.md` first. Evaluate the build "
            "below against the original specification. Run all lint and test "
            "commands via `exec`. Inspect key files with `read_file`. Output "
            "exactly one VERDICT: APPROVE or VERDICT: REJECT with a structured "
            "bug report. Do not ask questions.\n\n"
            f"ORIGINAL SPECIFICATION:\n{spec}\n\n"
            f"CODER OUTPUT / FILE PATHS:\n{coder_output}"
        )
        verdict = await self._call_agent(
            self._qa, "@qa", prompt, f"pipeline:qa:{iteration}"
        )
        logger.info("@qa iteration {} verdict: {}", iteration, verdict[:100])
        return verdict

    # ------------------------------------------------------------------
    # Background execution pipeline (coder ↔ qa loop)
    # ------------------------------------------------------------------

    async def _run_execution_pipeline(
        self,
        spec: str,
        reply_channel: str,
        reply_chat_id: str,
        session_key: str,
    ) -> None:
        """
        Run the coder ↔ qa loop in the background.
        Called via asyncio.create_task so the event loop stays non-blocking.
        Clears the session's EXECUTING state when done so the user can start
        a new planning session.
        """
        try:
            await self._emit(
                "orchestrator", "executing",
                f"Execution pipeline started for session {session_key}"
            )

            for iteration in range(1, _MAX_QA_LOOPS + 1):
                coder_output = await self._stage_coder(spec, iteration)
                qa_output    = await self._stage_qa(coder_output, spec, iteration)

                if _APPROVE_RE.search(qa_output):
                    await self._emit("orchestrator", "approved", qa_output[:200])
                    await self._reply(
                        reply_channel, reply_chat_id,
                        f"✅ Build approved after {iteration} iteration(s).\n\nQA Report:\n{qa_output}",
                    )
                    return

                if _REJECT_RE.search(qa_output):
                    await self._emit(
                        "orchestrator", "rejected",
                        f"Iteration {iteration}: {qa_output[:200]}"
                    )
                    if iteration == _MAX_QA_LOOPS:
                        break
                    # Append the bug report to the spec for the next coder pass
                    spec = (
                        f"{spec}\n\n"
                        f"--- QA REJECTION (iteration {iteration}) ---\n{qa_output}"
                    )
                else:
                    await self._emit("orchestrator", "ambiguous", qa_output[:200])

            # Exhausted retries
            await self._reply(
                reply_channel, reply_chat_id,
                f"❌ Pipeline could not pass QA after {_MAX_QA_LOOPS} iteration(s). "
                "Escalating for human review.",
            )
            await self._emit("orchestrator", "escalated", "Max QA loops reached")

        finally:
            # Return session to PLANNING so the user can iterate further
            self._session_state[session_key] = "planning"

    # ------------------------------------------------------------------
    # Main event loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Listen on the user bus and route each message through the state machine.

        PLANNING  → forward to @architect; check response for <FINAL_SPEC>.
        EXECUTING → send a "still working" notice; ignore message body.
        """
        logger.info("Orchestrator started — listening for intents")
        await self._emit("orchestrator", "ready", "Listening for intents")

        while True:
            try:
                msg: InboundMessage = await asyncio.wait_for(
                    self._user_bus.consume_inbound(), timeout=2.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            # Derive a stable session key from the user's channel + chat_id
            session_key = f"architect:{msg.channel}:{msg.chat_id}"
            state = self._session_state.get(session_key, "planning")

            if state == "executing":
                # Don't interrupt a running build — inform and move on
                await self._reply(
                    msg.channel, msg.chat_id,
                    "⏳ Your build is still running. I'll notify you when it's done.",
                )
                continue

            # ── PLANNING state ──────────────────────────────────────────────
            arch_response = await self._stage_architect(msg.content, session_key)

            # Check for the <FINAL_SPEC> trigger
            match = _FINAL_SPEC_RE.search(arch_response)
            if match:
                spec = match.group(1).strip()
                logger.info(
                    "FINAL_SPEC detected ({} chars) — delegating to @coder/@qa",
                    len(spec),
                )

                # Mark session as executing BEFORE spawning the task
                self._session_state[session_key] = "executing"

                # Acknowledge to the user
                await self._reply(
                    msg.channel, msg.chat_id,
                    "✅ Plan approved. Delegating execution to @coder and @qa...\n"
                    "I'll message you here when the build is complete.",
                )

                # Fire execution in the background — does not block the event loop
                asyncio.create_task(
                    self._run_execution_pipeline(
                        spec=spec,
                        reply_channel=msg.channel,
                        reply_chat_id=msg.chat_id,
                        session_key=session_key,
                    ),
                    name=f"exec:{session_key}",
                )

            else:
                # Still in planning — echo architect's reply directly to the user
                await self._reply(msg.channel, msg.chat_id, arch_response)

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    @property
    def user_bus(self) -> MessageBus:
        """Expose the user-facing bus so channel adapters can publish to it."""
        return self._user_bus


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

async def _main(config_path: str) -> None:
    cfg_path = Path(config_path)
    repo_root = Path(__file__).parent.parent.resolve()

    orchestrator = PipelineOrchestrator(
        base_config_path=cfg_path,
        repo_root=repo_root,
    )

    from nanobot.channels.manager import ChannelManager
    cfg = load_config(cfg_path)
    channel_manager = ChannelManager(config=cfg, bus=orchestrator.user_bus)
    asyncio.create_task(channel_manager.start_all())

    await orchestrator.run()


if __name__ == "__main__":
    import sys
    cfg_arg = (
        sys.argv[1] if len(sys.argv) > 1
        else str(Path.home() / ".nanobot" / "config.json")
    )
    asyncio.run(_main(cfg_arg))
