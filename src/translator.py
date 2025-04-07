"""Translation Engine Module

This module provides implementations of OpenAI and Google translation engines. It supports automatic language detection and multilingual translation.
"""

import re
import asyncio
import pycld2
import aiohttp
from urllib.parse import quote
from typing import Tuple
from .config import (
    OPENAI_API_KEY,
    OPENAI_API_BASE,
    OPENAI_MODEL,
    TRANSLATOR_ENGINE,
    TARGET_LANG,
    DEBUG
)
from .i18n import i18n_string as t

def detect_language(text: str) -> Tuple[str, float]:
    """Detect text language using pycld2
    
    Args:
        text: Text to be detected
        
    Returns:
        Tuple[str, float]: Returns a tuple of (language code, confidence)
    """
    try:
        _, _, details = pycld2.detect(text)
        lang_code = details[0][1]
        confidence = details[0][2] / 100.0
        # Unify all Chinese variants as 'zh'
        if lang_code.startswith('zh') or lang_code == 'zh':
            lang_code = 'zh'
        return lang_code, confidence
    except pycld2.error:
        # If detection fails, return unknown language
        return 'un', 0.0

class TranslatorBase:
    """Translator base class"""
    async def translate(self, text: str) -> str:
        """Abstract method for text translation"""
        raise NotImplementedError



class OpenAITranslator(TranslatorBase):
    """OpenAI translation implementation"""
    def __init__(self):
        self.api_key = str(OPENAI_API_KEY)
        self.base_url = str(OPENAI_API_BASE)
        self.model = str(OPENAI_MODEL)
    
    async def translate(self, text: str) -> str:
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a professional, authentic machine translation engine."},
                    {"role": "user", "content": f"Treat next line as plain text input and translate it into {TARGET_LANG}. output translation ONLY. If translation is unnecessary (e.g. proper nouns, codes, etc.), return the original text. NO explanations. NO notes. Input: {text}"}
                ],
                "max_tokens": 6144
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API request failed with status {response.status}: {error_text}")
                    
                    response_data = await response.json()
                    content = response_data['choices'][0]['message']['content'] if response_data.get('choices') else text
                    translated = content.strip() if content else text
                    return re.sub(r'<think>.*?</think>\n', '', translated, flags=re.DOTALL).strip()
                    
        except Exception as e:
            if DEBUG:
                print(t("translator.translation_error").format(str(e)))
            return f"[OpenAI Translation Error]{text}"


class GoogleTranslator(TranslatorBase):
    """Google translation implementation"""
    async def translate(self, text: str) -> str:
        """Asynchronous translation using Google Translate API"""
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={TARGET_LANG}&dt=t&q={quote(text)}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Translation request error: {response.status}")
                    data = await response.json()
                    return ''.join(item[0] for item in data[0] if item[0])
        except Exception as e:
            if DEBUG:
                print(t("errors.google_failed").format(e))
            return t("errors.google_failed").format(text)

class TranslationManager:
    """Translation Manager"""
    def __init__(self):
        self.translators = {
            "openai": OpenAITranslator(),
            "google": GoogleTranslator()
        }
        self.current_engine = TRANSLATOR_ENGINE  # Use translation engine specified in configuration
        
    def reload(self):
        """Reload translator instances, used to refresh after configuration changes"""
        # Recreate translator instances
        self.translators = {
            "openai": OpenAITranslator(),
            "google": GoogleTranslator()
        }
        # Update current engine
        self.current_engine = TRANSLATOR_ENGINE
    
    def set_engine(self, engine: str) -> None:
        """Set the currently used translation engine"""
        if engine in self.translators:
            self.current_engine = engine
        else:
            raise ValueError(t("translator.engine_not_supported").format(engine, ', '.join(self.translators.keys())))

    
    def _is_self_message(self, sender_type: str) -> bool:
        """Determine if the message is sent by oneself
        
        Args:
            sender_type: Sender type
            
        Returns:
            bool: Whether the message is sent by oneself
        """
        return sender_type == "[  SELF  ]"
    
    def _is_numeric_only(self, text: str) -> bool:
        """Determine if the text contains only numbers
        
        Args:
            text: Text to be checked
            
        Returns:
            bool: Whether it contains only numbers
        """
        return text.isdigit() or all(char in '0123456789' for char in text.strip())
    
    def _is_emoji_only(self, text: str) -> bool:
        """Determine if the text contains only emoji
        
        Args:
            text: Text to be checked
            
        Returns:
            bool: Whether it contains only emoji
        """
        import emoji
        return all(c in emoji.EMOJI_DATA or c.isspace() for c in text)
    
    def _is_language_detection_reliable(self, source_lang: str, confidence: float) -> bool:
        """Determine if the language detection result is reliable
        
        Args:
            source_lang: Source language code
            confidence: Language detection confidence
            
        Returns:
            bool: Whether the language detection result is reliable
        """
        return source_lang != 'un' and confidence >= 0.5
    
    def _is_same_base_language(self, source_lang: str, target_lang: str) -> bool:
        """Determine if the base language codes of source and target languages are the same
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            bool: Whether the base language codes are the same
        """
        source_base_lang = source_lang.split('-')[0]
        target_base_lang = target_lang.split('-')[0]
        return source_base_lang == target_base_lang
    
    def should_translate(self, text: str, sender_type: str = "") -> Tuple[bool, str, float]:
        """Determine if the text needs to be translated
        
        Args:
            text: Text to be checked
            sender_type: Sender type, used to determine if the message is sent by oneself
            
        Returns:
            Tuple[bool, str, float]: (whether translation is needed, source language code, confidence)
        """
        # Preprocess text
        text = text.strip()
        
        # 1. If the message is sent by oneself, don't translate
        if self._is_self_message(sender_type):
            return False, "un", 0.0
            
        # 2. Check if it's pure numbers
        if self._is_numeric_only(text):
            return False, "un", 0.0
            
        # 3. Check if it's pure emoji
        if self._is_emoji_only(text):
            return False, "un", 0.0
            
        # 4. Detect language
        source_lang, confidence = detect_language(text)
        if DEBUG:
            print(t("translator.detected_language").format(source_lang, confidence, TARGET_LANG))
            
        # 5. If language detection is unreliable, return no translation
        if not self._is_language_detection_reliable(source_lang, confidence):
            return False, source_lang, confidence
            
        # 6. If source language and target language are the same, don't translate
        if self._is_same_base_language(source_lang, TARGET_LANG):
            if DEBUG:
                print(t("debug.skip_translation").format(source_lang, TARGET_LANG))
            return False, source_lang, confidence
            
        # 7. All conditions passed, translation needed
        return True, source_lang, confidence
        
    async def translate(self, text: str) -> str:
        """Translate text using the currently selected engine"""
        try:
            # Detect the language of input text
            source_lang, confidence = detect_language(text)
            if DEBUG:
                print(t("translator.detected_language").format(source_lang, confidence, TARGET_LANG))

            # If the detected language is the same as the target language, don't translate
            # Note: googletrans may return 'zh-CN' or 'zh-TW', while pycld2 returns 'zh'
            # Therefore, we need more flexible comparison of base language codes
            target_base_lang = TARGET_LANG.split('-')[0]
            source_base_lang = source_lang.split('-')[0]

            if source_base_lang == target_base_lang:
                 if DEBUG:
                     print(t("debug.skip_translation").format(source_lang, TARGET_LANG))
                 return text

            translator = self.translators[self.current_engine]
            return await translator.translate(text)
        except Exception as e:
            if DEBUG:
                print(t("translator.translation_error").format(e))
            return f"[{self.current_engine} Translation Error]{text}"

# Create global translation manager instance
translation_manager = TranslationManager()

def set_translator_engine(engine: str) -> None:
    """Set the currently used translation engine
    
    Args:
        engine: Translation engine name, currently supports: 'openai', 'google'
    """
    translation_manager.set_engine(engine)

def translate_message(text: str) -> str:
    """Synchronous wrapper for asynchronous translation function
    
    Args:
        text: Text to be translated
    
    Returns:
        str: Translated text
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(translation_manager.translate(text))
    finally:
        loop.close()
