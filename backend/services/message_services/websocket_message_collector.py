#!/usr/bin/env python3
"""
WebSocket Message Collector for The Gold Box
Collects messages and dice rolls from WebSocket clients
Replaces DOM scraping with WebSocket-based collection

License: CC-BY-NC-SA 4.0
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketMessageCollector:
    """
    Collects messages and dice rolls from WebSocket clients
    Replaces DOM scraping with real-time WebSocket collection
    """
    
    def __init__(self):
        """Initialize WebSocket message collector"""
        self.client_messages: Dict[str, List[Dict[str, Any]]] = {}
        self.client_rolls: Dict[str, List[Dict[str, Any]]] = {}
        self.max_messages_per_client = 100
        self.max_rolls_per_client = 50
        
        logger.info("WebSocketMessageCollector initialized")
    
    def add_message(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a chat message from WebSocket client
        
        Args:
            client_id: WebSocket client identifier
            message: Message data
            
        Returns:
            True if message added successfully
        """
        try:
            if client_id not in self.client_messages:
                self.client_messages[client_id] = []
            
            # Validate message structure
            if not self._validate_message(message):
                logger.warning(f"Invalid message structure from client {client_id}: {message}")
                return False
            
            # Add timestamp if not present
            if 'timestamp' not in message:
                message['timestamp'] = int(time.time() * 1000)
            
            # Add client ID to message
            message['client_id'] = client_id
            
            self.client_messages[client_id].append(message)
            
            # Limit message count
            if len(self.client_messages[client_id]) > self.max_messages_per_client:
                self.client_messages[client_id] = self.client_messages[client_id][-self.max_messages_per_client:]
            
            logger.debug(f"Added message from client {client_id}: {message.get('type', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message from client {client_id}: {e}")
            return False
    
    def add_roll(self, client_id: str, roll_data: Dict[str, Any]) -> bool:
        """
        Add a dice roll from WebSocket client
        
        Args:
            client_id: WebSocket client identifier
            roll_data: Dice roll data
            
        Returns:
            True if roll added successfully
        """
        try:
            if client_id not in self.client_rolls:
                self.client_rolls[client_id] = []
            
            # Validate roll structure
            if not self._validate_roll(roll_data):
                logger.warning(f"Invalid roll structure from client {client_id}: {roll_data}")
                return False
            
            # Add timestamp if not present
            if 'timestamp' not in roll_data:
                roll_data['timestamp'] = int(time.time() * 1000)
            
            # Add client ID to roll
            roll_data['client_id'] = client_id
            
            self.client_rolls[client_id].append(roll_data)
            
            # Limit roll count
            if len(self.client_rolls[client_id]) > self.max_rolls_per_client:
                self.client_rolls[client_id] = self.client_rolls[client_id][-self.max_rolls_per_client:]
            
            logger.debug(f"Added roll from client {client_id}: {roll_data.get('formula', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding roll from client {client_id}: {e}")
            return False
    
    def get_combined_messages(self, client_id: str, max_count: int = 50) -> List[Dict[str, Any]]:
        """
        Get combined messages and rolls for a client
        
        Args:
            client_id: WebSocket client identifier
            max_count: Maximum number of items to return
            
        Returns:
            Combined list of messages and rolls in chronological order (oldest first)
        """
        try:
            messages = self.client_messages.get(client_id, [])
            rolls = self.client_rolls.get(client_id, [])
            
            # Combine all items
            all_items = messages + rolls
            
            # Sort by timestamp (oldest first for proper AI processing)
            all_items.sort(key=lambda x: x.get('timestamp', 0))
            
            # Get the most recent items, then return in chronological order (oldest first)
            recent_items = all_items[-max_count:] if len(all_items) > max_count else all_items
            recent_items.sort(key=lambda x: x.get('timestamp', 0))  # Ensure chronological order
            
            return recent_items
            
        except Exception as e:
            logger.error(f"Error getting combined messages for client {client_id}: {e}")
            return []
    
    def clear_client_data(self, client_id: str) -> bool:
        """
        Clear all data for a specific client
        
        Args:
            client_id: WebSocket client identifier
            
        Returns:
            True if cleared successfully
        """
        try:
            self.client_messages.pop(client_id, None)
            self.client_rolls.pop(client_id, None)
            
            logger.debug(f"Cleared data for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing data for client {client_id}: {e}")
            return False
    
    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Validate message structure
        
        Args:
            message: Message to validate
            
        Returns:
            True if valid
        """
        try:
            # Check required fields
            if not isinstance(message, dict):
                return False
            
            # Must have content or be a recognized type
            message_type = message.get('type')
            if 'content' not in message and message_type not in ['system', 'combat_context']:
                return False
            
            # Content must be non-empty for non-system, non-combat-context messages
            content = message.get('content', '')
            if message_type not in ['system', 'combat_context'] and not content.strip():
                return False
            
            # Combat context messages must have combat_context field
            if message_type == 'combat_context':
                if 'combat_context' not in message:
                    return False
                # Validate combat_context structure
                combat_context = message.get('combat_context')
                if not isinstance(combat_context, dict):
                    return False
                if 'in_combat' not in combat_context:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating message: {e}")
            return False
    
    def _validate_roll(self, roll_data: Dict[str, Any]) -> bool:
        """
        Validate dice roll structure
        
        Args:
            roll_data: Roll data to validate
            
        Returns:
            True if valid
        """
        try:
            # Check required fields
            if not isinstance(roll_data, dict):
                return False
            
            # Must have formula for roll
            if 'formula' not in roll_data:
                return False
            
            # Must have type set to 'roll'
            if roll_data.get('type') != 'roll':
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating roll: {e}")
            return False
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """
        Get statistics for a client
        
        Args:
            client_id: WebSocket client identifier
            
        Returns:
            Client statistics
        """
        try:
            messages = self.client_messages.get(client_id, [])
            rolls = self.client_rolls.get(client_id, [])
            
            return {
                'client_id': client_id,
                'message_count': len(messages),
                'roll_count': len(rolls),
                'total_items': len(messages) + len(rolls),
                'last_message_time': messages[-1].get('timestamp') if messages else None,
                'last_roll_time': rolls[-1].get('timestamp') if rolls else None,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting stats for client {client_id}: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all clients
        
        Returns:
            All client statistics
        """
        try:
            total_messages = sum(len(msgs) for msgs in self.client_messages.values())
            total_rolls = sum(len(rolls) for rolls in self.client_rolls.values())
            total_clients = len(set(list(self.client_messages.keys()) + list(self.client_rolls.keys())))
            
            return {
                'total_clients': total_clients,
                'total_messages': total_messages,
                'total_rolls': total_rolls,
                'total_items': total_messages + total_rolls,
                'client_ids': list(set(list(self.client_messages.keys()) + list(self.client_rolls.keys()))),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting all stats: {e}")
            return {}

# Global instance
websocket_message_collector = WebSocketMessageCollector()

def get_websocket_message_collector() -> WebSocketMessageCollector:
    """Get the WebSocket message collector instance"""
    return websocket_message_collector

def add_client_message(client_id: str, message: Dict[str, Any]) -> bool:
    """
    Add a chat message from WebSocket client
    
    Args:
        client_id: WebSocket client identifier
        message: Message data
        
    Returns:
        True if message added successfully
    """
    return websocket_message_collector.add_message(client_id, message)

def add_client_roll(client_id: str, roll_data: Dict[str, Any]) -> bool:
    """
    Add a dice roll from WebSocket client
    
    Args:
        client_id: WebSocket client identifier
        roll_data: Dice roll data
        
    Returns:
        True if roll added successfully
    """
    return websocket_message_collector.add_roll(client_id, roll_data)

def get_combined_client_messages(client_id: str, max_count: int = 50) -> List[Dict[str, Any]]:
    """
    Get combined messages and rolls for a client
    
    Args:
        client_id: WebSocket client identifier
        max_count: Maximum number of items to return
        
    Returns:
        Combined list of messages and rolls in chronological order
    """
    return websocket_message_collector.get_combined_messages(client_id, max_count)

def clear_client_data(client_id: str) -> bool:
    """
    Clear all data for a specific client
    
    Args:
        client_id: WebSocket client identifier
        
    Returns:
        True if cleared successfully
    """
    return websocket_message_collector.clear_client_data(client_id)
