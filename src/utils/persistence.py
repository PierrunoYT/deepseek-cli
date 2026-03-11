"""Persistence utilities for DeepSeek CLI"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class PersistenceManager:
    """Handles saving and loading chat history and settings"""
    
    def __init__(self, config_dir: Optional[str] = None) -> None:
        """Initialize persistence manager
        
        Args:
            config_dir: Directory to store persistence files. Defaults to ~/.deepseek-cli
        """
        if config_dir is None:
            home = Path.home()
            self.config_dir = home / ".deepseek-cli"
        else:
            self.config_dir = Path(config_dir)
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        self.history_file = self.config_dir / "chat_history.json"
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
                "version": "1.0"
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
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
            
            with open(self.history_file, 'r', encoding='utf-8') as f:
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
                "version": "1.0"
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
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
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
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
