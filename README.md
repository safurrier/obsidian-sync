# obsidian-sync

Headless git sync daemon that keeps your Obsidian vault backed up to a git remote when the app is closed. Matches the Obsidian Git plugin's strategy (rebase, pull-before-push, hostname-tagged commits) and automatically defers when Obsidian is running to avoid conflicts.

## Installation

```bash
# With uv (recommended)
uv tool install obsidian-sync

# With pipx
pipx install obsidian-sync
```

Requires Python 3.11+ and `git` on your PATH.

## Quick Start

```bash
# Create a config file (interactive)
obsidian-sync config --init

# Run a single sync cycle
obsidian-sync sync

# Start the daemon (foreground)
obsidian-sync start

# Start the daemon (background)
obsidian-sync start --daemon
```

## Commands

| Command | Description |
|---------|-------------|
| `start` | Start the sync loop (`--daemon` to run in background) |
| `stop` | Stop a running daemon |
| `status` | Show daemon status and last log entry |
| `sync` | Run one sync cycle, then exit |
| `config` | Show current config (`--init` to create, `--edit` to open in $EDITOR) |
| `log` | Show recent log entries (`--tail` to follow, `-n` for line count) |
| `install` | Install as a system service (launchd on macOS, systemd on Linux) |
| `uninstall` | Remove the system service |
| `enable` | Enable service to start on login |
| `disable` | Disable service from starting on login |

All commands accept `--config PATH` to use a non-default config file and `--verbose` for debug output.

## Service Setup

### macOS (launchd)

```bash
obsidian-sync install   # copies plist to ~/Library/LaunchAgents/
obsidian-sync enable    # loads the service
```

To remove:

```bash
obsidian-sync disable
obsidian-sync uninstall
```

### Linux (systemd)

```bash
obsidian-sync install   # copies unit to ~/.config/systemd/user/
obsidian-sync enable    # enables and starts the service
```

To remove:

```bash
obsidian-sync disable
obsidian-sync uninstall
```

## Configuration

Config file location: `~/.config/obsidian-sync/config.yaml`

Create one interactively with `obsidian-sync config --init`, or write it manually:

```yaml
vault_path: ~/obsidian-vault
sync:
  interval_seconds: 60
  pull_strategy: rebase    # rebase | merge | ff-only
  remote: origin
  branch: main
commit:
  template: "{{date}} — Auto-sync completed [host={{hostname}}] [files={{numFiles}}] [changed={{files}}]"
  date_format: "%Y-%m-%d %H:%M:%S"
  list_files_in_body: true
log:
  path: ~/.local/state/obsidian-sync/sync.log
  max_size_mb: 10
lock_path: ~/.local/state/obsidian-sync/daemon.lock
```

| Setting | Default | Description |
|---------|---------|-------------|
| `vault_path` | `~/obsidian-vault` | Path to your Obsidian vault git repo |
| `sync.interval_seconds` | `60` | Seconds between sync cycles |
| `sync.pull_strategy` | `rebase` | Git pull strategy (`rebase`, `merge`, or `ff-only`) |
| `sync.remote` | `origin` | Git remote name |
| `sync.branch` | `main` | Git branch name |
| `commit.template` | *(see above)* | Commit message template with `{{date}}`, `{{hostname}}`, `{{numFiles}}`, `{{files}}` variables |
| `commit.date_format` | `%Y-%m-%d %H:%M:%S` | strftime format for `{{date}}` |
| `commit.list_files_in_body` | `true` | Include changed file list in commit body |
| `log.path` | `~/.local/state/obsidian-sync/sync.log` | Log file location |
| `log.max_size_mb` | `10` | Max log file size before rotation |
| `lock_path` | `~/.local/state/obsidian-sync/daemon.lock` | PID lock file location |

## Behavior

- **Auto-commit**: Stages all changes and commits with a timestamped, hostname-tagged message
- **Pull before push**: Pulls with rebase (by default) to keep history linear
- **Obsidian detection**: Automatically defers syncing while Obsidian is open to avoid conflicts with the Obsidian Git plugin
- **Lock file**: Uses a PID lock to prevent duplicate daemons
- **Conflict handling**: Stops the daemon on merge conflicts (manual resolution required)

## License

MIT
