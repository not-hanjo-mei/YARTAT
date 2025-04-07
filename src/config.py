"""Configuration Management Module

This module is responsible for loading and managing application configuration information, including debug switches, performance settings, API keys, etc.
"""

import os
import json
from typing import Any, Dict, Optional

class Config:
    def __init__(self):
        self.config_data: Dict = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration file"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
        except Exception as e:
            # Since we cannot directly import the i18n module (would cause circular import), we use hardcoded messages here
            # This error message will be improved in future versions
            print(f"Load config file error: {e}")
            self.config_data = {}
    
    def get_value(self, key_path: str) -> Optional[Any]:
        """Recursively get configuration value
        
        Args:
            key_path: Configuration key path, such as 'openai.apiKey'
            
        Returns:
            Configuration value or None (if it doesn't exist)
        """
        keys = key_path.split('.')
        current = self.config_data
        
        for key in keys:
            if isinstance(current, dict):
                if key in current:
                    current = current[key]
                else:
                    return None
            else:
                return None
        
        return current.get('value') if isinstance(current, dict) and 'value' in current else current

# Create global configuration instance
config = Config()

# Export commonly used configuration items
DEBUG = config.get_value('debug') or False
MAX_WORKERS = int(config.get_value('performance.maxWorkers') or 1)
TRANSLATION_TIMEOUT = int(config.get_value('performance.translationTimeout') or 30)

MEDIA_ID = config.get_value('reality.mediaId')
MY_VLIVEID = config.get_value('reality.vLiveId')
MY_GID = config.get_value('reality.gid')
MY_AUTH = config.get_value('reality.auth')

OPENAI_API_KEY = config.get_value('openai.apiKey')
OPENAI_API_BASE = config.get_value('openai.apiBase')
OPENAI_MODEL = config.get_value('openai.model')

TRANSLATOR_ENGINE = config.get_value('translation.engine') or "google"
TARGET_LANG = config.get_value('translation.targetLanguage') or "en-US"

PRINT_CONFIG = config.get_value('startup.printConfig') if config.get_value('startup.printConfig') is not None else True