"""WebSocket Communication Module

This module is responsible for establishing WebSocket connections with the Reality App server and handling real-time messages.
Includes a disconnection reconnection mechanism, with a maximum of five reconnection attempts, each with increasing interval time.
"""

import websocket
import ssl
import threading
from typing import Callable, Optional
from .config import MEDIA_ID, MY_VLIVEID, MY_GID, MY_AUTH, DEBUG
from .i18n import i18n_string as t

class WebSocketClient:
    def __init__(self):
        self.url = "wss://comment.reality.app"
        self.ws: Optional[websocket.WebSocketApp] = None
        self.headers = {
            "X-WFLE-vLiveID": MY_VLIVEID,
            "X-WFLE-GID": MY_GID,
            "Authorization": MY_AUTH,
            "X-WFLE-CLIENT-IDENTIFIER": "viewer",
            "Accept-Charset": "UTF-8",
            "Accept": "*/*",
            "User-Agent": "ktor-client",
            "Sec-WebSocket-Extensions": "permessage-deflate"
        }
        self.reconnect_count = 0
        self.max_reconnect_attempts = 5
        self.reconnect_base_delay = 2  # Base reconnection delay (seconds)
        self.is_reconnecting = False
        self._callbacks = {}
        self._reconnect_timer = None
        self._connected = False
        self._normal_exit = False  # Add normal exit flag

    def is_connected(self) -> bool:
        """Check if the WebSocket connection is established and in connected state
        
        Returns:
            bool: Returns True if the connection is established and in connected state, otherwise False
        """
        return self.ws is not None and self._connected
    
    def connect(self, on_message: Callable, on_error: Callable, on_close: Callable, on_open: Callable) -> None:
        """Establish WebSocket connection
        
        Args:
            on_message: Message handling callback function
            on_error: Error handling callback function
            on_close: Connection close callback function
            on_open: Connection established callback function
        """
        # Save callback functions for reconnection
        self._callbacks = {
            'on_message': on_message,
            'on_error': on_error,
            'on_close': self._on_close_wrapper(on_close),
            'on_open': on_open
        }
        
        websocket.enableTrace(DEBUG)
        self.ws = websocket.WebSocketApp(
            f"{self.url}?media_id={MEDIA_ID}",
            header=self.headers,
            on_message=on_message,
            on_error=on_error,
            on_close=self._callbacks['on_close'],
            on_open=self._on_open_wrapper(on_open)
        )
    
    def _on_close_wrapper(self, original_on_close: Callable) -> Callable:
        def wrapped_on_close(ws, close_status_code, close_msg):
            # Update connection status
            self._connected = False
            
            # Call the original on_close callback
            original_on_close(ws, close_status_code, close_msg)
            
            # Only attempt to reconnect on abnormal exit
            if not self.is_reconnecting and not self._normal_exit and close_status_code != 1000:
                self._schedule_reconnect()
                
        return wrapped_on_close
    
    def _on_open_wrapper(self, original_on_open: Callable) -> Callable:
        """Wrap the original on_open callback, add connection status update
        
        Args:
            original_on_open: Original on_open callback function
            
        Returns:
            Wrapped on_open callback function
        """
        def wrapped_on_open(ws):
            # Update connection status
            self._connected = True
            # Reset reconnection count
            self.reconnect_count = 0
            self.is_reconnecting = False
            # Call the original on_open callback
            original_on_open(ws)
            
        return wrapped_on_open
    
    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt"""
        if self.reconnect_count >= self.max_reconnect_attempts:
            if DEBUG:
                print(t("connection.max_attempts").format(self.max_reconnect_attempts))
            return
            
        self.is_reconnecting = True
        self.reconnect_count += 1
        
        # Calculate delay with exponential backoff
        delay = self.reconnect_base_delay * (2 ** (self.reconnect_count - 1))
        
        if DEBUG:
            print(t("connection.reconnect_attempt").format(self.reconnect_count, delay))
            
        # Cancel any existing timer
        if self._reconnect_timer:
            self._reconnect_timer.cancel()
            
        # Schedule reconnection
        self._reconnect_timer = threading.Timer(delay, self._reconnect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()
    
    def _reconnect(self) -> None:
        """Perform the actual reconnection"""
        if self.ws is not None:
            # Create a new WebSocket instance with the saved callbacks
            self.ws = websocket.WebSocketApp(
                f"{self.url}?media_id={MEDIA_ID}",
                header=self.headers,
                on_message=self._callbacks.get('on_message'),
                on_error=self._callbacks.get('on_error'),
                on_close=self._callbacks.get('on_close'),
                on_open=self._callbacks.get('on_open')
            )
            
            # Start the WebSocket in a new thread
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
    
    def run_forever(self) -> None:
        """Run the WebSocket connection in the current thread"""
        if self.ws is not None:
            # Set SSL options to use TLS 1.2
            ssl_opt = {"cert_reqs": ssl.CERT_NONE}
            self.ws.run_forever(sslopt=ssl_opt)
    
    def close(self) -> None:
        """Close the WebSocket connection"""
        self._normal_exit = True  # Mark as normal exit
        if self._reconnect_timer:
            self._reconnect_timer.cancel()
            
        if self.ws is not None:
            self.ws.close()

# Create global WebSocket client instance
ws_client = WebSocketClient()