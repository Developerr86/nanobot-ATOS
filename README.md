<div align="center">
  <img src="nanobot_logo.png" alt="nanobot" width="500">
  <h1>🐈 nanobot: Intent-Centric Multi-Agent Development Pipeline</h1>
  <p>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <a href="https://discord.gg/MnCvHqpUGB"><img src="https://img.shields.io/badge/Discord-Community-5865F2?style=flat&logo=discord&logoColor=white" alt="Discord"></a>
  </p>
</div>

> **This is a forked and purpose-built version of nanobot.** The original framework has been transformed into an autonomous, multi-agent code generation pipeline for AI-Native Application Development. It is no longer a general-purpose personal assistant.

## What This Is

This project uses `nanobot`'s core event bus, scheduling, and tool infrastructure as a foundation for a **three-agent autonomous development pipeline** that operates over Discord, Telegram, or WhatsApp.

A user sends a natural language intent (e.g. *"Build a farmer login page with OTP auth"*). The pipeline autonomously:

1. **`@architect`** — Analyses the intent and produces a complete architectural specification.
2. **`@coder`** — Reads the spec and executes the [OpenCode CLI](https://opencode.ai) to generate actual code.
3. **`@qa`** — Runs lint, unit tests, and an AI code review. Issues a structured `VERDICT: APPROVE` or `VERDICT: REJECT`.

If rejected, the bug report is automatically fed back to `@coder` and the loop repeats (up to 3 times). A live **Rich TUI dashboard** visualises the entire pipeline in real time.

---

## Table of Contents

- [Architecture](#-architecture)
- [Install](#-install)
- [Configuration](#️-configuration)
- [Quick Start (CLI)](#-quick-start-cli)
- [Running the Full Pipeline](#-running-the-full-pipeline)
- [Live TUI Monitor](#-live-tui-monitor)
- [Chat Channels](#-chat-channels)
- [Agent Workspaces](#-agent-workspaces)
- [Skills Reference](#-skills-reference)
- [Project Structure](#-project-structure)
- [CLI Reference](#-cli-reference)
- [Extending the Pipeline](#-extending-the-pipeline)

---

## 🏗 Architecture

```
User (Discord / Telegram / WhatsApp)
          │
          ▼
  PipelineOrchestrator              ← nanobot/orchestrator.py
  ┌────────────────────────────────────────────────────┐
  │                                                    │
  │  Stage 1: @architect ─────────── spec             │
  │           workspaces/architect/                    │
  │                                                    │
  │  Stage 2: @coder ─────────────── opencode CLI     │
  │           workspaces/coder/                        │
  │           skills/opencode/SKILL.md                 │
  │                    │                               │
  │       ┌────────────┘                               │
  │       ▼                                            │
  │  Stage 3: @qa ──── APPROVE ───────────► User      │
  │           workspaces/qa/       REJECT              │
  │           skills/quality-assurance/SKILL.md   │   │
  │                                               └───┘
  │                                          (loop, max 3x)
  └────────────────────────────────────────────────────┘
          │
          ▼
   TUI Dashboard                    ← nanobot/tui_monitor.py
   [Magenta: @architect | Cyan: @coder | Green: @qa]
```

**Core infrastructure retained from nanobot:**
- `MessageBus` — async inbound/outbound event routing
- `AgentLoop` — LLM reasoning + tool execution engine
- `cron/` — scheduled task support
- `heartbeat/` — 24/7 health monitoring
- `agent/tools/web.py` — web search and fetch

---

## 📦 Install

**Clone and install in editable mode** (required — the orchestrator imports from the local package):

```bash
git clone <your-fork-url>
cd nanobot
pip install -e .
```

Verify the install:

```bash
nanobot --version
```

**Requirements:**
- Python ≥ 3.11
- `opencode` CLI installed on the host ([opencode.ai](https://opencode.ai))
- Node.js ≥ 18 (only if using WhatsApp)

---

## ⚙️ Configuration

The main config file lives at `~/.nanobot/config.json`. Run `nanobot onboard` once to generate it with defaults, then edit.

### Minimal config (API key only)

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-YOUR_KEY"
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-opus-4-5",
      "provider": "openrouter"
    }
  }
}
```

### Supported Providers

| Provider | Field | Get Key |
|---|---|---|
| OpenRouter (recommended) | `openrouter.apiKey` | [openrouter.ai](https://openrouter.ai/keys) |
| Anthropic (Claude direct) | `anthropic.apiKey` | [console.anthropic.com](https://console.anthropic.com) |
| OpenAI (GPT direct) | `openai.apiKey` | [platform.openai.com](https://platform.openai.com) |
| Google Gemini | `gemini.apiKey` | [aistudio.google.com](https://aistudio.google.com) |
| DeepSeek | `deepseek.apiKey` | [platform.deepseek.com](https://platform.deepseek.com) |
| Groq (also Whisper transcription) | `groq.apiKey` | [console.groq.com](https://console.groq.com) |
| Ollama (local) | `ollama.apiBase` | `http://localhost:11434` |
| Azure OpenAI | `azure_openai.apiKey` + `apiBase` | [portal.azure.com](https://portal.azure.com) |
| Any OpenAI-compatible endpoint | `custom.apiKey` + `apiBase` | — |

### Exec Tool (required for pipeline)

The pipeline agents use the `exec` tool to run shell commands. Enable it globally or per-workspace:

```json
{
  "tools": {
    "exec": {
      "timeout": 120
    }
  }
}
```

Per-workspace overrides in `workspaces/coder/config.json` and `workspaces/qa/config.json` are already pre-configured.

---

## 🚀 Quick Start (CLI)

Test that your configuration works before running the full pipeline:

**1. Initialise the default workspace:**

```bash
nanobot onboard --config ~/.nanobot/config.json
```

**2. Send a single message:**

```bash
nanobot agent -m "Hello! What model are you?" --config ~/.nanobot/config.json
```

**3. Interactive chat session:**

```bash
nanobot agent --config ~/.nanobot/config.json
```

In the interactive session:

| Command | Effect |
|---|---|
| `/new` | Start a fresh conversation |
| `/stop` | Cancel the current running task |
| `/restart` | Restart the bot process |
| `/help` | Show available commands |
| `exit` or `Ctrl+C` | Quit |

---

## 🔁 Running the Full Pipeline

### Step 1: Scaffold the agent workspaces

Each agent needs its own workspace directory initialised with template files. Run this once for each:

```bash
# Back up the custom AGENTS.md files first — onboard will overwrite them
cp workspaces/coder/AGENTS.md /tmp/coder_agents_backup.md
cp workspaces/qa/AGENTS.md /tmp/qa_agents_backup.md

# Scaffold workspaces
nanobot onboard --config ~/.nanobot/config.json --workspace workspaces/architect
nanobot onboard --config ~/.nanobot/config.json --workspace workspaces/coder
nanobot onboard --config ~/.nanobot/config.json --workspace workspaces/qa

# Restore custom personas
cp /tmp/coder_agents_backup.md workspaces/coder/AGENTS.md
cp /tmp/qa_agents_backup.md workspaces/qa/AGENTS.md
```

### Step 2: Verify opencode is on PATH

```bash
opencode --version
```

If not found, install it per the [OpenCode docs](https://opencode.ai) and ensure it's in one of:
- `/usr/local/bin`
- `/opt/homebrew/bin`
- `~/.local/bin`

These paths are pre-configured in `workspaces/coder/config.json`.

### Step 3: Run the pipeline headlessly

```bash
python -m nanobot.orchestrator ~/.nanobot/config.json
```

To send a test intent, add this before `await orchestrator.run()` in `nanobot/orchestrator.py`:

```python
from nanobot.bus.events import InboundMessage
await orchestrator.user_bus.publish_inbound(InboundMessage(
    channel="cli",
    sender_id="user",
    chat_id="direct",
    content="Build a farmer login page with OTP authentication for KisanSahay",
))
```

---

## 🖥 Live TUI Monitor

Run the orchestrator **and** the live dashboard together in a single process:

```bash
python -m nanobot.tui_monitor ~/.nanobot/config.json
```

The TUI renders a split-pane layout:

```
┌──────────────────────────┬─────────────────────────────────┐
│  📡 Event Log            │  @architect (Magenta)            │
│  [03:52:00] ▶ @arch...  │  [03:52:01] ✓ Spec produced     │
│  [03:52:10] ▶ @coder... ├─────────────────────────────────┤
│  [03:53:00] ✅ @qa AP.. │  @coder (Cyan)                  │
│                          │  [03:52:10] ↳ Running opencode  │
│                          ├─────────────────────────────────┤
│                          │  @qa Verdicts (Green)            │
│                          │  [03:53:00] ✅ VERDICT: APPROVE │
└──────────────────────────┴─────────────────────────────────┘
```

- **Left pane** — Scrolling log of all events from all agents (last 40 lines)
- **Right-top** — `@architect` current activity — **Magenta**
- **Right-mid** — `@coder` current activity — **Cyan**
- **Right-bot** — `@qa` verdict history — **Green** (APPROVE) / **Red** (REJECT)

Press `Ctrl+C` to exit.

---

## 💬 Chat Channels

The pipeline ingests user intents from connected chat channels. Start the full gateway for channel support:

```bash
nanobot gateway --config ~/.nanobot/config.json
```

### Telegram (Recommended)

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_TELEGRAM_USER_ID"]
    }
  }
}
```

1. Create a bot via `@BotFather` on Telegram.
2. Add the token and your user ID to config.
3. Run `nanobot gateway`.

### Discord

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_DISCORD_USER_ID"],
      "groupPolicy": "mention"
    }
  }
}
```

1. Create an app at [discord.com/developers](https://discord.com/developers/applications).
2. Enable **Message Content Intent** under the Bot settings.
3. Invite the bot to your server with `Send Messages` and `Read Message History` permissions.
4. Run `nanobot gateway`.

> `groupPolicy`: `"mention"` (respond only when @mentioned) or `"open"` (respond to all).

### WhatsApp

Requires Node.js ≥ 18.

```bash
# Terminal 1 — link your device
nanobot channels login

# Terminal 2 — start gateway
nanobot gateway --config ~/.nanobot/config.json
```

```json
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "allowFrom": ["+1234567890"]
    }
  }
}
```

Scan the QR code with **WhatsApp → Settings → Linked Devices**.

---

## 🗂 Agent Workspaces

Each agent is isolated in its own workspace directory. The pipeline respects these boundaries:

```
workspaces/
├── architect/        ← @architect workspace (no exec access)
│   └── AGENTS.md    ← Custom persona (place here manually)
├── coder/
│   ├── AGENTS.md    ← Strict executor persona (pre-configured)
│   └── config.json  ← exec tool enabled + opencode pathAppend
└── qa/
    ├── AGENTS.md    ← Ruthless QA engineer persona (pre-configured)
    └── config.json  ← exec + read_file + list_dir enabled
```

### @coder Rules (from `workspaces/coder/AGENTS.md`)
- Does NOT write code manually in markdown blocks.
- Uses `exec` tool to call `opencode` CLI commands.
- Reports file paths and exit status; hands off to `@qa`.

### @qa Rules (from `workspaces/qa/AGENTS.md`)
- Does NOT write features or speculate.
- Runs lint, tests, and inspects code with `read_file`.
- Issues exactly one verdict: `VERDICT: APPROVE` or `VERDICT: REJECT`.
- On `REJECT`, includes a structured bug report with file and line references.

---

## 📚 Skills Reference

Skills are Markdown files in `nanobot/skills/<name>/SKILL.md` that the LLM reads on demand to understand a capability.

### `skills/opencode/` — OpenCode CLI

Teaches `@coder` how to invoke the OpenCode CLI. Key commands:

| Command | Purpose |
|---|---|
| `opencode run [prompt]` | Execute an AI task against the project |
| `opencode generate [prompt]` | Generate new code from a prompt |
| `opencode pr create` | Open a pull request from the session's changes |
| `opencode session list` | List all sessions |
| `opencode providers list` | List configured AI providers |
| `opencode debug config` | Inspect CLI configuration |

### `skills/quality-assurance/` — QA Playbook

Teaches `@qa` a five-step evaluation protocol:

1. **Orient** — `list_dir` to verify directory structure
2. **Lint** — `exec` ESLint / Flake8 / Ruff
3. **Test** — `exec` Jest / Pytest with coverage
4. **Inspect** — `read_file` on entry points, API handlers, auth logic
5. **Verdict** — `VERDICT: APPROVE` or `VERDICT: REJECT` with structured report

### `skills/cron/` — Scheduled Tasks
### `skills/memory/` — Long-term Memory
### `skills/tmux/` — Terminal Session Management
### `skills/skill-creator/` — Create New Skills at Runtime

---

## 📁 Project Structure

```
nanobot/                   ← Repo root
├── nanobot/               ← Core Python package
│   ├── agent/
│   │   ├── loop.py        ← Main AgentLoop (LLM → tools → response)
│   │   ├── context.py     ← System prompt builder
│   │   ├── memory.py      ← Persistent memory
│   │   ├── skills.py      ← Dynamic skill loader
│   │   ├── subagent.py    ← Background sub-agent execution
│   │   └── tools/
│   │       ├── web.py     ← Web search & fetch (DO NOT MODIFY)
│   │       ├── shell.py   ← exec tool
│   │       ├── filesystem.py
│   │       └── message.py
│   ├── bus/
│   │   ├── queue.py       ← Async MessageBus
│   │   └── events.py      ← InboundMessage / OutboundMessage
│   ├── channels/
│   │   ├── discord.py     ← ✅ Retained
│   │   ├── telegram.py    ← ✅ Retained
│   │   ├── whatsapp.py    ← ✅ Retained
│   │   ├── base.py
│   │   ├── manager.py
│   │   └── registry.py    ← Auto-discovers channel plugins
│   ├── config/
│   │   ├── schema.py      ← Pydantic config models
│   │   └── loader.py      ← load_config() / save_config()
│   ├── skills/
│   │   ├── opencode/      ← OpenCode CLI skill (Phase 2)
│   │   ├── quality-assurance/ ← QA playbook (Phase 3)
│   │   ├── cron/
│   │   ├── memory/
│   │   ├── tmux/
│   │   └── skill-creator/
│   ├── cron/              ← ✅ Retained — scheduled tasks
│   ├── heartbeat/         ← ✅ Retained — 24/7 health monitoring
│   ├── providers/         ← LLM provider adapters
│   ├── orchestrator.py    ← 🆕 Multi-agent pipeline orchestrator
│   └── tui_monitor.py     ← 🆕 Live Rich TUI dashboard
├── workspaces/
│   ├── coder/
│   │   ├── AGENTS.md      ← @coder persona
│   │   └── config.json    ← exec tool config
│   └── qa/
│       ├── AGENTS.md      ← @qa persona
│       └── config.json    ← exec + read_file + list_dir config
├── bridge/                ← WhatsApp Node.js bridge
├── tests/
├── docs/
├── context.md             ← Full developer context & transformation log
└── pyproject.toml
```

---

## 🖥 CLI Reference

```bash
# Initialise workspace and config
nanobot onboard [--config PATH] [--workspace DIR]

# Single-shot message
nanobot agent -m "your message" [--config PATH]

# Interactive chat session
nanobot agent [--config PATH] [--workspace DIR]

# Start full multi-channel gateway
nanobot gateway [--config PATH] [--port PORT]

# Link WhatsApp device
nanobot channels login

# Run the multi-agent pipeline (headless)
python -m nanobot.orchestrator [CONFIG_PATH]

# Run pipeline + live TUI
python -m nanobot.tui_monitor [CONFIG_PATH]
```

---

## 🔧 Extending the Pipeline

### Add a new agent stage

1. Create a new workspace: `workspaces/<agent-name>/`
2. Add `AGENTS.md` (persona) and `config.json` (tool permissions)
3. Add a new `_stage_<name>()` method in `nanobot/orchestrator.py`
4. Wire it into the `_run_pipeline()` method

### Add a new skill

1. Create `nanobot/skills/<skill-name>/SKILL.md`
2. Follow the YAML frontmatter format (`name:`, `description:`)
3. The `SkillsLoader` picks it up automatically — no registration needed

### Add a new LLM provider

1. Add a `ProviderConfig` entry to `ProvidersConfig` in `nanobot/config/schema.py`
2. Add a `ProviderSpec` entry to `nanobot/providers/registry.py`
3. That's it — the config loader and provider factory handle the rest

### Add a new channel plugin

See `docs/CHANNEL_PLUGIN_GUIDE.md`. Only Telegram, Discord, and WhatsApp are enabled in this fork — to add more, create a new adapter in `nanobot/channels/` following the `BaseChannel` interface.

---

## 📖 Developer Context

For a full log of all transformation phases (pruning, agent configuration, orchestrator design), see [`context.md`](./context.md).

---

## 📄 License

MIT — see [LICENSE](./LICENSE).
