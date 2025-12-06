"""
The Gold Box - WebSocket Server
Native WebSocket implementation to replace Relay Server dependency
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

class GoldBoxWebSocketServer:
    """
    Native WebSocket server for The Gold Box
    Replaces Relay Server dependency with direct WebSocket communication
    """
    
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.client_info: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Set[str]] = {}  # token -> set of client_ids
        self.message_handlers: Dict[str, Callable] = {}
        self.running = False
        self.server = None
        
    async def start_server(self):
        """Start WebSocket server"""
        try:
            logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
            
            # Create WebSocket server with proper CORS handling
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                ping_interval=20,  # 20 seconds
                ping_timeout=10,   # 10 seconds
                close_timeout=10,  # 10 seconds
                max_size=10**7,  # 10MB max message size
                compression=None,   # Disable compression for better performance
            )
            
            self.running = True
            logger.info(f"WebSocket server started successfully on {self.host}:{self.port}")
            logger.info(f"server listening on 127.0.0.1:{self.port}")
            logger.info(f"server listening on [::1]:{self.port}")
            
            # Keep server running
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        try:
            self.running = False
            
            # Close all client connections
            for client_id, websocket in list(self.clients.items()):
                try:
                    await websocket.close(1000, "Server shutting down")
                    logger.info(f"Closed connection to client {client_id}")
                except Exception as e:
                    logger.error(f"Error closing connection to {client_id}: {e}")
            
            # Clear client data
            self.clients.clear()
            self.client_info.clear()
            self.sessions.clear()
            
            # Close server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            logger.info("WebSocket server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping WebSocket server: {e}")
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connection"""
        client_id = None
        
        try:
            logger.info(f"New WebSocket connection from {websocket.remote_address}")
            
            # Wait for initial connection message
            connect_message = await websocket.recv()
            
            try:
                connect_data = json.loads(connect_message)
            except json.JSONDecodeError as e:
                await websocket.close(1008, "Invalid JSON in connection message")
                logger.error(f"Invalid JSON from {websocket.remote_address}: {e}")
                return
            
            # Validate connection message
            if connect_data.get("type") != "connect":
                await websocket.close(1008, "Expected connection message")
                logger.warning(f"Expected connect message from {websocket.remote_address}")
                return
            
            client_id = connect_data.get("client_id")
            token = connect_data.get("token")
            
            if not client_id or not token:
                await websocket.close(1008, "Missing client_id or token")
                logger.warning(f"Missing client_id or token from {websocket.remote_address}")
                return
            
            # Check if client already exists
            if client_id in self.clients:
                await websocket.close(1008, "Client ID already connected")
                logger.warning(f"Duplicate client ID {client_id} from {websocket.remote_address}")
                return
            
            # Register client
            self.clients[client_id] = websocket
            self.client_info[client_id] = {
                "connected_at": datetime.now().isoformat(),
                "remote_address": str(websocket.remote_address),
                "token": token,
                "world_info": connect_data.get("world_info", {}),
                "user_info": connect_data.get("user_info", {}),
                "last_ping": time.time()
            }
            
            # Add to session group
            if token not in self.sessions:
                self.sessions[token] = set()
            self.sessions[token].add(client_id)
            
            logger.info(f"Client {client_id} registered with token {token[:8]}...")
            
            # Send connection confirmation
            await self.send_to_client(client_id, {
                "type": "connected",
                "data": {
                    "client_id": client_id,
                    "server_time": datetime.now().isoformat(),
                    "message": "Successfully connected to The Gold Box WebSocket server"
                }
            })
            
            # Handle messages from this client
            try:
                async for message in websocket:
                    await self.handle_message(websocket, client_id, message)
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client {client_id} disconnected normally")
            except Exception as e:
                logger.error(f"Error handling messages from {client_id}: {e}")
            
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected during handshake")
        except Exception as e:
            logger.error(f"Error in connection handler: {e}")
        finally:
            # Clean up client connection
            if client_id and client_id in self.clients:
                await self.unregister_client(client_id)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, client_id: str, raw_message: str):
        """Handle incoming message from client"""
        try:
            # Parse message
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {client_id}: {e}")
                await self.send_error(client_id, "Invalid JSON format")
                return
            
            # Update last activity
            if client_id in self.client_info:
                self.client_info[client_id]["last_ping"] = time.time()
            
            message_type = message.get("type")
            
            # Handle ping messages
            if message_type == "ping":
                await self.send_to_client(client_id, {
                    "type": "pong",
                    "timestamp": time.time()
                })
                return
            
            # Route to registered handlers
            if message_type in self.message_handlers:
                try:
                    await self.message_handlers[message_type](client_id, message)
                except Exception as e:
                    logger.error(f"Error in message handler for {message_type}: {e}")
                    await self.send_error(client_id, f"Handler error: {e}")
            else:
                logger.warning(f"Unknown message type {message_type} from {client_id}")
                await self.send_error(client_id, f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await self.send_error(client_id, f"Message processing error: {e}")
    
    async def unregister_client(self, client_id: str):
        """Unregister client and clean up resources"""
        try:
            if client_id in self.clients:
                del self.clients[client_id]
            
            if client_id in self.client_info:
                token = self.client_info[client_id]["token"]
                del self.client_info[client_id]
                
                # Remove from session
                if token in self.sessions:
                    self.sessions[token].discard(client_id)
                    if not self.sessions[token]:
                        del self.sessions[token]
            
            logger.info(f"Client {client_id} unregistered")
            
        except Exception as e:
            logger.error(f"Error unregistering client {client_id}: {e}")
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific client"""
        try:
            if client_id not in self.clients:
                logger.warning(f"Attempted to send to unknown client {client_id}")
                return False
            
            websocket = self.clients[client_id]
            if websocket.open:
                # Add timestamp to message
                message["timestamp"] = time.time()
                await websocket.send(json.dumps(message))
                return True
            else:
                logger.warning(f"Attempted to send to closed client {client_id}")
                await self.unregister_client(client_id)
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to {client_id}: {e}")
            await self.unregister_client(client_id)
            return False
    
    async def send_to_session(self, token: str, message: Dict[str, Any]) -> int:
        """Send message to all clients in session"""
        try:
            if token not in self.sessions:
                logger.warning(f"Attempted to send to unknown session {token}")
                return 0
            
            sent_count = 0
            client_ids = list(self.sessions[token])  # Copy to avoid modification during iteration
            
            for client_id in client_ids:
                if await self.send_to_client(client_id, message):
                    sent_count += 1
            
            logger.info(f"Sent message to {sent_count}/{len(client_ids)} clients in session {token[:8]}...")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error broadcasting to session {token}: {e}")
            return 0
    
    async def send_error(self, client_id: str, error_message: str):
        """Send error message to client"""
        await self.send_to_client(client_id, {
            "type": "error",
            "data": {
                "error": error_message,
                "timestamp": time.time()
            }
        })
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler"""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client information"""
        return self.client_info.get(client_id)
    
    def get_session_clients(self, token: str) -> Set[str]:
        """Get all client IDs in a session"""
        return self.sessions.get(token, set())
    
    def get_connected_clients(self) -> Set[str]:
        """Get all connected client IDs"""
        return set(self.clients.keys())
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "connected_clients": len(self.clients),
            "active_sessions": len(self.sessions),
            "server_running": self.running,
            "uptime": datetime.now().isoformat() if self.running else None
        }

# Global WebSocket server instance
websocket_server = None

def get_websocket_server() -> GoldBoxWebSocketServer:
    """Get or create WebSocket server instance"""
    global websocket_server
    if websocket_server is None:
        websocket_server = GoldBoxWebSocketServer()
    return websocket_server

async def start_websocket_server():
    """Start the WebSocket server"""
    server = get_websocket_server()
    await server.start_server()

async def stop_websocket_server():
    """Stop the WebSocket server"""
    server = get_websocket_server()
    await server.stop_server()
