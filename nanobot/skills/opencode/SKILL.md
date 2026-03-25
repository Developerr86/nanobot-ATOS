---
name: opencode
description: Execute coding tasks and generate code using the OpenCode CLI via the exec tool.
---

# OpenCode CLI Skill

## Purpose
To execute coding tasks and generate code autonomously using the `opencode` CLI tool. As the `@coder` agent, you must act as an operator for this tool. You must **NOT** write code manually in markdown blocks. Delegate all code generation to the CLI using the `exec` tool.

## Key Relevant Commands
For an AI Agent specifically building code, the most relevant commands are:
- `opencode run [prompt]`: Runs a prompt against the current project. This is the core command for executing AI tasks.
- `opencode generate [prompt]`: Generates code based on a prompt.
- `opencode pr create`: Creates a new Pull Request from the current session's changes to finalize them.

## Complete List of Commands and Subcommands
### Primary Commands
- `opencode run [prompt]`: Runs a prompt against the current project.
- `opencode generate [prompt]`: Generates code based on a prompt.
- `opencode agent`: Manages agents.
- `opencode session`: Manages sessions.
- `opencode db`: Manages the local database.
- `opencode mcp`: Manages Model Context Protocol (MCP) servers.
- `opencode models`: Manages AI models.
- `opencode providers`: Manages AI providers.
- `opencode account`: Manages the user account.
- `opencode github`: GitHub integration commands.
- `opencode pr`: Pull Request management commands.
- `opencode stats`: Displays usage statistics.
- `opencode serve`: Starts the OpenCode server.
- `opencode workspace-serve`: Starts the workspace server.
- `opencode web`: Opens the OpenCode web interface.
- `opencode import`: Imports data into OpenCode.
- `opencode export`: Exports data from OpenCode.
- `opencode upgrade`: Upgrades the OpenCode CLI.
- `opencode uninstall`: Uninstalls OpenCode.
- `opencode acp`: Agent Control Plane related commands.
- `opencode debug`: Internal debugging tools.

### Detailed Subcommand Breakdown
#### session (Session Management)
- `opencode session list`: Lists all active and past sessions.
- `opencode session open <id>`: Opens a specific session.
- `opencode session remove <id>`: Deletes a session.
- `opencode session rename <id> <name>`: Renames a session.

#### mcp (Model Context Protocol)
- `opencode mcp list`: Lists configured MCP servers.
- `opencode mcp add`: Adds a new MCP server.
- `opencode mcp remove`: Removes an MCP server.

#### models & providers
- `opencode models list`: Lists available models.
- `opencode providers list`: Lists configured AI providers.
- `opencode providers add`: Configures a new AI provider (e.g., Anthropic, OpenAI).

#### github & pr
- `opencode github auth`: Authenticates with GitHub.
- `opencode pr create`: Creates a new Pull Request from the current session's changes.
- `opencode pr list`: Lists open Pull Requests for the project.

#### debug (Troubleshooting)
- `opencode debug config`: Inspects the current CLI configuration.
- `opencode debug lsp`: Debugs Language Server Protocol integrations.
- `opencode debug ripgrep`: Tests search functionality.

## Rules of Engagement
1. The agent must ALWAYS read the architectural specification provided by the `@architect` first.
2. The agent must pass the architectural context into the `opencode run` or `opencode generate` prompts.
3. The agent must rely on the terminal output of these commands to verify success or failure.
4. The agent must report the final status to the `@qa` agent.
