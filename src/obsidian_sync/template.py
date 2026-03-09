"""Commit message template rendering with variable substitution."""

import socket
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath

MAX_FILES_IN_MESSAGE = 5


@dataclass
class CommitContext:
    """Context data for rendering a commit message template."""

    changed_files: list[str] = field(default_factory=list)
    date_format: str = "%Y-%m-%d %H:%M:%S"
    hostname: str = ""


def _format_file_list(files: list[str]) -> str:
    """Format a list of file paths as comma-separated basenames, truncated."""
    basenames = [PurePosixPath(f).name for f in files]
    if len(basenames) <= MAX_FILES_IN_MESSAGE:
        return ", ".join(basenames)
    truncated = basenames[:MAX_FILES_IN_MESSAGE]
    return ", ".join(truncated) + ", ..."


def render_commit_message(template: str, context: CommitContext) -> str:
    """Render a commit message template with the given context.

    Supported variables: {{date}}, {{hostname}}, {{numFiles}}, {{files}}
    """
    hostname = context.hostname if context.hostname else socket.gethostname()
    date_str = datetime.now().strftime(context.date_format)
    num_files = str(len(context.changed_files))
    file_list = _format_file_list(context.changed_files)

    result = template
    result = result.replace("{{date}}", date_str)
    result = result.replace("{{hostname}}", hostname)
    result = result.replace("{{numFiles}}", num_files)
    result = result.replace("{{files}}", file_list)
    return result
