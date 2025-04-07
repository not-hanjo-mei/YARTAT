"""Internationalization (i18n) Module

This module is responsible for managing the internationalization and localization of the application, supporting multilingual interface display.
"""

import os
import json
from typing import Dict, Optional
from .config import TARGET_LANG, DEBUG

# Translation cache
_translations: Dict[str, Dict[str, str]] = {}

_current_language = TARGET_LANG
_default_language = "en-US"

def load_translations(language: str) -> bool:
    """Load translation file for the specified language
    
    Args:
        language: Language code, such as 'en-US', 'zh-CN'
        
    Returns:
        bool: Whether the loading was successful
    """
    global _translations
    
    # If this language has already been loaded, return success directly
    if language in _translations:
        return True
    
    # Build translation file path
    translations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'translations')
    translation_file = os.path.join(translations_dir, f"{language}.json")
    
    try:
        # Ensure translation directory exists
        if not os.path.exists(translations_dir):
            os.makedirs(translations_dir)
            
        # Try to load translation file
        if os.path.exists(translation_file):
            with open(translation_file, 'r', encoding='utf-8') as f:
                _translations[language] = json.load(f)
            return True
        else:
            if DEBUG:
                print(i18n_string("i18n.translation_file_not_exist").format(translation_file))
            return False
    except Exception as e:
        if DEBUG:
            # Cannot use i18n_string function directly here, as it may cause circular reference
            # Use new key that has been added to the translation file
            print(f"i18n.load_translation_failed: {e}")
        return False

def set_language(language: str) -> bool:
    """Set the currently used language
    
    Args:
        language: Language code, such as 'en-US'
        
    Returns:
        bool: Whether the setting was successful
    """
    global _current_language, _translations
    
    # If switching to a different language, clear translation cache to ensure reloading
    if language != _current_language:
        # Keep translations of current language for fallback if loading fails
        current_translations = _translations.get(_current_language, {})
        # Clear translation cache for other languages
        _translations = {}
        if _current_language in _translations:
            _translations[_current_language] = current_translations
    
    # Try to load language file
    if load_translations(language):
        _current_language = language
        return True
    
    # If loading fails and it's not the default language, try to load the default language
    if language != _default_language:
        if load_translations(_default_language):
            _current_language = _default_language
            return True
    
    return False

def get_text(key: str, default: Optional[str] = None) -> str:
    """Get translation text for the specified key
    
    Args:
        key: Translation key, such as 'app.title'
        default: Default value to return when translation doesn't exist
        
    Returns:
        str: Translated text or default value
    """
    global _translations, _current_language, _default_language
    
    # Ensure current language is loaded
    if _current_language not in _translations:
        load_translations(_current_language)
    
    # Try to get translation from current language
    if _current_language in _translations and key in _translations[_current_language]:
        return _translations[_current_language][key]
    
    # Try to get translation from default language
    if _default_language in _translations and key in _translations[_default_language]:
        return _translations[_default_language][key]
    
    # If not found in either, return default value or key name
    return default if default is not None else key

# Load current language when initializing the module
def initialize():
    """Initialize i18n module, load translation for current language"""
    set_language(TARGET_LANG)

def i18n_string(key: str, default: Optional[str] = None) -> str:
    """Get translation text for the specified key
    
    Args:
        key: Translation key, such as 'connection.established'
        default: Default value when translation doesn't exist
        
    Returns:
        str: Translated text
    """
    global _current_language, _default_language
    
    # Ensure translation for current language is loaded
    if _current_language not in _translations and not load_translations(_current_language):
        # If current language loading fails, try to load default language
        if _default_language not in _translations and not load_translations(_default_language):
            # If default language also fails to load, return key name or default value directly
            if DEBUG:
                # Cannot use i18n_string function here because it's in the initialization process
                print(f"i18n.warning_no_translation_files: {key}")
            return default if default is not None else key
    
    # Use translation from current language or default language
    translations = _translations.get(_current_language) or _translations.get(_default_language, {})
    
    # Handle nested keys, such as 'connection.established'
    parts = key.split('.')
    value = translations
    
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            # If translation not found, return default value or key name
            if DEBUG:
                # Use hardcoded message here, as we might be looking for a non-existent translation key
                print(f"i18n.warning_translation_key_not_found: {key}")
            return default if default is not None else key
    
    # Ensure final value is a string
    if not isinstance(value, str):
        if DEBUG:
            # Use hardcoded message ID here, as we might be handling incorrect translation value type
            print(f"i18n.warning_translation_not_string: {key} -> {value}")
        return default if default is not None else key
        
    return value

# Initialize module
initialize()