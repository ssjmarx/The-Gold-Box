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

logger = logging.getLogger(__name__)

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
        logger.info("WebSocket Handler initialized")
    
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
            logger.info("WebSocket connection accepted")
            
            # Wait for initial connection message
            connect_message = await websocket.receive_json()
            logger.info(f"Received connection message: {connect_message}")
            
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
            logger.info(f"WebSocket client connected: {client_id}")
            
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
                logger.info(f"WebSocket client {client_id} disconnected normally")
            except Exception as e:
                logger.error(f"WebSocket error for {client_id}: {e}")
            finally:
                # Clean up connection
                await self.websocket_manager.disconnect(client_id)
                
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            if client_id:
                await self.websocket_manager.disconnect(client_id)
            else:
                # Try to close the connection if it was opened
                try:
                    await websocket.close(code=1011, reason="Internal server error")
                except:
                    pass

    async def start_websocket_chat_handler(self):
        """
        Initialize WebSocket chat handler (now using FastAPI built-in WebSocket)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("WebSocket endpoint /ws registered with FastAPI")
            logger.info("WebSocket chat handler started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket chat handler: {e}")
            return False

    async def start_relay_server(self):
        """
        Start relay server as a subprocess (deprecated, using WebSocket instead)
        
        Returns:
            bool: True for compatibility
        """
        logger.info("Relay server is deprecated, using native WebSocket server instead")
        return True

    def stop_relay_server(self):
        """
        Stop relay server process (deprecated)
        """
        # Simplified for new implementation
        logger.info("Relay server stopped")

def get_websocket_connection_manager(websocket_manager):
    """
    Get the global WebSocket connection manager instance
    
    Args:
        websocket_manager: The global WebSocket connection manager instance
        
    Returns:
        The WebSocket connection manager instance
    """
    return websocket_manager
