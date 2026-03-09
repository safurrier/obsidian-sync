# obsidian-sync

Headless git sync daemon that keeps your Obsidian vault backed up to a git remote when the app is closed.

Matches the Obsidian Git plugin's strategy (rebase, pull-before-push, hostname-tagged commits) and automatically defers when Obsidian is running to avoid conflicts.

## Features

- **Auto-commit** with timestamped, hostname-tagged messages
- **Pull before push** with configurable strategy (rebase, merge, ff-only)
- **Obsidian detection** — defers syncing while Obsidian is open
- **System service** — install as launchd (macOS) or systemd (Linux) service
- **Conflict handling** — stops on merge conflicts for manual resolution

## Installation

```bash
# With uv (recommended)
uv tool install obsidian-sync

# With pipx
pipx install obsidian-sync
```

Requires Python 3.11+ and `git` on your PATH.

## Quick start

```bash
# Create a config file
obsidian-sync config --init

# Run a single sync cycle
obsidian-sync sync

# Start the daemon
obsidian-sync start --daemon
```

See [Getting Started](getting-started.md) for a full walkthrough.
