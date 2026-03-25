"""
orchestrator.py — Intent-Centric Multi-Agent Pipeline Orchestrator

Routes user intents through the @architect → @coder → @qa triad via nanobot's
internal MessageBus. Each agent runs its own isolated AgentLoop bound to its
own workspace and config.

Usage:
    python -m nanobot.orchestrator --config ~/.nanobot/config.json
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
# Verdict detection helpers
# ---------------------------------------------------------------------------

_APPROVE_RE = re.compile(r"\bVERDICT\s*:\s*APPROVE\b", re.IGNORECASE)
_REJECT_RE = re.compile(r"\bVERDICT\s*:\s*REJECT\b", re.IGNORECASE)
_MAX_QA_LOOPS = 3  # maximum coder→qa cycles before escalating


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
    """Construct an AgentLoop for one of the three pipeline agents."""
    cfg = base_config

    # Merge per-workspace config.json overrides if present
    if workspace_config_path and workspace_config_path.exists():
        with open(workspace_config_path, encoding="utf-8") as f:
            overrides = json.load(f)
        # Apply exec overrides
        exec_overrides = overrides.get("tools", {}).get("exec", {})
        exec_cfg = ExecToolConfig(
            timeout=exec_overrides.get("timeout", cfg.tools.exec.timeout),
            path_append=exec_overrides.get("pathAppend", cfg.tools.exec.path_append),
        )
    else:
        exec_cfg = cfg.tools.exec

    # Build the LLM provider (reuse base config credentials)
    from nanobot.cli.commands import _make_provider  # shared factory
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
    Coordinates the @architect → @coder → @qa pipeline.

    Each agent has its own isolated AgentLoop + workspace.  A shared
    *event bus* carries the hand-off payloads between stages; a separate
    *user bus* connects to the inbound Discord/WhatsApp channel messages.
    """

    def __init__(
        self,
        base_config_path: Path,
        repo_root: Path,
        on_status: Callable[[str, str, str], Awaitable[None]] | None = None,
    ):
        """
        Args:
            base_config_path: Path to the main nanobot config.json with API keys.
            repo_root:        Root of the nanobot repo (contains workspaces/).
            on_status:        Optional async callback(agent, event_type, message)
                              called for every significant pipeline event (used by TUI).
        """
        self.base_config_path = base_config_path
        self.repo_root = repo_root
        self.on_status = on_status

        # One bus per agent — prevents cross-agent message bleed
        self._user_bus = MessageBus()       # inbound from channels
        self._arch_bus = MessageBus()       # architect internal bus
        self._coder_bus = MessageBus()      # coder internal bus
        self._qa_bus = MessageBus()         # qa internal bus

        cfg = load_config(base_config_path)

        ws_root = repo_root / "workspaces"
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
        """Fire the status callback (non-blocking, swallows errors)."""
        if self.on_status:
            try:
                await self.on_status(agent, event_type, message)
            except Exception:
                pass

    async def _call_agent(
        self,
        agent_loop: AgentLoop,
        agent_name: str,
        prompt: str,
        session_key: str,
    ) -> str:
        """Run a single prompt through an agent and return its response."""
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
    # Pipeline stages
    # ------------------------------------------------------------------

    async def _stage_architect(self, user_intent: str) -> str:
        """Stage 1: Produce an architectural specification from the user intent."""
        prompt = (
            "You are @architect. Analyse the following user intent and produce a "
            "complete, unambiguous architectural specification that the @coder can "
            "execute without further clarification.\n\n"
            f"USER INTENT:\n{user_intent}"
        )
        spec = await self._call_agent(
            self._architect, "@architect", prompt, "pipeline:architect"
        )
        logger.info("@architect spec produced ({} chars)", len(spec))
        return spec

    async def _stage_coder(self, spec: str, iteration: int) -> str:
        """Stage 2: Implement the spec using OpenCode CLI."""
        prompt = (
            "You are @coder. Read `skills/opencode/SKILL.md` first, then use the "
            "`exec` tool to invoke the appropriate `opencode` commands to implement "
            "the following architectural specification. Report the output file paths "
            "and exit status when done.\n\n"
            f"ARCHITECTURAL SPECIFICATION:\n{spec}"
        )
        result = await self._call_agent(
            self._coder, "@coder", prompt, f"pipeline:coder:{iteration}"
        )
        logger.info("@coder iteration {} done ({} chars)", iteration, len(result))
        return result

    async def _stage_qa(self, coder_output: str, spec: str, iteration: int) -> str:
        """Stage 3: Run QA against the coder output."""
        prompt = (
            "You are @qa. Read `skills/quality-assurance/SKILL.md` first. Then "
            "evaluate the build described below against the original spec. Run all "
            "lint and test commands via the `exec` tool. Inspect key files with "
            "`read_file`. Output exactly one VERDICT: APPROVE or VERDICT: REJECT "
            "with details.\n\n"
            f"ORIGINAL SPEC:\n{spec}\n\n"
            f"CODER OUTPUT / FILE PATHS:\n{coder_output}"
        )
        verdict = await self._call_agent(
            self._qa, "@qa", prompt, f"pipeline:qa:{iteration}"
        )
        logger.info("@qa iteration {} verdict: {}", iteration, verdict[:100])
        return verdict

    # ------------------------------------------------------------------
    # Main pipeline driver
    # ------------------------------------------------------------------

    async def _run_pipeline(self, user_intent: str, reply_channel: str, reply_chat_id: str) -> None:
        """Execute the full architect → coder ⟷ qa loop for one user intent."""
        await self._emit("orchestrator", "start", f"Pipeline started for: {user_intent[:80]}")

        # Stage 1: Architect
        spec = await self._stage_architect(user_intent)

        # Stage 2/3: Coder ↔ QA loop
        for iteration in range(1, _MAX_QA_LOOPS + 1):
            coder_output = await self._stage_coder(spec, iteration)
            qa_output = await self._stage_qa(coder_output, spec, iteration)

            if _APPROVE_RE.search(qa_output):
                await self._emit("orchestrator", "approved", qa_output[:200])
                final_msg = (
                    f"✅ Build approved after {iteration} iteration(s).\n\n"
                    f"QA Report:\n{qa_output}"
                )
                await self._user_bus.publish_outbound(OutboundMessage(
                    channel=reply_channel, chat_id=reply_chat_id, content=final_msg,
                ))
                return

            if _REJECT_RE.search(qa_output):
                await self._emit("orchestrator", "rejected", f"Iteration {iteration}: {qa_output[:200]}")
                if iteration == _MAX_QA_LOOPS:
                    break
                # Feed the bug report back into the spec for the next coder pass
                spec = f"{spec}\n\n--- QA REJECTION (iteration {iteration}) ---\n{qa_output}"
            else:
                # Ambiguous output — treat as failure
                await self._emit("orchestrator", "ambiguous", qa_output[:200])

        # Exhausted retries
        await self._user_bus.publish_outbound(OutboundMessage(
            channel=reply_channel,
            chat_id=reply_chat_id,
            content=(
                f"❌ Pipeline could not pass QA after {_MAX_QA_LOOPS} iteration(s). "
                "Escalating for human review."
            ),
        ))
        await self._emit("orchestrator", "escalated", "Max QA loops reached")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """
        Start the orchestrator event loop.

        Listens on the user bus for inbound messages (published by channel
        adapters) and dispatches each intent through the pipeline.
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

            # Fire pipeline as a background task so the loop stays responsive
            asyncio.create_task(
                self._run_pipeline(msg.content, msg.channel, msg.chat_id),
                name=f"pipeline:{msg.session_key}",
            )

    @property
    def user_bus(self) -> MessageBus:
        """Expose the user-facing bus so channel adapters can publish to it."""
        return self._user_bus


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

async def _main(config_path: str) -> None:
    repo_root = Path(__file__).parent.parent.resolve()  # nanobot/ → repo root
    orchestrator = PipelineOrchestrator(
        base_config_path=Path(config_path),
        repo_root=repo_root,
    )
    await orchestrator.run()


if __name__ == "__main__":
    import sys
    cfg = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / ".nanobot" / "config.json")
    asyncio.run(_main(cfg))
