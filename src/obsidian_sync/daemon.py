"""Sync daemon with loop, lock file, signal handling, and Obsidian detection."""

import logging
import os
import platform
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from obsidian_sync.config import SyncConfig, expand_paths
from obsidian_sync.git_ops import (
    GitError,
    PullConflictError,
    PushError,
    add_all,
    commit,
    get_changed_files,
    is_ahead,
    is_dirty,
    pull,
    push,
)
from obsidian_sync.template import CommitContext, render_commit_message

logger = logging.getLogger("obsidian-sync")

OBSIDIAN_PROCESS_NAME_MACOS = "Obsidian"
OBSIDIAN_PROCESS_NAME_LINUX = "obsidian"


@dataclass
class SyncResult:
    """Result of a single sync cycle."""

    synced: bool
    files_changed: int
    message: str
    deferred: bool = False
    error: str | None = None


class LockError(Exception):
    """Raised when the daemon lock cannot be acquired."""


class SyncDaemon:
    """Headless git sync daemon for Obsidian vaults."""

    def __init__(self, config: SyncConfig) -> None:
        self.config = expand_paths(config)
        self._running = False
        self._lock_acquired = False

    def run(self) -> None:
        """Run the sync loop until stopped by signal."""
        self._setup_signals()
        self._acquire_lock()
        self._running = True
        logger.info(
            "Daemon started (vault=%s, interval=%ds)",
            self.config.vault_path,
            self.config.sync.interval_seconds,
        )
        try:
            while self._running:
                result = self.sync_cycle()
                is_conflict = (
                    result.error
                    and isinstance(result.error, str)
                    and "conflict" in result.error.lower()
                )
                if is_conflict:
                    logger.error("Conflict detected, stopping daemon: %s", result.error)
                    sys.exit(1)
                logger.info("Next sync in %d seconds", self.config.sync.interval_seconds)
                self._sleep(self.config.sync.interval_seconds)
        finally:
            self._release_lock()
            logger.info("Daemon stopped")

    def run_once(self) -> SyncResult:
        """Run a single sync cycle, then return."""
        return self.sync_cycle()

    def sync_cycle(self) -> SyncResult:
        """Execute one commit-pull-push cycle.

        Commits local changes before pulling so that ``git pull --rebase``
        can cleanly rebase the local commit on top of remote changes.
        Without committing first, pull fails with "cannot pull with rebase:
        You have unstaged changes" when dirty files overlap with remote.
        """
        vault = Path(self.config.vault_path)
        if not vault.exists():
            msg = f"Vault path does not exist: {vault}"
            logger.error(msg)
            return SyncResult(synced=False, files_changed=0, message=msg, error=msg)

        if self._is_obsidian_running():
            msg = "Deferring to Obsidian (app is running)"
            logger.info(msg)
            return SyncResult(synced=False, files_changed=0, message=msg, deferred=True)

        # Phase 1: Commit local changes (if any)
        committed = False
        changed_files: list[str] = []
        if is_dirty(vault):
            changed_files = get_changed_files(vault)
            add_all(vault)

            context = CommitContext(
                changed_files=changed_files,
                date_format=self.config.commit.date_format,
            )
            commit_msg = render_commit_message(self.config.commit.template, context)

            body = None
            if self.config.commit.list_files_in_body and changed_files:
                body = "\n".join(changed_files)

            commit(vault, commit_msg, body=body)
            logger.info("Committed: %s", commit_msg)
            committed = True

        # Phase 2: Pull remote changes (rebase replays local commit on top)
        try:
            pull_result = pull(
                vault,
                self.config.sync.remote,
                self.config.sync.branch,
                self.config.sync.pull_strategy,
            )
            logger.info("Pull: %s", pull_result.message)
        except PullConflictError as e:
            msg = f"Pull conflict: {e}"
            logger.error(msg)
            return SyncResult(synced=False, files_changed=0, message=msg, error=msg)
        except GitError as e:
            msg = f"Pull failed (will retry): {e}"
            logger.warning(msg)
            return SyncResult(synced=False, files_changed=0, message=msg, error=msg)

        # Phase 3: Push if local is ahead of remote (covers both fresh commits
        # and previously-committed-but-not-pushed changes from failed pulls)
        needs_push = committed or is_ahead(
            vault, self.config.sync.remote, self.config.sync.branch
        )
        if not needs_push:
            msg = "Working tree clean, nothing to sync"
            logger.info(msg)
            return SyncResult(synced=True, files_changed=0, message=msg)

        try:
            push(vault, self.config.sync.remote, self.config.sync.branch)
            logger.info("Pushed to %s/%s", self.config.sync.remote, self.config.sync.branch)
        except PushError as e:
            msg = f"Push failed: {e}"
            logger.error(msg)
            return SyncResult(
                synced=False, files_changed=len(changed_files), message=msg, error=msg
            )

        msg = f"Synced {len(changed_files)} file(s)"
        logger.info(msg)
        return SyncResult(synced=True, files_changed=len(changed_files), message=msg)

    def _is_obsidian_running(self) -> bool:
        """Check if Obsidian is currently running."""
        if platform.system() == "Darwin":
            name = OBSIDIAN_PROCESS_NAME_MACOS
        else:
            name = OBSIDIAN_PROCESS_NAME_LINUX
        try:
            result = subprocess.run(
                ["pgrep", "-x", name],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _acquire_lock(self) -> None:
        """Acquire the PID-based lock file. Raises LockError if already held."""
        lock_path = Path(self.config.lock_path)
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        if lock_path.exists():
            try:
                existing_pid = int(lock_path.read_text().strip())
                if _is_pid_alive(existing_pid):
                    raise LockError(f"Another daemon is running (PID {existing_pid})")
                logger.warning("Removing stale lock file (PID %d no longer running)", existing_pid)
            except (ValueError, OSError):
                logger.warning("Removing invalid lock file")

        lock_path.write_text(str(os.getpid()))
        self._lock_acquired = True

    def _release_lock(self) -> None:
        """Release the lock file if we hold it."""
        if not self._lock_acquired:
            return
        lock_path = Path(self.config.lock_path)
        try:
            if lock_path.exists():
                stored_pid = int(lock_path.read_text().strip())
                if stored_pid == os.getpid():
                    lock_path.unlink()
        except (ValueError, OSError) as e:
            logger.warning("Error releasing lock: %s", e)
        self._lock_acquired = False

    def _setup_signals(self) -> None:
        """Register signal handlers for graceful shutdown."""
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum: int, _frame: object) -> None:
        """Handle shutdown signals gracefully."""
        sig_name = signal.Signals(signum).name
        logger.info("Received %s, shutting down after current cycle", sig_name)
        self._running = False

    def _sleep(self, seconds: int) -> None:
        """Sleep in short intervals to allow signal handling."""
        end_time = time.monotonic() + seconds
        while self._running and time.monotonic() < end_time:
            time.sleep(min(1.0, end_time - time.monotonic()))

    def stop(self) -> bool:
        """Stop a running daemon by reading PID from lock file and sending SIGTERM."""
        lock_path = Path(self.config.lock_path)
        if not lock_path.exists():
            return False
        try:
            pid = int(lock_path.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            return True
        except (ValueError, OSError, ProcessLookupError):
            return False


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def setup_logging(log_path: str, verbose: bool = False) -> None:
    """Configure logging for the daemon."""
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [logging.FileHandler(log_file)]
    if verbose:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


def daemonize() -> None:
    """Fork the process and detach from terminal (Unix double-fork)."""
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    os.setsid()
    pid = os.fork()
    if pid > 0:
        sys.exit(0)
    sys.stdin.close()
