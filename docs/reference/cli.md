# CLI Reference

All commands accept `--config PATH` for a non-default config file and `--verbose` for debug output.

## Commands

### `obsidian-sync start`

Start the sync loop.

```bash
obsidian-sync start           # foreground
obsidian-sync start --daemon  # background
```

### `obsidian-sync stop`

Stop a running daemon.

```bash
obsidian-sync stop
```

### `obsidian-sync status`

Show daemon status, config summary, and last log entry.

```bash
obsidian-sync status
```

### `obsidian-sync sync`

Run one sync cycle (stage, commit, pull, push), then exit.

```bash
obsidian-sync sync
```

### `obsidian-sync config`

Show, create, or edit configuration.

```bash
obsidian-sync config          # show current config
obsidian-sync config --init   # create config interactively
obsidian-sync config --edit   # open in $EDITOR
```

### `obsidian-sync log`

Show sync log entries.

```bash
obsidian-sync log             # last 50 lines
obsidian-sync log -n 100      # last 100 lines
obsidian-sync log --tail      # follow log output
```

### `obsidian-sync install`

Install as a system service (launchd on macOS, systemd on Linux).

### `obsidian-sync uninstall`

Remove the system service.

### `obsidian-sync enable`

Enable service to start on login.

### `obsidian-sync disable`

Disable service from starting on login.
