#!/usr/bin/env python3
"""
The Gold Box - WebSocket Handler Module
Handles WebSocket connections for real-time communication with Foundry VTT frontend

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
Dependencies: FastAPI (MIT), Uvicorn (BSD 3-Clause)
"""

from fastapi import WebSocket, WebSocketDisconnect
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Import frontend settings handler
from .frontend_settings_handler import get_frontend_settings_handler, FrontendSettingsException

logger = logging.getLogger(__name__)

class WebSocketHandlerException(Exception):
    """Exception raised when WebSocket handler operations fail"""
    pass

class WebSocketHandler:
    """
    Handles WebSocket connections and message processing
    """
    
    def __init__(self, websocket_manager):
        """
        Initialize WebSocket handler
        
        Args:
            websocket_manager: The global WebSocket connection manager instance
        """
        self.websocket_manager = websocket_manager
        # WebSocket Handler initialized
    
    async def handle_websocket_connection(self, websocket: WebSocket):
        """
        Handle WebSocket connection lifecycle
        Accept connection, validate, register client, handle messages, cleanup
        
        Args:
            websocket: FastAPI WebSocket connection object
        """
        client_id = None
        
        try:
            # Accept WebSocket connection first
            await websocket.accept()
            
            # Wait for initial connection message
            connect_message = await websocket.receive_json()
            
            # Validate connection message
            if connect_message.get("type") != "connect":
                await websocket.close(code=1008, reason="Expected connection message")
                logger.warning("WebSocket: Expected connect message")
                return
            
            client_id = connect_message.get("client_id")
            token = connect_message.get("token")
            
            if not client_id or not token:
                await websocket.close(code=1008, reason="Missing client_id or token")
                logger.warning("WebSocket: Missing client_id or token")
                return
            
            # Check for duplicate connections
            if client_id in self.websocket_manager.connection_info:
                await websocket.close(code=1008, reason="Client ID already connected")
                logger.warning(f"WebSocket: Duplicate client ID {client_id}")
                return
            
            # Connect client
            connection_info = {
                "token": token,
                "world_info": connect_message.get("world_info", {}),
                "user_info": connect_message.get("user_info", {})
            }
            
            # Manually add to connection manager since we already accepted
            self.websocket_manager.active_connections.append(websocket)
            self.websocket_manager.connection_info[client_id] = {
                "websocket": websocket,
                "connected_at": datetime.now().isoformat(),
                **connection_info
            }
            
            # Send connection confirmation
            await self.websocket_manager.send_to_client(client_id, {
                "type": "connected",
                "data": {
                    "client_id": client_id,
                    "server_time": datetime.now().isoformat(),
                    "message": "Successfully connected to The Gold Box WebSocket server"
                }
            })
            
            # Handle messages from this client
            try:
                while True:
                    message = await websocket.receive_json()
                    await self.websocket_manager.handle_message(client_id, message)
                    
            except WebSocketDisconnect:
                # WebSocket client disconnected
                pass
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"WebSocket message processing error for {client_id}: {e}")
                raise WebSocketHandlerException(f"Message processing failed for {client_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected WebSocket error for {client_id}: {e}")
                raise WebSocketHandlerException(f"Unexpected WebSocket error for {client_id}: {e}")
            finally:
                # Clean up connection
                await self.websocket_manager.disconnect(client_id)
                
        except WebSocketDisconnect:
            # Client disconnected during initial connection - normal behavior
            logger.debug("WebSocket client disconnected during initial connection")
            if client_id:
                await self.websocket_manager.disconnect(client_id)
        except (ValueError, KeyError) as validation_error:
            logger.error(f"WebSocket connection validation error: {validation_error}")
            if client_id:
                await self.websocket_manager.disconnect(client_id)
            else:
                try:
                    await websocket.close(code=1008, reason="Invalid connection data")
                except Exception as close_error:
                    logger.debug(f"WebSocket close during connection validation: {close_error}")
            raise WebSocketHandlerException(f"Connection validation failed: {validation_error}")
        except Exception as connection_error:
            logger.error(f"WebSocket connection error: {connection_error}")
            if client_id:
                await self.websocket_manager.disconnect(client_id)
            else:
                try:
                    await websocket.close(code=1011, reason="Internal server error")
                except Exception as close_error:
                    logger.debug(f"WebSocket close during connection error: {close_error}")
            raise WebSocketHandlerException(f"Connection error: {connection_error}")

    async def start_websocket_chat_handler(self):
        """
        Initialize WebSocket chat handler (now using FastAPI built-in WebSocket)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return True
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket chat handler: {e}")
            raise WebSocketHandlerException(f"WebSocket handler startup failed: {e}")

    # Relay server functionality removed - using native WebSocket server instead
    # All relay server dependencies have been eliminated in favor of direct WebSocket communication

def get_websocket_connection_manager(websocket_manager):
    """
    Get global WebSocket connection manager instance
    
    Args:
        websocket_manager: The global WebSocket connection manager instance
        
    Returns:
        The WebSocket connection manager instance
    """
    return websocket_manager
