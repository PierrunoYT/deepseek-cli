"""Persistence utilities for DeepSeek CLI"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


def _xdg_config_home() -> Path:
    """Return $XDG_CONFIG_HOME if set, otherwise ~/.config (XDG spec default)."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    return Path(xdg) if xdg else Path.home() / ".config"


def _xdg_data_home() -> Path:
    """Return $XDG_DATA_HOME if set, otherwise ~/.local/share (XDG spec default)."""
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    return Path(xdg) if xdg else Path.home() / ".local" / "share"


def _resolve_dirs() -> tuple:
    """Resolve config and data directories with XDG support and legacy fallback.

    Priority order:
      1. If the legacy ~/.deepseek-cli directory exists, keep using it for
         both config and data (no disruption to existing users).
      2. Otherwise use XDG Base Directory locations:
         - config/settings  → $XDG_CONFIG_HOME/deepseek-cli
         - history/data     → $XDG_DATA_HOME/deepseek-cli

    Returns:
        (config_dir, data_dir) as Path objects.
    """
    legacy = Path.home() / ".deepseek-cli"
    if legacy.is_dir():
        return legacy, legacy
    if legacy.exists():
        # Path exists but is not a directory (e.g. a plain file); using it
        # would cause mkdir to fail at startup, so fall back to XDG paths.
        import warnings
        warnings.warn(
            f"{legacy} exists but is not a directory; "
            "falling back to XDG Base Directory paths.",
            UserWarning,
            stacklevel=2,
        )

    config_dir = _xdg_config_home() / "deepseek-cli"
    data_dir = _xdg_data_home() / "deepseek-cli"
    return config_dir, data_dir


def _mkdir_private(path: Path) -> None:
    """Create *path* (and parents) restricted to the owner where supported.

    ``mode`` is ignored by mkdir on Windows and is masked by the process umask
    on POSIX, so an explicit chmod follows for an existing or freshly created
    directory. Permission systems that don't implement chmod (Windows) raise
    nothing useful here, so failures are non-fatal.
    """
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(path, 0o700)
    except (OSError, NotImplementedError):
        pass


def _open_private(path: Path, mode: str):
    """Open *path* for writing with owner-only permissions from the start.

    The file is created via ``os.open`` with 0o600 so there is no window in
    which the transcript exists world-readable; chmod afterwards also fixes
    files created by earlier versions of the CLI.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.chmod(path, 0o600)
    except (OSError, NotImplementedError):
        pass
    return os.fdopen(fd, mode, encoding="utf-8")


class PersistenceManager:
    """Handles saving and loading chat history and settings"""

    def __init__(self, config_dir: Optional[str] = None) -> None:
        """Initialize persistence manager

        Args:
            config_dir: Directory to store ALL persistence files. When provided
                this path is used for both config and data (legacy/test behaviour).
                When omitted, XDG Base Directory locations are used unless the
                legacy ~/.deepseek-cli directory already exists (backward compat).
        """
        if config_dir is not None:
            self.config_dir = Path(config_dir)
            self.data_dir = self.config_dir
        else:
            self.config_dir, self.data_dir = _resolve_dirs()

        # Ensure directories exist, owner-only. These hold the full transcript
        # (including the text of any attached files), so they must not be
        # readable by other local users.
        _mkdir_private(self.config_dir)
        if self.data_dir != self.config_dir:
            _mkdir_private(self.data_dir)

        self.history_file = self.data_dir / "chat_history.json"
        self.settings_file = self.config_dir / "settings.json"

    def save_history(self, messages: List[Dict[str, Any]]) -> bool:
        """Save chat history to disk

        Args:
            messages: List of message dictionaries

        Returns:
            True if successful, False otherwise
        """
        try:
            history_data = {
                "messages": messages,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }

            with _open_private(self.history_file, "w") as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Warning: Failed to save chat history: {e}")
            return False

    def load_history(self) -> Optional[List[Dict[str, Any]]]:
        """Load chat history from disk

        Returns:
            List of message dictionaries if successful, None otherwise
        """
        try:
            if not self.history_file.exists():
                return None

            with open(self.history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            # Validate structure
            if not isinstance(history_data, dict) or "messages" not in history_data:
                return None

            messages = history_data["messages"]
            if not isinstance(messages, list):
                return None

            return messages
        except Exception as e:
            print(f"Warning: Failed to load chat history: {e}")
            return None

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to disk

        Args:
            settings: Settings dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            settings_data = {
                "settings": settings,
                "last_updated": datetime.now().isoformat(),
                "version": "1.0",
            }

            with _open_private(self.settings_file, "w") as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Warning: Failed to save settings: {e}")
            return False

    def load_settings(self) -> Optional[Dict[str, Any]]:
        """Load settings from disk

        Returns:
            Settings dictionary if successful, None otherwise
        """
        try:
            if not self.settings_file.exists():
                return None

            with open(self.settings_file, "r", encoding="utf-8") as f:
                settings_data = json.load(f)

            # Validate structure
            if not isinstance(settings_data, dict) or "settings" not in settings_data:
                return None

            return settings_data["settings"]
        except Exception as e:
            print(f"Warning: Failed to load settings: {e}")
            return None

    def get_config_dir(self) -> Path:
        """Get the configuration directory path"""
        return self.config_dir

    def get_data_dir(self) -> Path:
        """Get the data directory path (may differ from config dir on XDG systems)"""
        return self.data_dir

    def clear_history(self) -> bool:
        """Clear chat history from disk

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.history_file.exists():
                self.history_file.unlink()
            return True
        except Exception as e:
            print(f"Warning: Failed to clear chat history: {e}")
            return False

    def clear_settings(self) -> bool:
        """Clear settings from disk

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.settings_file.exists():
                self.settings_file.unlink()
            return True
        except Exception as e:
            print(f"Warning: Failed to clear settings: {e}")
            return False
