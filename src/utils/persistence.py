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
    if legacy.exists():
        return legacy, legacy

    config_dir = _xdg_config_home() / "deepseek-cli"
    data_dir = _xdg_data_home() / "deepseek-cli"
    return config_dir, data_dir


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

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if self.data_dir != self.config_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)

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

            with open(self.history_file, "w", encoding="utf-8") as f:
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

            with open(self.settings_file, "w", encoding="utf-8") as f:
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
