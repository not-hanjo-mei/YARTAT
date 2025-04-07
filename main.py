import os
import threading
from time import sleep
from src.message_handler import process_translation_queue, handle_message
from src.websocket_client import ws_client
from src.i18n import i18n_string as t
from src.tui import start_tui, on_connection_status
from src.config import DEBUG

def initialize_console():
    """Initialize console settings"""
    if os.name == 'nt':
        os.system('chcp 65001')
        os.system('cls')
    elif os.name == 'posix':
        os.system('clear')

def initialize_websocket():
    """Initialize WebSocket connection"""
    ws_client.connect(
        on_message=handle_message,
        on_error=lambda ws, error: on_connection_status(f"{t('connection.error').format(error)}"),
        on_close=lambda ws, code, msg: on_connection_status(f"{t('connection.closed_abnormal').format(code, msg)}"),
        on_open=lambda ws: on_connection_status(t('connection.established'))
    )
    
    ws_thread = threading.Thread(target=ws_client.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

def initialize_translation_queue():
    """Initialize translation queue"""
    translation_thread = threading.Thread(target=process_translation_queue)
    translation_thread.daemon = True
    translation_thread.start()

def main():
    # Initialize console
    initialize_console()
    
    # Start TUI interface (this will block the main thread until TUI exits)
    try:
        initialize_websocket()
        initialize_translation_queue()
        if DEBUG:
            while True:
                sleep(1)
        start_tui()
    except KeyboardInterrupt:
        print(t("program.interrupted"))
    except Exception as e:
        print(t("program.error").format(e))
        print(t("program.exit_hint"))
    finally:
        ws_client.close()

if __name__ == "__main__":
    main()