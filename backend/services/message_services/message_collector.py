"""
The Gold Box - Message Collector
Collects messages directly from WebSocket clients instead of using relay server
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from shared.exceptions import MessageCollectionException, MessageValidationException
from shared.utils.message_type_detector import is_dice_message, detect_message_type, MessageType
from shared.utils.roll_extractor import extract_roll_data

logger = logging.getLogger(__name__)

class MessageCollector:
    """
    Collects and manages messages from WebSocket clients
    Replaces relay server dependency with direct client communication
    """
    
    def __init__(self):
        self.client_messages: Dict[str, List[Dict[str, Any]]] = {}
        self.client_rolls: Dict[str, List[Dict[str, Any]]] = {}
        self.max_messages_per_client = 1000  # Prevent memory issues
        self.message_retention_hours = 24  # Keep messages for 24 hours
        self._last_timestamp: Dict[str, int] = {}  # Track last timestamp per client for sequential ordering
        
    def _get_sequential_timestamp(self, client_id: str) -> int:
        """
        Get a sequential timestamp ONLY for messages that don't have their own timestamp.
        Foundry timestamps should always be preserved when available.
        """
        current_time = int(time.time() * 1000)
        
        # Initialize or get last timestamp for this client
        if client_id not in self._last_timestamp:
            self._last_timestamp[client_id] = current_time
            return current_time
        
        # If last timestamp is too old (more than 1 second), reset to current time
        if current_time - self._last_timestamp[client_id] > 1000:
            self._last_timestamp[client_id] = current_time
            return current_time
        
        # Increment by 1ms to ensure sequential ordering
        self._last_timestamp[client_id] += 1
        return self._last_timestamp[client_id]
    
    def add_message(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a chat message from a client
        
        Raises:
            MessageValidationException: When message data is invalid
            MessageCollectionException: When message collection fails
        """
        try:
            # Validate input
            if not client_id or not isinstance(client_id, str):
                raise MessageValidationException("Client ID must be a non-empty string")
            
            if not message or not isinstance(message, dict):
                raise MessageValidationException("Message must be a non-empty dictionary")
            
            if client_id not in self.client_messages:
                self.client_messages[client_id] = []
            
            # Use existing timestamp if provided, otherwise generate sequential timestamp
            timestamp_value = message.get("timestamp")
            if timestamp_value is None:
                timestamp_value = self._get_sequential_timestamp(client_id)
            else:
                # Convert to int if needed, but preserve original value
                try:
                    if isinstance(timestamp_value, str):
                        timestamp_value = int(timestamp_value)
                    elif isinstance(timestamp_value, (int, float)):
                        timestamp_value = int(timestamp_value)
                    else:
                        timestamp_value = self._get_sequential_timestamp(client_id)
                except (ValueError, TypeError):
                    timestamp_value = self._get_sequential_timestamp(client_id)
                
            enriched_message = {
                **message,
                "timestamp": timestamp_value,
                "client_id": client_id,
                "message_type": "chat",
                "collected_at": datetime.now().isoformat()
            }
            
            self.client_messages[client_id].append(enriched_message)
            
            # Cleanup old messages if needed
            self._cleanup_client_messages(client_id)
            
            logger.debug(f"Added chat message for client {client_id}: {message.get('type', 'unknown')}")
            return True
            
        except MessageValidationException:
            raise  # Re-raise validation exceptions directly
        except Exception as e:
            raise MessageCollectionException(f"Error adding message for client {client_id}: {e}")
    
    def add_roll(self, client_id: str, roll_data: Dict[str, Any]) -> bool:
        """
        Add a dice roll from a client
        
        Raises:
            MessageValidationException: When roll data is invalid
            MessageCollectionException: When roll collection fails
        """
        try:
            # Validate input
            if not client_id or not isinstance(client_id, str):
                raise MessageValidationException("Client ID must be a non-empty string")
            
            if not roll_data or not isinstance(roll_data, dict):
                raise MessageValidationException("Roll data must be a non-empty dictionary")
            
            if client_id not in self.client_rolls:
                self.client_rolls[client_id] = []
            
            # Use existing timestamp if provided, otherwise generate sequential timestamp
            timestamp_value = roll_data.get("timestamp")
            if timestamp_value is None:
                timestamp_value = self._get_sequential_timestamp(client_id)
            else:
                # Convert to int if needed, but preserve original value
                try:
                    if isinstance(timestamp_value, str):
                        timestamp_value = int(timestamp_value)
                    elif isinstance(timestamp_value, (int, float)):
                        timestamp_value = int(timestamp_value)
                    else:
                        timestamp_value = self._get_sequential_timestamp(client_id)
                except (ValueError, TypeError):
                    timestamp_value = self._get_sequential_timestamp(client_id)
                
            enriched_roll = {
                **roll_data,
                "timestamp": timestamp_value,
                "client_id": client_id,
                "message_type": "roll",
                "collected_at": datetime.now().isoformat()
            }
            
            self.client_rolls[client_id].append(enriched_roll)
            
            # Cleanup old rolls if needed
            self._cleanup_client_rolls(client_id)
            
            logger.debug(f"Added roll for client {client_id}: {roll_data.get('formula', 'unknown')}")
            return True
            
        except MessageValidationException:
            raise  # Re-raise validation exceptions directly
        except Exception as e:
            raise MessageCollectionException(f"Error adding roll for client {client_id}: {e}")
    
    def get_messages(self, client_id: str, count: int = 15) -> List[Dict[str, Any]]:
        """
        Get recent chat messages for a client
        
        Raises:
            MessageValidationException: When client_id or count is invalid
            MessageCollectionException: When message retrieval fails
        """
        try:
            # Validate input
            if not client_id or not isinstance(client_id, str):
                raise MessageValidationException("Client ID must be a non-empty string")
            
            if count is None or not isinstance(count, int) or count <= 0:
                raise MessageValidationException("Count must be a positive integer")
            
            if client_id not in self.client_messages:
                return []
            
            messages = self.client_messages[client_id]
            
            # Sort by timestamp (newest first)
            sorted_messages = sorted(messages, key=lambda x: x.get('timestamp', 0), reverse=True)
            
            # Return the most recent 'count' messages
            recent_messages = sorted_messages[:count]
            
            # Reverse to chronological order (oldest first)
            return list(reversed(recent_messages))
            
        except MessageValidationException:
            raise  # Re-raise validation exceptions directly
        except Exception as e:
            raise MessageCollectionException(f"Error getting messages for client {client_id}: {e}")
    
    def get_rolls(self, client_id: str, count: int = 15) -> List[Dict[str, Any]]:
        """
        Get recent dice rolls for a client
        
        Raises:
            MessageValidationException: When client_id or count is invalid
            MessageCollectionException: When roll retrieval fails
        """
        try:
            # Validate input
            if not client_id or not isinstance(client_id, str):
                raise MessageValidationException("Client ID must be a non-empty string")
            
            if count is None or not isinstance(count, int) or count <= 0:
                raise MessageValidationException("Count must be a positive integer")
            
            if client_id not in self.client_rolls:
                return []
            
            rolls = self.client_rolls[client_id]
            
            # Sort by timestamp (newest first)
            sorted_rolls = sorted(rolls, key=lambda x: x.get('timestamp', 0), reverse=True)
            
            # Return the most recent 'count' rolls
            recent_rolls = sorted_rolls[:count]
            
            # Reverse to chronological order (oldest first)
            return list(reversed(recent_rolls))
            
        except MessageValidationException:
            raise  # Re-raise validation exceptions directly
        except Exception as e:
            raise MessageCollectionException(f"Error getting rolls for client {client_id}: {e}")
    
    def get_combined_messages(self, client_id: str, count: int = 15) -> List[Dict[str, Any]]:
        """
        Get combined chat messages and rolls for a client, sorted chronologically
        
        Raises:
            MessageValidationException: When client_id or count is invalid
            MessageCollectionException: When message retrieval fails
        """
        try:
            # Validate input
            if not client_id or not isinstance(client_id, str):
                raise MessageValidationException("Client ID must be a non-empty string")
            
            if count is None or not isinstance(count, int) or count <= 0:
                raise MessageValidationException("Count must be a positive integer")
            
            # Get messages and rolls separately with proper count handling
            messages = self.get_messages(client_id, count)
            rolls = self.get_rolls(client_id, count)
            
            # Combine all messages
            all_messages = []
            
            # Add chat messages with _source
            for msg in messages:
                msg['_source'] = 'chat'
                all_messages.append(msg)
            
            # Add rolls with _source
            for roll in rolls:
                roll['_source'] = 'roll'
                all_messages.append(roll)
            
            # Sort ALL messages by timestamp (newest first)
            all_messages.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            # Take the most recent 'count' messages TOTAL and reverse to chronological order
            combined_messages = list(reversed(all_messages[:count]))
            
            logger.debug(f"Combined {len(messages)} messages and {len(rolls)} rolls for client {client_id}")
            return combined_messages
            
        except MessageValidationException:
            raise  # Re-raise validation exceptions directly
        except Exception as e:
            raise MessageCollectionException(f"Error getting combined messages for client {client_id}: {e}")
    
    def clear_client_data(self, client_id: str) -> bool:
        """
        Clear all data for a specific client
        
        Raises:
            MessageValidationException: When client_id is invalid
            MessageCollectionException: When clearing fails
        """
        try:
            # Validate input
            if not client_id or not isinstance(client_id, str):
                raise MessageValidationException("Client ID must be a non-empty string")
            
            if client_id in self.client_messages:
                del self.client_messages[client_id]
            
            if client_id in self.client_rolls:
                del self.client_rolls[client_id]
            
            # Clear last timestamp tracking for this client
            if client_id in self._last_timestamp:
                del self._last_timestamp[client_id]
            
            logger.debug(f"Cleared all data for client {client_id}")
            return True
            
        except MessageValidationException:
            raise  # Re-raise validation exceptions directly
        except Exception as e:
            raise MessageCollectionException(f"Error clearing client data for {client_id}: {e}")
    
    def _cleanup_client_messages(self, client_id: str):
        """
        Cleanup old messages for a client to prevent memory issues
        """
        try:
            if client_id not in self.client_messages:
                return
            
            messages = self.client_messages[client_id]
            
            # Remove messages older than retention period
            cutoff_time = int(time.time() * 1000) - (self.message_retention_hours * 60 * 60 * 1000)
            
            filtered_messages = [
                msg for msg in messages 
                if msg.get('timestamp', 0) > cutoff_time
            ]
            
            # If still too many messages, keep only most recent
            if len(filtered_messages) > self.max_messages_per_client:
                filtered_messages = sorted(
                    filtered_messages, 
                    key=lambda x: x.get('timestamp', 0), 
                    reverse=True
                )[:self.max_messages_per_client]
            
            self.client_messages[client_id] = filtered_messages
            
        except Exception as e:
            logger.error(f"Error cleaning up messages for client {client_id}: {e}")
    
    def _cleanup_client_rolls(self, client_id: str):
        """
        Cleanup old rolls for a client to prevent memory issues
        """
        try:
            if client_id not in self.client_rolls:
                return
            
            rolls = self.client_rolls[client_id]
            
            # Remove rolls older than retention period
            cutoff_time = int(time.time() * 1000) - (self.message_retention_hours * 60 * 60 * 1000)
            
            filtered_rolls = [
                roll for roll in rolls 
                if roll.get('timestamp', 0) > cutoff_time
            ]
            
            # If still too many rolls, keep only most recent
            if len(filtered_rolls) > self.max_messages_per_client:
                filtered_rolls = sorted(
                    filtered_rolls, 
                    key=lambda x: x.get('timestamp', 0), 
                    reverse=True
                )[:self.max_messages_per_client]
            
            self.client_rolls[client_id] = filtered_rolls
            
        except Exception as e:
            logger.error(f"Error cleaning up rolls for client {client_id}: {e}")
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific client
        
        Raises:
            MessageValidationException: When client_id is invalid
            MessageCollectionException: When stats retrieval fails
        """
        try:
            # Validate input
            if not client_id or not isinstance(client_id, str):
                raise MessageValidationException("Client ID must be a non-empty string")
            
            message_count = len(self.client_messages.get(client_id, []))
            roll_count = len(self.client_rolls.get(client_id, []))
            
            # Get timestamps of newest messages
            newest_message = None
            newest_roll = None
            
            if message_count > 0:
                messages = self.client_messages[client_id]
                newest_message = max(msg.get('timestamp', 0) for msg in messages)
            
            if roll_count > 0:
                rolls = self.client_rolls[client_id]
                newest_roll = max(roll.get('timestamp', 0) for roll in rolls)
            
            return {
                "client_id": client_id,
                "message_count": message_count,
                "roll_count": roll_count,
                "total_items": message_count + roll_count,
                "newest_message_timestamp": newest_message,
                "newest_roll_timestamp": newest_roll,
                "last_activity": max(
                    filter(None, [newest_message, newest_roll]),
                    default=0
                )
            }
            
        except MessageValidationException:
            raise  # Re-raise validation exceptions directly
        except Exception as e:
            raise MessageCollectionException(f"Error getting client stats for {client_id}: {e}")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all clients
        
        Raises:
            MessageCollectionException: When stats retrieval fails
        """
        try:
            all_client_ids = set()
            all_client_ids.update(self.client_messages.keys())
            all_client_ids.update(self.client_rolls.keys())
            
            total_messages = sum(len(msgs) for msgs in self.client_messages.values())
            total_rolls = sum(len(rolls) for rolls in self.client_rolls.values())
            
            return {
                "total_clients": len(all_client_ids),
                "total_messages": total_messages,
                "total_rolls": total_rolls,
                "total_items": total_messages + total_rolls,
                "client_ids": list(all_client_ids),
                "retention_hours": self.message_retention_hours,
                "max_messages_per_client": self.max_messages_per_client
            }
            
        except Exception as e:
            raise MessageCollectionException(f"Error getting all stats: {e}")
    
    def cleanup_all_clients(self) -> int:
        """
        Cleanup old data for all clients
        Returns count of clients that were cleaned up
        
        Raises:
            MessageCollectionException: When cleanup fails
        """
        try:
            cleanup_count = 0
            
            for client_id in list(self.client_messages.keys()):
                old_count = len(self.client_messages[client_id])
                self._cleanup_client_messages(client_id)
                new_count = len(self.client_messages[client_id])
                if new_count < old_count:
                    cleanup_count += 1
            
            for client_id in list(self.client_rolls.keys()):
                old_count = len(self.client_rolls[client_id])
                self._cleanup_client_rolls(client_id)
                new_count = len(self.client_rolls[client_id])
                if new_count < old_count:
                    cleanup_count += 1
            
            logger.info(f"Cleanup completed for {cleanup_count} clients")
            return cleanup_count
            
        except Exception as e:
            raise MessageCollectionException(f"Error during cleanup: {e}")


# Convenience functions that use ServiceRegistry via service factory
def add_client_message(client_id: str, message: Dict[str, Any]) -> bool:
    """Add a message for a client using ServiceRegistry"""
    from ..system_services.service_factory import get_message_collector
    collector = get_message_collector()
    return collector.add_message(client_id, message)

def add_client_roll(client_id: str, roll_data: Dict[str, Any]) -> bool:
    """Add a roll for a client using ServiceRegistry"""
    from ..system_services.service_factory import get_message_collector
    collector = get_message_collector()
    return collector.add_roll(client_id, roll_data)

def get_client_messages(client_id: str, count: int = 15) -> List[Dict[str, Any]]:
    """Get messages for a client using ServiceRegistry"""
    from ..system_services.service_factory import get_message_collector
    collector = get_message_collector()
    return collector.get_messages(client_id, count)

def get_client_rolls(client_id: str, count: int = 15) -> List[Dict[str, Any]]:
    """Get rolls for a client using ServiceRegistry"""
    from ..system_services.service_factory import get_message_collector
    collector = get_message_collector()
    return collector.get_rolls(client_id, count)

def get_combined_client_messages(client_id: str, count: int = 15) -> List[Dict[str, Any]]:
    """Get combined messages and rolls for a client using ServiceRegistry"""
    from ..system_services.service_factory import get_message_collector
    collector = get_message_collector()
    return collector.get_combined_messages(client_id, count)

def clear_client_data(client_id: str) -> bool:
    """Clear all data for a client using ServiceRegistry"""
    from ..system_services.service_factory import get_message_collector
    collector = get_message_collector()
    return collector.clear_client_data(client_id)

def cleanup_all_clients() -> int:
    """Cleanup old data for all clients using ServiceRegistry"""
    from ..system_services.service_factory import get_message_collector
    collector = get_message_collector()
    return collector.cleanup_all_clients()

def get_collector_stats() -> Dict[str, Any]:
    """Get message collector statistics using ServiceRegistry"""
    from ..system_services.service_factory import get_message_collector
    collector = get_message_collector()
    return collector.get_all_stats()
