"""File attachment handler for DeepSeek CLI.

The DeepSeek chat-completions API doesn't have a native file-upload endpoint
(unlike the official DeepSeek app, which extracts text from uploaded files
and embeds it in the prompt). This module replicates that behaviour: it lets
the user attach one or more local text files whose contents are then folded
into the next outgoing user message as additional context.

Two ways to attach files are exposed:

  * ``FileHandler.attach(pattern)`` — programmatic / command-line use.
    Accepts a literal path, a ``~``-prefixed path, or a glob pattern
    (``src/*.py``, ``**/*.md`` …).

  * ``pick_files()`` — interactive picker built on prompt_toolkit's
    ``PathCompleter``. Provides tab completion and supports multiple
    space-separated paths/globs in a single line.
"""

from __future__ import annotations

import glob
import os
import shlex
from pathlib import Path
from typing import Dict, List, Tuple

from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Limits — generous but bounded so a stray ``**/*`` doesn't blow up context.
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 1 * 1024 * 1024        # 1 MiB per file
MAX_TOTAL_SIZE = 4 * 1024 * 1024       # 4 MiB cumulative
MAX_FILES = 20

# Extensions we refuse to read as text. UTF-8 decoding would catch most of
# these too, but rejecting up-front gives a clearer error.
BINARY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".obj", ".o", ".a", ".lib",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".tif", ".tiff", ".webp",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac", ".ogg", ".m4a",
    ".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".otf",
}


class FileHandler:
    """Manages the list of files attached for the next user message."""

    def __init__(self) -> None:
        # Each entry: {"path": absolute_path, "content": text, "size": bytes}
        self.attached_files: List[Dict[str, object]] = []

    # ------------------------------------------------------------------
    # Bookkeeping
    # ------------------------------------------------------------------
    def total_size(self) -> int:
        return sum(int(f.get("size", 0)) for f in self.attached_files)

    def list_attachments(self) -> List[Dict[str, object]]:
        return list(self.attached_files)

    def clear(self) -> None:
        self.attached_files = []

    def has_attachments(self) -> bool:
        return bool(self.attached_files)

    def remove(self, path_or_index: str) -> bool:
        """Remove an attachment by 0-based index or by path."""
        try:
            idx = int(path_or_index)
            if 0 <= idx < len(self.attached_files):
                self.attached_files.pop(idx)
                return True
            return False
        except ValueError:
            pass

        target = os.path.abspath(os.path.expanduser(path_or_index))
        for i, f in enumerate(self.attached_files):
            if f["path"] == target:
                self.attached_files.pop(i)
                return True
        return False

    # ------------------------------------------------------------------
    # Attaching
    # ------------------------------------------------------------------
    def attach(self, path_pattern: str) -> Tuple[List[str], List[str]]:
        """Attach files matching *path_pattern* (literal path or glob).

        Returns:
            ``(attached_paths, errors)`` — both lists may be empty.
        """
        attached: List[str] = []
        errors: List[str] = []

        expanded = os.path.expanduser(path_pattern)
        matches = glob.glob(expanded, recursive=True)

        # Fall back to a literal path if glob yielded nothing but the path
        # exists (handles paths containing characters glob treats literally).
        if not matches and os.path.exists(expanded):
            matches = [expanded]

        if not matches:
            errors.append(f"No files matching: {path_pattern}")
            return attached, errors

        for match in sorted(matches):
            if os.path.isdir(match):
                errors.append(f"Skipping directory: {match}")
                continue

            abs_path = os.path.abspath(match)

            if any(f["path"] == abs_path for f in self.attached_files):
                errors.append(f"Already attached: {abs_path}")
                continue

            if len(self.attached_files) >= MAX_FILES:
                errors.append(f"Maximum of {MAX_FILES} attached files reached")
                break

            ext = Path(abs_path).suffix.lower()
            if ext in BINARY_EXTENSIONS:
                errors.append(f"Binary file rejected: {abs_path}")
                continue

            try:
                size = os.path.getsize(abs_path)
            except OSError as exc:
                errors.append(f"Cannot stat {abs_path}: {exc}")
                continue

            if size > MAX_FILE_SIZE:
                errors.append(
                    f"File too large ({size} bytes > {MAX_FILE_SIZE}): {abs_path}"
                )
                continue

            if self.total_size() + size > MAX_TOTAL_SIZE:
                errors.append(
                    f"Total attachment size ({MAX_TOTAL_SIZE} bytes) would be "
                    f"exceeded; skipping {abs_path}"
                )
                continue

            try:
                with open(abs_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except UnicodeDecodeError:
                errors.append(f"Not a UTF-8 text file: {abs_path}")
                continue
            except OSError as exc:
                errors.append(f"Cannot read {abs_path}: {exc}")
                continue

            self.attached_files.append(
                {"path": abs_path, "content": content, "size": size}
            )
            attached.append(abs_path)

        return attached, errors

    # ------------------------------------------------------------------
    # Message formatting
    # ------------------------------------------------------------------
    def format_for_message(self, user_text: str) -> str:
        """Inject attached file contents into *user_text*.

        If no files are attached, *user_text* is returned unchanged.
        """
        if not self.attached_files:
            return user_text

        parts: List[str] = [
            "The following file(s) are attached for context:",
            "",
        ]
        for f in self.attached_files:
            parts.append(f"--- File: {f['path']} ---")
            parts.append(str(f["content"]))
            parts.append(f"--- End of file: {f['path']} ---")
            parts.append("")

        if user_text.strip():
            parts.append("User message:")
            parts.append(user_text)
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Interactive picker
# ---------------------------------------------------------------------------
def pick_files() -> List[str]:
    """Prompt the user for one or more paths/globs with tab completion.

    Returns:
        A list of raw path/glob strings the user entered (possibly empty if
        they cancelled or submitted an empty line). Each entry is later fed
        through :meth:`FileHandler.attach`, so globs and ``~`` are honoured.
    """
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import PathCompleter
    except ImportError:
        console.print(
            "[red]prompt_toolkit is required for the interactive picker. "
            "Install with: pip install prompt_toolkit[/red]"
        )
        return []

    completer = PathCompleter(expanduser=True)
    console.print("[cyan]File picker[/cyan]")
    console.print("[dim]  - Tab completes paths; Enter submits.[/dim]")
    console.print(
        "[dim]  - Multiple paths can be space-separated; quote paths with spaces.[/dim]"
    )
    console.print("[dim]  - Globs work: src/*.py, **/*.md (recursive).[/dim]")
    console.print("[dim]  - Empty line / Ctrl+C cancels.[/dim]")

    session: PromptSession = PromptSession()
    try:
        text = session.prompt("📁 Select file(s): ", completer=completer)
    except (KeyboardInterrupt, EOFError):
        return []

    text = text.strip()
    if not text:
        return []

    try:
        return shlex.split(text, posix=(os.name != "nt"))
    except ValueError:
        return text.split()
