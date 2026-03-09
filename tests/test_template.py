"""Tests for obsidian_sync.template module."""

import socket
from datetime import datetime
from unittest.mock import patch

from obsidian_sync.template import MAX_FILES_IN_MESSAGE, CommitContext, render_commit_message

FULL_TEMPLATE = (
    "{{date}} — Auto-sync completed [host={{hostname}}] [files={{numFiles}}] [changed={{files}}]"
)


class TestRenderBasic:
    def test_render_basic(self):
        context = CommitContext(
            changed_files=["notes/todo.md", "journal/2024-01.md", "readme.md"],
            hostname="myhost",
        )
        with patch("obsidian_sync.template.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 15, 10, 30, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = render_commit_message(FULL_TEMPLATE, context)
        assert "2024-01-15 10:30:00" in result
        assert "host=myhost" in result
        assert "files=3" in result
        assert "todo.md" in result
        assert "2024-01.md" in result
        assert "readme.md" in result


class TestRenderSingleFile:
    def test_render_single_file(self):
        context = CommitContext(
            changed_files=["notes/single.md"],
            hostname="host1",
        )
        with patch("obsidian_sync.template.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 6, 1, 12, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = render_commit_message(FULL_TEMPLATE, context)
        assert "files=1" in result
        assert "single.md" in result


class TestRenderNoFiles:
    def test_render_no_files(self):
        context = CommitContext(changed_files=[], hostname="host1")
        with patch("obsidian_sync.template.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 6, 1, 12, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = render_commit_message(FULL_TEMPLATE, context)
        assert "files=0" in result


class TestRenderManyFilesTruncated:
    def test_render_many_files_truncated(self):
        files = [f"dir/file{i}.md" for i in range(8)]
        context = CommitContext(changed_files=files, hostname="host1")
        with patch("obsidian_sync.template.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 6, 1, 12, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = render_commit_message(FULL_TEMPLATE, context)
        assert "files=8" in result
        # First MAX_FILES_IN_MESSAGE files should be present
        for i in range(MAX_FILES_IN_MESSAGE):
            assert f"file{i}.md" in result
        # Files beyond the limit should not appear individually
        assert "file5.md" not in result
        assert "..." in result


class TestRenderCustomDateFormat:
    def test_render_custom_date_format(self):
        context = CommitContext(
            changed_files=["a.md"],
            date_format="%d/%m/%Y",
            hostname="host1",
        )
        with patch("obsidian_sync.template.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 3, 15, 9, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = render_commit_message(FULL_TEMPLATE, context)
        assert "15/03/2024" in result


class TestRenderHostname:
    def test_render_hostname(self):
        context = CommitContext(
            changed_files=["a.md"],
            hostname="custom-host",
        )
        with patch("obsidian_sync.template.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 0, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = render_commit_message(FULL_TEMPLATE, context)
        assert "host=custom-host" in result

    def test_render_default_hostname(self):
        context = CommitContext(changed_files=["a.md"])
        with patch("obsidian_sync.template.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 0, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = render_commit_message(FULL_TEMPLATE, context)
        expected_hostname = socket.gethostname()
        assert f"host={expected_hostname}" in result
