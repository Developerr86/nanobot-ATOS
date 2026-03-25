# 🐈 nanobot Context

## 📌 Project Overview
**nanobot** is an ultra-lightweight personal AI assistant framework designed to be simple, fast, and research-ready. It delivers core agentic functionality with a minimal footprint, inspired by larger agent frameworks but focused on being 99% smaller and more readable.

### 📐 Codebase Size
- **Total Lines of Code**: Approximately ~15,000 - 20,000 lines (including all channel and provider adapters).
- **Core Agent Logic**: ~2,000 - 3,000 lines.
- **Languages**: 
    - **Python**: Primary language for agent logic, bus, and adapters.
    - **TypeScript**: Used for the WhatsApp bridge and certain web components.

---

## 🏗️ Project Structure

The project is organized into several key modules:

### 🐍 `nanobot/` (Core Python Package)
- **`agent/`**: The brain of the assistant. Contains the agent loop (`loop.py`), memory management (`memory.py`), and tool handling (`skills.py`).
- **`bus/`**: An event-driven message bus for internal communication.
- **`channels/`**: Integration adapters for various chat platforms (Telegram, Discord, Feishu, Slack, WhatsApp, QQ, etc.).
- **`providers/`**: Adapters for LLM services (OpenRouter, Anthropic, Gemini, DeepSeek, OpenAI, etc.).
- **`skills/`**: Implementation of specific agent skills and tool definitions.
- **`session/`**: Manages user sessions and conversational history.
- **`cron/`**: Handles scheduled tasks and recurring agent actions.
- **`config/`**: Configuration management system for API keys and system defaults.
- **`heartbeat/`**: Health monitoring and status reporting.

### 🌉 `bridge/`
- Node.js/TypeScript code providing bridge functionality for channels like WhatsApp that require a JavaScript runtime.

### 🧪 `tests/`
- Comprehensive test suite for core logic and integration points.

### 📂 `docs/`
- Documentation for developers, including channel plugin guides and API references.

---

## 🏷️ Metadata
- **Name**: `nanobot-ai`
- **Version**: `0.1.4.post5`
- **License**: MIT
- **Dependencies**: 
    - `litellm` (LLM abstraction)
    - `pydantic` (Data validation)
    - `websockets` / `httpx` (Networking)
    - `typer` (CLI interface)
    - `mcp` (Model Context Protocol)
- **Primary OS Support**: Windows, Linux, macOS.

---

## 🛠️ Key Commands
- `nanobot onboard`: Initialize configuration.
- `nanobot agent`: Start the CLI agent.
- `nanobot gateway`: Start the multi-channel gateway.
- `nanobot channels login`: Login to external channels like WhatsApp.


# Nanobot Context & Developer Guide

## Repository Overview
**Nanobot** is an ultra-lightweight personal AI assistant designed to deliver core agent functionality with minimal code complexity. It acts as a continuous process capable of chatting across multiple channels, executing shell commands, reading/writing files, spawning background subagents, and triggering periodic tasks. 

When modifying the codebase or adding new capabilities, prioritize maintaining its lightweight, low-footprint philosophy.

---

## Directory Structure & Component Mapping

The core logic resides in the `nanobot/` directory. 

### 1. `nanobot/agent/` (The Core Brain)
This directory houses the primary reasoning and execution logic.
* **`loop.py`**: Contains the main Agent Loop. This is where the LLM evaluates the prompt, decides to call tools, and returns responses.
* **`context.py`**: The prompt builder. It constructs the system instructions, injects memory context, time, and user environment data.
* **`memory.py`**: Handles persistent memory state across conversations.
* **`skills.py`**: Loads dynamic skills from the `skills/` directory.
* **`subagent.py`**: Manages background task execution. Subagents run their own isolated loops and report back to the main agent.
* **`tools/`**: Contains all native tools available to the LLM.
    * `registry.py`: The tool registry where tools are mapped to callable functions.
    * `filesystem.py`, `shell.py`, `web.py`: Built-in capabilities for reading/writing, shell execution, and web searching.

### 2. `nanobot/channels/` (I/O & Integrations)
Handles the communication layer between the bot and external platforms (Telegram, Discord, Slack, etc.). 
* To add a new chat platform, you must create a new channel plugin here and register it so the Message Bus can route I/O appropriately.

### 3. `nanobot/bus/` (Event Routing)
* **`queue.py` & `events.py`**: The internal messaging infrastructure. For example, when a subagent finishes a task, it publishes an `InboundMessage` to the bus, which routes it back to the main agent or user.

### 4. `nanobot/providers/` (LLM Backends)
* **`registry.py`**: The single source of truth for LLM configurations. If you need to add support for a new AI model provider, you only need to add a `ProviderSpec` entry here and update the `ProvidersConfig` schema.

### 5. `nanobot/templates/` & Workspace Config
* **`AGENTS.md`**: Contains base instructions for the agent (e.g., rules for scheduling reminders vs. heartbeat tasks). 
* **`HEARTBEAT.md`**: Monitored by `nanobot/heartbeat/`. If the user asks for a recurring or periodic task, the agent is instructed to modify this file using file tools, which the gateway periodically evaluates.

---

## Modifying & Extending Capabilities (Coding Agent SOP)

### A. Adding a Custom Tool
1.  **Create the Tool Class**: Create a new file in `nanobot/agent/tools/` (or append to an existing category). Ensure it defines its parameters clearly for the LLM.
2.  **Register the Tool**: Update `nanobot/agent/tools/registry.py` to ensure the tool is loaded into the agent's context during initialization.
3.  **Context**: The LLM will now automatically see the tool in its system prompt definitions.

### B. Modifying Agent Behavior / System Prompts
1.  **Direct Instructions**: To change how the bot fundamentally responds or behaves, modify `nanobot/templates/AGENTS.md` or the prompt compilation logic in `nanobot/agent/context.py`.
2.  **Subagent Instructions**: If modifying background task behavior, edit the `_build_subagent_prompt` method inside `nanobot/agent/subagent.py`.

### C. Implementing Custom Agents (Subagents)
Nanobot natively supports background execution via `SubagentManager`.
1.  **Lifecycle**: Subagents are triggered via the `spawn` tool, running isolated from the main conversation.
2.  **Tool Scope**: By default, subagents are spawned with a restricted subset of tools (e.g., no message tool, no nested spawning). To grant custom capabilities to subagents, inject them in `_run_subagent` within `nanobot/agent/subagent.py`.
3.  **Communication back**: Subagents announce results using `self.bus.publish_inbound(msg)` formatted as a `system` channel message. This silently triggers the main agent to summarize the results to the user.

### D. Adding Scheduled/Periodic Behaviors
1.  **Heartbeat Tasks**: If your custom agent needs to monitor something 24/7, program it to append tasks to the user's `HEARTBEAT.md` file. The system natively polls this file every heartbeat interval.
2.  **Cron**: For strict time-based tasks, the bot utilizes a `cron` tool that manages jobs internally.

---

## 🔧 Intent-Centric Pipeline Transformation Log

This section documents ongoing modifications made to adapt nanobot into an **autonomous, multi-agent code generation pipeline** for AI-Native Application Development. The target architecture is intent-driven (Discord/Telegram/WhatsApp input → specialized agents → isolated workspaces).

### Phase 1: Aggressive Pruning (Complete)

**Goal:** Strip the repo of irrelevant "personal assistant" features, retaining only the core infrastructure and the three target channels.

#### Channels Pruned (`nanobot/channels/`)
The following channel adapter files were deleted. Only `discord.py`, `telegram.py`, `whatsapp.py`, `base.py`, `manager.py`, and `registry.py` are retained.
- `slack.py`, `feishu.py`, `dingtalk.py`, `matrix.py`, `email.py`, `qq.py`, `wecom.py`, `weixin.py`, `mochat.py`

> **Note:** `registry.py` and `__init__.py` use `pkgutil` auto-discovery — no explicit import lists needed updating. Deleted files are automatically excluded from the channel discovery scan.

#### Skills Pruned (`nanobot/skills/`)
The following general-purpose skill directories were deleted:
- `weather/`, `clawhub/`, `summarize/`

**Retained:** `cron/`, `memory/`, `tmux/`, `skill-creator/`, `opencode/` (new).

#### Social Network Logic
Scanned the full codebase for "Moltbook" and "ClawdChat" references. No hardcoded routing logic existed in the Python source — these were only referenced in `README.md` as external skill examples (benign documentation, not executable logic). No code removals were necessary.

#### Verification
- `nanobot/heartbeat/` and `nanobot/cron/` remain fully intact.
- `nanobot/agent/tools/web.py` was not touched.
- `python -c "import nanobot"` confirmed no broken imports after removals.

---

### Phase 2: OpenCode CLI Integration (Complete)

**Goal:** Configure the `@coder` agent to autonomously delegate all code generation to the `opencode` CLI via nanobot's native `exec` tool.

#### Files Created

| File | Purpose |
|---|---|
| `nanobot/skills/opencode/SKILL.md` | Skill definition teaching the LLM the full OpenCode CLI command surface, rules of engagement, and delegation workflow. |
| `workspaces/coder/config.json` | Workspace config enabling the `exec` tool and setting `pathAppend` for standard binary locations. |
| `workspaces/coder/AGENTS.md` | Persona override redefining the `@coder` agent as a strict CLI executor — no manual code writing, only `exec` calls. |

#### `workspaces/coder/config.json` (Key Settings)
```json
{
  "tools": {
    "exec": {
      "enable": true,
      "pathAppend": "/usr/local/bin:/opt/homebrew/bin:~/.local/bin"
    }
  }
}
```

#### OpenCode CLI Command Surface (documented in SKILL.md)
Primary commands: `run`, `generate`, `agent`, `session`, `db`, `mcp`, `models`, `providers`, `account`, `github`, `pr`, `stats`, `serve`, `workspace-serve`, `web`, `import`, `export`, `upgrade`, `acp`, `debug`.

Key subcommands: `session list/open/remove/rename`, `mcp list/add/remove`, `models list`, `providers list/add`, `github auth`, `pr create/list`, `debug config/lsp/ripgrep`.

#### @coder Workflow (from `AGENTS.md`)
1. Receive architectural specification from `@architect`.
2. Consult `skills/opencode/SKILL.md` for CLI syntax.
3. Use `exec` tool to invoke `opencode run` / `opencode generate` with the spec as context.
4. Report terminal output and final status to `@qa`. No markdown code blocks. No manual writing.

---

### Phase 3: @qa Agent Integration (Complete)

**Goal:** Configure the `@qa` agent as the ruthless gatekeeper of the pipeline — running tests, performing static analysis, AI-driven code reviews, and issuing structured APPROVE/REJECT verdicts.

#### Files Created

| File | Purpose |
|---|---|
| `workspaces/qa/config.json` | Workspace config enabling `exec`, `read_file`, and `list_dir` tools with standard `pathAppend`. |
| `workspaces/qa/AGENTS.md` | Persona override defining the `@qa` agent as a strict QA engineer that issues only verdicts. |
| `nanobot/skills/quality-assurance/SKILL.md` | Full QA playbook: lint → test → inspect → verdict. |

#### Workspace Isolation Verified
```
workspaces/
├── coder/
│   ├── AGENTS.md   ← @coder persona
│   └── config.json ← exec-only
└── qa/
    ├── AGENTS.md   ← @qa persona
    └── config.json ← exec + read_file + list_dir
```
The two workspaces share no config, no session state, and no file paths.

#### QA Playbook Summary (`quality-assurance/SKILL.md`)
1. **Orient** — `list_dir` to verify directory structure matches the spec.
2. **Lint** — `exec` ESLint / Flake8 / Ruff against the target directory.
3. **Test** — `exec` Jest / Pytest with coverage flags.
4. **Inspect** — `read_file` on entry points, API handlers, auth logic, and lint-flagged files.
5. **Verdict** — Exactly one structured payload:
   - `VERDICT: APPROVE` if all gates pass.
   - `VERDICT: REJECT` with file/line bug report sent back to `@coder`.

#### @qa Rules (from `AGENTS.md`)
- Does not write features or speculate.
- Does not approve a build with a single failing test, lint error, or unhandled input.
- Outputs only the structured verdict payload — no casual conversation.

---

### Phase 4: Master Orchestrator & Live TUI (Complete)

**Goal:** Stitch all three agents into a unified autonomous pipeline and provide a real-time TUI for monitoring.

#### Files Created

| File | Purpose |
|---|---|
| `nanobot/orchestrator.py` | Async pipeline orchestrator routing intents through `@architect → @coder ↔ @qa`. |
| `nanobot/tui_monitor.py` | Rich live TUI with split-pane agent monitoring and color-coded event log. |

#### Orchestrator Architecture (`orchestrator.py`)
- **`PipelineOrchestrator`** creates three fully isolated `AgentLoop` instances, each with its own `MessageBus` and workspace-specific `ExecToolConfig`.
- **Stage 1 — `@architect`**: Converts raw user intent into an unambiguous spec.
- **Stage 2 — `@coder`**: Executes `opencode` CLI commands against the spec; returns file paths.
- **Stage 3 — `@qa`**: Runs lint + tests + code review; emits `VERDICT: APPROVE` or `VERDICT: REJECT`.
- **Reject loop**: On `REJECT`, the bug report is appended to the spec and the coder is re-invoked (up to `_MAX_QA_LOOPS = 3` times). On exhaustion, the pipeline escalates to human review via the original channel.
- **`on_status` callback**: Every significant event fires an async callback consumed by the TUI.

#### TUI Architecture (`tui_monitor.py`)
- **`EventStore`**: Async-safe ring buffer (`deque(maxlen=200)`) holding all pipeline events, partitioned by agent.
- **Layout** (Rich `Layout` + `Live`, refreshes at 4 Hz):
  - Left pane: scrolling event log (all agents, last 40 lines)
  - Right-top: `@architect` activity panel — **Magenta**
  - Right-mid: `@coder` activity panel — **Cyan**
  - Right-bot: `@qa` verdict history — **Green** (APPROVE) / **Red** (REJECT)

#### How to Run
```bash
# Run the full pipeline + TUI together (recommended):
python -m nanobot.tui_monitor ~/.nanobot/config.json

# Run orchestrator only (headless):
python -m nanobot.orchestrator ~/.nanobot/config.json
```

> `rich` is already listed as a dependency in `pyproject.toml` via the nanobot CLI. No new packages required.