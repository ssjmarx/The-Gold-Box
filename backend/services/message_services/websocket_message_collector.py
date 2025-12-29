#!/usr/bin/env python3
"""
WebSocket Message Collector for The Gold Box
Collects messages and dice rolls from WebSocket clients
Replaces DOM scraping with WebSocket-based collection

Enhanced with delta filtering to prevent old messages from entering backend processing.

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
    
    Enhanced with delta filtering to prevent duplicate/old messages from entering backend.
    """
    
    def __init__(self):
        """Initialize WebSocket message collector"""
        self.client_messages: Dict[str, List[Dict[str, Any]]] = {}
        self.client_rolls: Dict[str, List[Dict[str, Any]]] = {}
        self.client_last_processed: Dict[str, int] = {}  # Track last processed timestamp per client
        self.client_combat_state: Dict[str, Dict[str, Any]] = {}  # Cache combat state per client
        self.client_game_delta: Dict[str, Optional[Dict[str, Any]]] = {}  # Store game delta per client
        self.max_messages_per_client = 100
        self.max_rolls_per_client = 50
        
        # Initialize delta service for filtering
        try:
            from .message_delta_service import get_message_delta_service
            self.delta_service = get_message_delta_service()
            logger.info("WebSocketMessageCollector initialized with delta filtering support")
        except ImportError as e:
            logger.warning(f"Delta service not available - filtering disabled: {e}")
            self.delta_service = None
        
        logger.info("WebSocketMessageCollector initialized")
    
    def add_message_with_delta_filtering(self, client_id: str, message: Dict[str, Any], session_id: str) -> bool:
        """
        Add a chat message from WebSocket client with delta filtering
        
        Args:
            client_id: WebSocket client identifier
            message: Message data
            session_id: AI session ID for delta filtering
            
        Returns:
            True if message added successfully, False if filtered out
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
            
            # Apply delta filtering if available
            if self.delta_service and session_id:
                # Get session's last processed timestamp
                last_processed = self.delta_service.ai_session_manager.get_session_timestamp(session_id)
                msg_timestamp = message.get('ts') or message.get('timestamp')
                
                if msg_timestamp and last_processed and msg_timestamp < last_processed:
                    logger.debug(f"Filtering old message {msg_timestamp} < {last_processed} for client {client_id}")
                    return False  # Skip old message
            
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
    
    def add_roll_with_delta_filtering(self, client_id: str, roll_data: Dict[str, Any], session_id: str) -> bool:
        """
        Add a dice roll from WebSocket client with delta filtering
        
        Args:
            client_id: WebSocket client identifier
            roll_data: Dice roll data
            session_id: AI session ID for delta filtering
            
        Returns:
            True if roll added successfully, False if filtered out
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
            
            # Apply delta filtering if available
            if self.delta_service and session_id:
                # Get session's last processed timestamp
                last_processed = self.delta_service.ai_session_manager.get_session_timestamp(session_id)
                roll_timestamp = roll_data.get('ts') or roll_data.get('timestamp')
                
                if roll_timestamp and last_processed and roll_timestamp < last_processed:
                    logger.debug(f"Filtering old roll {roll_timestamp} < {last_processed} for client {client_id}")
                    return False  # Skip old roll
            
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
    
    def add_message(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a chat message from WebSocket client (legacy method without filtering)
        
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
        Add a dice roll from WebSocket client (legacy method without filtering)
        
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
    
    def get_combined_messages(self, client_id: str, max_count: int = 50, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get combined messages and rolls for a client with optional delta filtering
        
        Args:
            client_id: WebSocket client identifier
            max_count: Maximum number of items to return
            session_id: Optional AI session ID for delta filtering
            
        Returns:
            Combined list of messages and rolls in chronological order (oldest first)
        """
        try:
            messages = self.client_messages.get(client_id, [])
            rolls = self.client_rolls.get(client_id, [])
            
            # Combine all items
            all_items = messages + rolls
            
            # Filter out combat_context messages (should only come from get_encounter tool)
            all_items = [item for item in all_items if item.get('type') != 'combat_context']
            
            # Apply delta filtering if session_id is provided
            if session_id and self.delta_service:
                all_items = self._apply_delta_filtering(session_id, all_items)
            
            # Sort by timestamp (oldest first for proper AI processing)
            all_items.sort(key=lambda x: x.get('timestamp', 0))
            
            # Get most recent items, then return in chronological order (oldest first)
            recent_items = all_items[-max_count:] if len(all_items) > max_count else all_items
            recent_items.sort(key=lambda x: x.get('timestamp', 0))  # Ensure chronological order
            
            return recent_items
            
        except Exception as e:
            logger.error(f"Error getting combined messages for client {client_id}: {e}")
            return []
    
    def _apply_delta_filtering(self, session_id: str, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply delta filtering to messages using the message delta service
        
        Args:
            session_id: AI session ID for delta filtering
            messages: List of messages to filter
            
        Returns:
            Filtered list of messages
        """
        try:
            if not self.delta_service:
                return messages
            
            # Use delta service to filter messages
            filtered_messages = self.delta_service.apply_message_delta(session_id, messages)
            logger.debug(f"Delta filtering applied for session {session_id}: {len(filtered_messages)}/{len(messages)} messages passed filter")
            return filtered_messages
            
        except Exception as e:
            logger.error(f"Error applying delta filtering for session {session_id}: {e}")
            return messages  # Return original messages if filtering fails
    def get_delta_filtered_messages(self, client_id: str, session_id: str, max_count: int = 50) -> List[Dict[str, Any]]:
        """
        Get delta-filtered messages for a specific AI session
        
        Args:
            client_id: WebSocket client identifier
            session_id: AI session ID for delta filtering
            max_count: Maximum number of items to return
            
        Returns:
            Delta-filtered list of messages in chronological order
        """
        try:
            # Get all combined messages with delta filtering applied
            messages = self.get_combined_messages(client_id, max_count, session_id)
            
            # Log delta statistics for debugging
            if self.delta_service:
                stats = self.get_delta_stats(client_id, session_id)
                # logger.info(f"Delta filtering for session {session_id}: {stats['filtered_count']}/{stats['original_count']} new messages (delta ratio: {stats['delta_ratio']:.1%})")
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting delta-filtered messages for client {client_id}, session {session_id}: {e}")
            return []
    
    def get_delta_stats(self, client_id: str, session_id: str) -> Dict[str, Any]:
        """
        Get delta filtering statistics for a client session
        
        Args:
            client_id: WebSocket client identifier
            session_id: AI session ID
            
        Returns:
            Delta filtering statistics
        """
        if not self.delta_service:
            return {'delta_filtering_enabled': False}
        
        try:
            all_messages = self.get_combined_messages(client_id)
            return self.delta_service.get_delta_stats(session_id, all_messages)
        except Exception as e:
            logger.error(f"Error getting delta stats for client {client_id}: {e}")
            return {'delta_filtering_enabled': False, 'error': str(e)}
    
    def set_combat_state(self, client_id: str, combat_state: Dict[str, Any]) -> bool:
        """
        Set or update combat state for a client
        
        Args:
            client_id: WebSocket client identifier
            combat_state: Combat state data from frontend
            
        Returns:
            True if set successfully
        """
        try:
            # Store combat state with timestamp
            self.client_combat_state[client_id] = {
                **combat_state,
                'last_updated': int(time.time() * 1000)
            }
            
            logger.info(f"Updated combat state for client {client_id}: in_combat={combat_state.get('in_combat')}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting combat state for client {client_id}: {e}")
            return False
    
    def get_cached_combat_state(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached combat state for a client
        
        Args:
            client_id: WebSocket client identifier
            
        Returns:
            Cached combat state or None if not available
        """
        try:
            return self.client_combat_state.get(client_id)
            
        except Exception as e:
            logger.error(f"Error getting combat state for client {client_id}: {e}")
            return None
    
    def clear_combat_state(self, client_id: str) -> bool:
        """
        Clear combat state for a client
        
        Args:
            client_id: WebSocket client identifier
            
        Returns:
            True if cleared successfully
        """
        try:
            self.client_combat_state.pop(client_id, None)
            logger.debug(f"Cleared combat state for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing combat state for client {client_id}: {e}")
            return False
    
    def set_game_delta(self, client_id: str, delta: Dict[str, Any]) -> bool:
        """
        Store game delta object from frontend
        
        Args:
            client_id: WebSocket client identifier
            delta: Game delta object from FrontendDeltaService
            
        Returns:
            True if set successfully
        """
        try:
            self.client_game_delta[client_id] = delta
            logger.info(f"Game delta stored for client {client_id}: {delta}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting game delta for client {client_id}: {e}")
            return False
    
    def get_game_delta(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored game delta for a client
        
        Args:
            client_id: WebSocket client identifier
            
        Returns:
            Game delta object or None if not available
        """
        try:
            return self.client_game_delta.get(client_id)
            
        except Exception as e:
            logger.error(f"Error getting game delta for client {client_id}: {e}")
            return None
    
    def clear_game_delta(self, client_id: str) -> bool:
        """
        Clear game delta for a client (after AI turn completes)
        
        Args:
            client_id: WebSocket client identifier
            
        Returns:
            True if cleared successfully
        """
        try:
            self.client_game_delta.pop(client_id, None)
            logger.debug(f"Cleared game delta for client {client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing game delta for client {client_id}: {e}")
            return False
    
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
            self.client_last_processed.pop(client_id, None)
            self.client_combat_state.pop(client_id, None)
            self.client_game_delta.pop(client_id, None)
            
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
                'timestamp': datetime.now().isoformat(),
                'delta_filtering_enabled': self.delta_service is not None
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
                'timestamp': datetime.now().isoformat(),
                'delta_filtering_enabled': self.delta_service is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting all stats: {e}")
            return {}

# Global instance
websocket_message_collector = WebSocketMessageCollector()

def get_websocket_message_collector() -> WebSocketMessageCollector:
    """Get WebSocket message collector instance"""
    return websocket_message_collector

def add_client_message(client_id: str, message: Dict[str, Any]) -> bool:
    """
    Add a chat message from WebSocket client (legacy method)
    
    Args:
        client_id: WebSocket client identifier
        message: Message data
        
    Returns:
        True if message added successfully
    """
    return websocket_message_collector.add_message(client_id, message)

def add_client_roll(client_id: str, roll_data: Dict[str, Any]) -> bool:
    """
    Add a dice roll from WebSocket client (legacy method)
    
    Args:
        client_id: WebSocket client identifier
        roll_data: Dice roll data
        
    Returns:
        True if roll added successfully
    """
    return websocket_message_collector.add_roll(client_id, roll_data)

def add_client_message_with_delta(client_id: str, message: Dict[str, Any], session_id: str) -> bool:
    """
    Add a chat message from WebSocket client with delta filtering
    
    Args:
        client_id: WebSocket client identifier
        message: Message data
        session_id: AI session ID for delta filtering
        
    Returns:
        True if message added successfully, False if filtered out
    """
    return websocket_message_collector.add_message_with_delta_filtering(client_id, message, session_id)

def add_client_roll_with_delta(client_id: str, roll_data: Dict[str, Any], session_id: str) -> bool:
    """
    Add a dice roll from WebSocket client with delta filtering
    
    Args:
        client_id: WebSocket client identifier
        roll_data: Dice roll data
        session_id: AI session ID for delta filtering
        
    Returns:
        True if roll added successfully, False if filtered out
    """
    return websocket_message_collector.add_roll_with_delta_filtering(client_id, roll_data, session_id)

def get_combined_client_messages(client_id: str, max_count: int = 50, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get combined messages and rolls for a client with optional delta filtering
    
    Args:
        client_id: WebSocket client identifier
        max_count: Maximum number of items to return
        session_id: Optional AI session ID for delta filtering
        
    Returns:
        Combined list of messages and rolls in chronological order
    """
    return websocket_message_collector.get_combined_messages(client_id, max_count, session_id)

def get_delta_filtered_client_messages(client_id: str, session_id: str, max_count: int = 50) -> List[Dict[str, Any]]:
    """
    Get delta-filtered messages for a specific AI session
    
    Args:
        client_id: WebSocket client identifier
        session_id: AI session ID for delta filtering
        max_count: Maximum number of items to return
        
    Returns:
        Delta-filtered list of messages in chronological order
    """
    return websocket_message_collector.get_delta_filtered_messages(client_id, session_id, max_count)

def get_client_delta_stats(client_id: str, session_id: str) -> Dict[str, Any]:
    """
    Get delta filtering statistics for a client session
    
    Args:
        client_id: WebSocket client identifier
        session_id: AI session ID
        
    Returns:
        Delta filtering statistics
    """
    return websocket_message_collector.get_delta_stats(client_id, session_id)

def clear_client_data(client_id: str) -> bool:
    """
    Clear all data for a specific client
    
    Args:
        client_id: WebSocket client identifier
        
    Returns:
        True if cleared successfully
    """
    return websocket_message_collector.clear_client_data(client_id)
