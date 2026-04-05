# Claude Code in Docker

This setup runs Claude Code in an isolated Docker container with access to the `/Chores/workspace` directory.

## Quick Start

### 1. Set up your API key
```bash
# On Windows, set the environment variable
set ANTHROPIC_API_KEY=sk-your-key-here

# Or create a .env file in this directory
echo ANTHROPIC_API_KEY=sk-your-key-here > .env
```

### 2. Build and start the container
```bash
docker compose -f docker-compose.claude.yml up -d
```

### 3. Enter the container and use Claude
```bash
docker compose -f docker-compose.claude.yml exec claude bash
```

Once inside, you can use Claude Code:
```bash
# Interactive chat
claude chat

# Run a specific task
claude chat "generate a summary of chores.json"

# See what's available
claude --help
```

## What's Available in the Container

- **Python 3** with pip (for Flask API)
- **Node.js** with npm (for Angular)
- **.NET SDK 8.0** (for C# tests)
- **Claude Code CLI** (ready to use)
- **Git** and other development tools

## Workspace Structure

Everything in `/Chores/workspace` on your host is mounted to `/workspace` in the container:
- `app/` — Angular frontend + Flask API
- `ChoreTests/` — C# test suite
- `chores.json` — Data file
- `constitution.md` — Rules
- `generate_sheet.py` — Script

## Safety

The container user runs as non-root (`claude`), and changes are isolated to the container and the `workspace` volume. If Claude needs to install dependencies or make changes, they won't affect your host machine.

## Cleanup

Stop the container:
```bash
docker compose -f docker-compose.claude.yml down
```

Remove the image:
```bash
docker compose -f docker-compose.claude.yml down --rmi all
```
