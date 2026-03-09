"""Shared test fixtures for obsidian-sync."""

import pytest
import yaml

from obsidian_sync.config import SyncConfig


@pytest.fixture
def tmp_config_dir(tmp_path):
    """Create a temporary directory for config files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_config_yaml(tmp_config_dir):
    """Write a sample config.yaml and return its path."""
    config_data = {
        "vault_path": "/tmp/test-vault",
        "sync": {
            "interval_seconds": 600,
            "pull_strategy": "merge",
            "remote": "upstream",
            "branch": "develop",
        },
        "commit": {
            "template": "{{date}} — sync [{{numFiles}} files]",
            "date_format": "%Y-%m-%d",
            "list_files_in_body": False,
        },
        "log": {
            "path": "/tmp/test-sync.log",
            "max_size_mb": 5,
        },
        "lock_path": "/tmp/test-daemon.lock",
    }
    config_path = tmp_config_dir / "config.yaml"
    config_path.write_text(yaml.dump(config_data, default_flow_style=False))
    return config_path


@pytest.fixture
def default_config():
    """Return a SyncConfig with all defaults."""
    return SyncConfig()
