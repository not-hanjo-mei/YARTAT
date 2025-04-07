"""TUI Module

This module provides a text user interface based on the textual library, used for displaying messages and status.
"""

import threading
import queue

from textual.app import App, ComposeResult, Screen
from textual.containers import Container
from textual.widgets import Static, Log, Label, Input
from textual.reactive import reactive
from textual.binding import Binding

import os
import json

# Import necessary config values and the config object itself for more flexibility
from .config import DEBUG, PRINT_CONFIG, TARGET_LANG, TRANSLATOR_ENGINE, OPENAI_MODEL, OPENAI_API_KEY, MEDIA_ID
from .i18n import i18n_string as t
from .message_handler import output_queue

# Global event queue, used to send events from other threads to TUI
tui_event_queue = queue.Queue()

# Global TUI application instance
tui_app = None

class MessageLog(Log):
    """Message log component, used to display chat messages"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = False

class StatusBar(Static):
    """Status bar component, displays connection status and translation engine information"""
    
    status = reactive("Disconnected")
    target_lang = reactive(TARGET_LANG)
    translator_engine = reactive(TRANSLATOR_ENGINE)
    
    def render(self) -> str:
        model_info = f"{t('tui.ai_model')}: {OPENAI_MODEL}" if TRANSLATOR_ENGINE == 'openai' else ""
        line1 = f"{t('tui.status')}: {self.status} | {t('tui.target_lang')}: {self.target_lang}"
        line2 = f"{t('tui.translation_engine')}: {self.translator_engine}"
        if model_info:
            line2 += f" | {model_info}"
        return f"{line1}\n{line2}"

class YARTATApp(App):
    """YARTAT TUI application main class"""
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1;
        grid-rows: 1fr auto;
    }
    
    MessageLog {
        height: 100%;
        border: solid white;
        background: $surface;
        color: white;
        width: 100%;
        text-overflow: fold;
        text-wrap: wrap;
    }
    
    StatusBar {
        height: 2;
        dock: bottom;
        background: $primary-background;
        color: white;
        width: 100%;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", t("tui.quit")),
        Binding("h", "show_help", t("tui.help")),
        Binding("c", "show_config", t("tui.config")),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_log = MessageLog(highlight=False)
        self.status_bar = StatusBar()
        
        # Start event processing thread
        self.event_thread = threading.Thread(target=self._process_events, daemon=True)
        self.event_thread.start()
        
        # Start output processing thread
        self.output_thread = threading.Thread(target=self._process_output, daemon=True)
        self.output_thread.start()

        global tui_app
        tui_app = self
    
    def compose(self) -> ComposeResult:
        """Compose the TUI layout"""
        yield self.message_log
        yield self.status_bar
    
    def on_mount(self) -> None:
        """Called when the app is mounted"""
        # Print configuration if enabled
        if PRINT_CONFIG:
            self.message_log.write(f"YARTAT - Yet Another Reality Translator and Transcriber\n")
            self.message_log.write(f"Target Language: {TARGET_LANG}\n")
            self.message_log.write(f"Translation Engine: {TRANSLATOR_ENGINE}\n")
            if TRANSLATOR_ENGINE == 'openai':
                self.message_log.write(f"OpenAI Model: {OPENAI_MODEL}\n")
            self.message_log.write(f"Media ID: {MEDIA_ID}\n")
            self.message_log.write(f"Debug Mode: {DEBUG}\n\n")
        
        # Set initial status
        self.status_bar.status = "Disconnected"
    
    def action_quit(self) -> None:
        """Quit the application"""
        # Send exit signals to worker threads
        tui_event_queue.put(None)
        output_queue.put(None)
        self.exit()
    
    def action_show_help(self) -> None:
        """Show help information"""
        help_text = """
        YARTAT - Yet Another Reality Translator and Transcriber
        
        Keyboard shortcuts:
        - q: Quit the application
        - h: Show this help information
        - c: Open configuration screen
        """
        self.message_log.write(help_text)
    
    def action_show_config(self) -> None:
        """Show configuration screen"""
        self.push_screen(ConfigScreen())

class ConfigScreen(Screen):
    """Configuration screen"""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", t("tui.back")),
        Binding("ctrl+s", "save_config", t("tui.save")),
    ]
    
    CSS = """
    ConfigScreen {
        layout: grid;
        grid-size: 1;
        grid-rows: 1fr auto;
        background: $surface;
    }
    
    #config-container {
        width: 100%;
        height: 100%;
        overflow-y: auto;
        padding: 1 2;
    }
    
    Label {
        width: 100%;
        height: 1;
        content-align: center middle;
    }
    
    Input {
        width: 100%;
        margin: 1 0;
    }
    
    #footer {
        height: 1;
        dock: bottom;
        background: $primary-background;
        color: white;
        width: 100%;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Compose the configuration screen layout"""
        with Container(id="config-container"):
            yield Label(t("tui.config_title"), id="title")
            
            # Target language configuration
            yield Label("Target Language (e.g. en-US, zh-CN, ja-JP)")
            self.target_lang_input = Input(value=TARGET_LANG, id="target-lang")
            yield self.target_lang_input
            
            # Translation engine configuration
            yield Label("Translation Engine (openai or google)")
            self.translator_engine_input = Input(value=TRANSLATOR_ENGINE, id="translator-engine")
            yield self.translator_engine_input
            
            # OpenAI configuration (only shown if OpenAI is selected)
            if TRANSLATOR_ENGINE == 'openai':
                yield Label("OpenAI Model")
                self.openai_model_input = Input(value=OPENAI_MODEL, id="openai-model")
                yield self.openai_model_input
                
                yield Label("OpenAI API Key")
                self.openai_api_key_input = Input(value=OPENAI_API_KEY or "", id="openai-api-key", password=True)
                yield self.openai_api_key_input
        
        # Footer with save hint
        yield Static(t("tui.save_hint"), id="footer")
    
    def action_save_config(self) -> None:
        """Save configuration and exit the configuration screen"""
        # Get values from inputs
        new_target_lang = self.target_lang_input.value
        new_translator_engine = self.translator_engine_input.value
        
        # Update configuration file
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Update values
            if 'translation' not in config_data:
                config_data['translation'] = {}
            
            config_data['translation']['targetLanguage'] = {'value': new_target_lang}
            config_data['translation']['engine'] = {'value': new_translator_engine}
            
            # Update OpenAI configuration if applicable
            if new_translator_engine == 'openai':
                if hasattr(self, 'openai_model_input') and hasattr(self, 'openai_api_key_input'):
                    new_openai_model = self.openai_model_input.value
                    new_openai_api_key = self.openai_api_key_input.value
                    
                    if 'openai' not in config_data:
                        config_data['openai'] = {}
                    
                    config_data['openai']['model'] = {'value': new_openai_model}
                    if new_openai_api_key:  # Only update API key if provided
                        config_data['openai']['apiKey'] = {'value': new_openai_api_key}
            
            # Write updated configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            
            # Update global variables
            from .config import config
            config.load_config()
            
            # Update i18n language if target language changed
            if new_target_lang != TARGET_LANG:
                from .i18n import set_language
                set_language(new_target_lang)
            
            # Update translation engine if changed
            if new_translator_engine != TRANSLATOR_ENGINE:
                from .translator import translation_manager
                translation_manager.reload()
            
        except Exception as e:
            # Show error message
            tui_app.message_log.write(f"Error saving configuration: {e}\n")
        
        # Exit configuration screen
        self.app.pop_screen()

def on_connection_status(status: str) -> None:
    """Update connection status in the TUI"""
    if tui_app is not None:
        tui_event_queue.put({'type': 'status_update', 'status': status})

def start_tui() -> None:
    """Start the TUI application"""
    global tui_app
    tui_app = YARTATApp()
    tui_app.run()

def tui_print_message(message: str) -> None:
    """Send a message to the TUI for printing"""
    if tui_app:
        tui_event_queue.put(("message", message))