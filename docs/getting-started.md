# Getting Started

## Install

```bash
uv tool install obsidian-sync
```

Or for development:

```bash
git clone https://github.com/safurrier/obsidian-sync.git
cd obsidian-sync
uv sync --all-extras
```

## Create a config

```bash
obsidian-sync config --init
```

This prompts for your vault path and sync interval, then writes `~/.config/obsidian-sync/config.yaml`.

## First sync

Run a one-off sync to verify everything works:

```bash
obsidian-sync sync
```

This stages all changes, commits with a timestamped message, pulls with rebase, and pushes.

## Start the daemon

Foreground (useful for testing):

```bash
obsidian-sync start
```

Background:

```bash
obsidian-sync start --daemon
```

Check status:

```bash
obsidian-sync status
```

## Install as a service

### macOS (launchd)

```bash
obsidian-sync install   # copies plist to ~/Library/LaunchAgents/
obsidian-sync enable    # loads the service
```

### Linux (systemd)

```bash
obsidian-sync install   # copies unit to ~/.config/systemd/user/
obsidian-sync enable    # enables and starts the service
```

The service starts automatically on login and syncs on your configured interval.

To remove:

```bash
obsidian-sync disable
obsidian-sync uninstall
```
