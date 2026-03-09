"""E2E tests that run the real obsidian-sync CLI against a test git repo.

Uses Click's CliRunner for in-process invocation so we can patch the
Obsidian-running check (which would otherwise defer the sync).
"""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from obsidian_sync.cli import main

pytestmark = pytest.mark.e2e


@pytest.fixture
def sync_env(tmp_path):
    """Set up a bare remote + cloned vault for e2e testing."""
    # Create bare "remote" repo with explicit main branch
    remote = tmp_path / "remote.git"
    remote.mkdir()
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(remote)],
        check=True,
        capture_output=True,
    )

    # Clone as "vault"
    vault = tmp_path / "vault"
    subprocess.run(["git", "clone", str(remote), str(vault)], check=True, capture_output=True)

    # Configure git user and disable hooks in the clone (global hooks like
    # branch-protection pre-commit would block test commits otherwise)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=vault,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=vault,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "core.hooksPath", "/dev/null"],
        cwd=vault,
        check=True,
        capture_output=True,
    )

    # Create initial commit so we have a branch
    (vault / "README.md").write_text("# Test Vault\n")
    subprocess.run(["git", "add", "."], cwd=vault, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=vault, check=True, capture_output=True)
    subprocess.run(["git", "push"], cwd=vault, check=True, capture_output=True)

    # Write obsidian-sync config using the actual nested schema
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config = {
        "vault_path": str(vault),
        "sync": {
            "interval_seconds": 5,
            "pull_strategy": "rebase",
            "remote": "origin",
            "branch": "main",
        },
        "commit": {
            "template": "Auto-sync [host={{hostname}}] [files={{numFiles}}]",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "list_files_in_body": True,
        },
        "log": {
            "path": str(tmp_path / "sync.log"),
            "max_size_mb": 10,
        },
        "lock_path": str(tmp_path / "daemon.lock"),
    }
    config_path = config_dir / "config.yaml"
    config_path.write_text(yaml.dump(config, default_flow_style=False))

    return {
        "remote": remote,
        "vault": vault,
        "config_dir": config_dir,
        "config_path": config_path,
        "tmp_path": tmp_path,
    }


def _invoke_sync(config_path: Path) -> object:
    """Invoke `obsidian-sync --config <path> sync` in-process via CliRunner.

    Patches the Obsidian-running check to always return False so the sync
    doesn't defer.
    """
    runner = CliRunner()
    with patch("obsidian_sync.daemon.SyncDaemon._is_obsidian_running", return_value=False):
        return runner.invoke(main, ["--config", str(config_path), "sync"])


def _clone_other_device(remote: Path, tmp_path: Path) -> Path:
    """Clone remote to simulate another device pushing changes."""
    other = tmp_path / "other-device"
    subprocess.run(["git", "clone", str(remote), str(other)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "other@test.com"],
        cwd=other,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Other"],
        cwd=other,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "core.hooksPath", "/dev/null"],
        cwd=other,
        check=True,
        capture_output=True,
    )
    return other


class TestSyncE2E:
    """Test the `obsidian-sync sync` command end-to-end."""

    def test_sync_commits_and_pushes_dirty_vault(self, sync_env):
        """Dirty vault -> sync -> commit appears in remote."""
        vault = sync_env["vault"]
        remote = sync_env["remote"]
        config_path = sync_env["config_path"]

        # Create a new file (dirty the vault)
        (vault / "New Note.md").write_text("# New Note\nSome content.\n")

        result = _invoke_sync(config_path)
        assert result.exit_code == 0, f"sync failed: {result.output}"

        # Verify commit exists in vault
        log = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=vault,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Auto-sync" in log.stdout

        # Verify pushed to remote
        remote_log = subprocess.run(
            ["git", "log", "--oneline", "-1", "main"],
            cwd=remote,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Auto-sync" in remote_log.stdout

    def test_sync_clean_vault_is_noop(self, sync_env):
        """Clean vault -> sync -> no new commit."""
        vault = sync_env["vault"]
        config_path = sync_env["config_path"]

        # Get current HEAD
        before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=vault,
            capture_output=True,
            text=True,
            check=True,
        )

        result = _invoke_sync(config_path)
        assert result.exit_code == 0, f"sync failed: {result.output}"

        # HEAD should be unchanged
        after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=vault,
            capture_output=True,
            text=True,
            check=True,
        )
        assert before.stdout == after.stdout

    def test_sync_pulls_remote_changes(self, sync_env):
        """Remote has new commits -> sync pulls them."""
        vault = sync_env["vault"]
        remote = sync_env["remote"]
        config_path = sync_env["config_path"]
        tmp_path = sync_env["tmp_path"]

        # Simulate another device pushing to remote
        other = _clone_other_device(remote, tmp_path)
        (other / "Remote Note.md").write_text("# From other device\n")
        subprocess.run(["git", "add", "."], cwd=other, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "from other device"],
            cwd=other,
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)

        result = _invoke_sync(config_path)
        assert result.exit_code == 0, f"sync failed: {result.output}"

        # Verify the remote file is now in our vault
        assert (vault / "Remote Note.md").exists()

    def test_sync_handles_concurrent_changes(self, sync_env):
        """Local dirty + remote changes -> sync pulls then commits."""
        vault = sync_env["vault"]
        remote = sync_env["remote"]
        config_path = sync_env["config_path"]
        tmp_path = sync_env["tmp_path"]

        # Push from "other device"
        other = _clone_other_device(remote, tmp_path)
        (other / "Other Note.md").write_text("# Other\n")
        subprocess.run(["git", "add", "."], cwd=other, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "other change"],
            cwd=other,
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)

        # Local change (non-conflicting)
        (vault / "Local Note.md").write_text("# Local\n")

        result = _invoke_sync(config_path)
        assert result.exit_code == 0, f"sync failed: {result.output}"

        # Both files should exist
        assert (vault / "Other Note.md").exists()
        assert (vault / "Local Note.md").exists()

        # Remote should have both
        remote_log = subprocess.run(
            ["git", "log", "--oneline", "-5", "main"],
            cwd=remote,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Auto-sync" in remote_log.stdout
