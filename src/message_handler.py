"""Message Processing Module

This module is responsible for handling messages received via WebSocket, message formatting, and translation queue management.
"""

import json
import queue
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from .config import DEBUG, MAX_WORKERS, TRANSLATION_TIMEOUT
from .translator import translate_message
from .i18n import i18n_string as t

# Message counter and queues
message_count = 0
message_queue = queue.Queue()  # Message queue
output_queue = queue.Queue()  # For maintaining message output order
translation_cache: Dict[str, str] = {}  # Translation cache

class MessageItem:
    def __init__(self, msg: str, sender_type: str, name: str, sequence_id: int, needs_translation: bool = False):
        self.msg = msg
        self.sender_type = sender_type
        self.name = name
        self.sequence_id = sequence_id
        self.needs_translation = needs_translation

def format_message(msg_item: MessageItem, translated: Optional[str] = None) -> str:
    """Format message output"""
    base = f"{msg_item.sender_type}{msg_item.name}: {msg_item.msg}"
    if translated:
        # Directly use translated text instead of getting template through translation function
        return f"{base}{t("message.translation")}: {translated}\n"
    return f"{base}\n"

def process_translation_queue():
    """Background thread for processing translation queue"""
    pending_messages = {}  # For storing messages waiting to be output
    next_sequence_id = 0  # ID of the next message to output
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while True:
            try:
                msg_item = message_queue.get()
                if msg_item is None:  # Exit signal
                    break
                
                output = None
                if msg_item.needs_translation:
                    cache_key = f"{msg_item.msg}"
                    try:
                        # Prioritize using cached translation results
                        translated = translation_cache.get(cache_key) or \
                                   executor.submit(translate_message, msg_item.msg).result(timeout=TRANSLATION_TIMEOUT)
                        translation_cache[cache_key] = translated
                        output = format_message(msg_item, translated)
                    except Exception as e:
                        if DEBUG:
                            print(t("errors.translation_task").format(e))
                        output = format_message(msg_item, t("errors.translation_failed").format(msg_item.msg))
                
                # Store formatted message
                pending_messages[msg_item.sequence_id] = output or format_message(msg_item)
                
                # Output messages in sequence
                while next_sequence_id in pending_messages:
                    output_queue.put(pending_messages.pop(next_sequence_id))
                    next_sequence_id += 1
                    
            except queue.Empty:
                continue
            except Exception as e:
                if DEBUG:
                    print(t("errors.queue_processing").format(e))
            finally:
                message_queue.task_done()



def handle_message(ws, message: str) -> None:
    """Handle WebSocket messages
    
    Args:
        ws: WebSocket instance
        message: Received message content
    """
    global message_count
    if DEBUG:
        print(t("debug.received_raw_data").format(message))
        
    try: 
        data = json.loads(message)
        msg = data.get('content', '')
        if not msg:
            return
            
        # Update message counter
        sequence_id = message_count
        message_count += 1
        
        # Determine sender type
        sender_types = {
            "": t("sender_types.system"),
            True: t("sender_types.self"),
            False: t("sender_types.others")
        }
        sender_type = sender_types.get(
            "" if data.get('vlive_id', None) == "" else data.get('is_self', False)
        ) or t("sender_types.others")
        
        # Use translation manager to determine if translation is needed
        from .translator import translation_manager
        needs_translation, _, _ = translation_manager.should_translate(msg, sender_type)
        
        # Create message item
        msg_item = MessageItem(
            msg=msg,
            sender_type=sender_type,
            name=data.get('nickname', t("message.unknown_user")),
            sequence_id=sequence_id,
            needs_translation=needs_translation
        )
        
        # Put into message queue
        message_queue.put(msg_item)
            
    except json.JSONDecodeError as e:
        if DEBUG:
            print(t("errors.json_parse").format(e))
    except Exception as e:
        if DEBUG:
            print(t("errors.message_processing").format(e))