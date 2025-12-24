#!/usr/bin/env python3
"""
Message Delta Service for The Gold Box
Filters messages to only include new messages since last AI call

Works with AI Session Manager to provide context delta filtering:
- Gets last message timestamp for session
- Filters messages to only newer ones
- Updates session timestamp with newest message

Always gathers fresh context from existing message collectors,
just applies intelligent filtering to reduce token usage.
"""

import logging
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MessageDeltaService:
    """
    Service for applying message delta filtering to AI contexts
    
    Integrates with AI Session Manager to:
    1. Get last message timestamp for session
    2. Filter messages to only include new ones
    3. Update session timestamp with newest message
    """
    
    def __init__(self, ai_session_manager=None):
        """
        Initialize message delta service
        
        Args:
            ai_session_manager: AISessionManager instance (injected for testing)
        """
        if ai_session_manager is None:
            from ..ai_services.ai_session_manager import get_ai_session_manager
            self.ai_session_manager = get_ai_session_manager()
        else:
            self.ai_session_manager = ai_session_manager
        
        logger.info("MessageDeltaService initialized with AI session manager integration")
    
    def get_enhanced_context(self, session_id: str, new_messages: List[Dict[str, Any]], 
                           max_history_messages: Optional[int] = None, 
                           max_history_hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get enhanced context combining conversation history with new delta-filtered messages
        
        Args:
            session_id: Session identifier for history tracking
            new_messages: List of new messages to apply delta filtering to
            max_history_messages: Maximum history messages to include (None for default)
            max_history_hours: Maximum age in hours for history messages (None for default)
            
        Returns:
            Combined context with conversation history + new messages
        """
        if not new_messages:
            logger.debug(f"No new messages for session {session_id}, returning conversation history only")
            return self.ai_session_manager.get_conversation_history(
                session_id, max_messages=max_history_messages, max_hours=max_history_hours
            )
        
        # Ensure auto-cleanup happens
        self.ai_session_manager.auto_cleanup()
        
        # Get conversation history
        conversation_history = self.ai_session_manager.get_conversation_history(
            session_id, max_messages=max_history_messages, max_hours=max_history_hours
        )
        
        # Apply delta filtering to new messages
        delta_filtered_messages = self.apply_message_delta(session_id, new_messages)
        
        # Combine conversation history with new messages
        full_context = conversation_history + delta_filtered_messages
        
        logger.info(f"Session {session_id} enhanced context: {len(conversation_history)} history + {len(delta_filtered_messages)} new = {len(full_context)} total messages")
        
        return full_context
    
    def apply_message_delta(self, session_id: str, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply delta filtering to messages based on session timestamps
        
        Args:
            session_id: Session identifier for timestamp tracking
            messages: List of messages to filter (chronological order preferred)
            
        Returns:
            Filtered list containing only new messages since last AI call
        """
        if not messages:
            logger.debug(f"No messages to filter for session {session_id}")
            return []
        
        # Ensure auto-cleanup happens
        self.ai_session_manager.auto_cleanup()
        
        # Get last message timestamp for session
        last_timestamp = self.ai_session_manager.get_session_timestamp(session_id)
        
        if last_timestamp is None:
            # New session - return all messages and save newest timestamp
            newest_timestamp = self._get_newest_message_timestamp(messages)
            if newest_timestamp is not None:
                success = self.ai_session_manager.update_session_timestamp(session_id, newest_timestamp)
                if success:
                    logger.info(f"New session {session_id} - sending {len(messages)} messages, saved timestamp {newest_timestamp}")
                else:
                    logger.warning(f"Failed to save timestamp for new session {session_id}")
            else:
                logger.warning(f"No valid timestamps found in messages for new session {session_id}")
            
            return messages
        
        # Normalize stored timestamp to milliseconds for comparison
        # (it might be stored in seconds if from older code)
        normalized_last_timestamp = self._normalize_timestamp(last_timestamp)
        
        # Filter messages newer than stored timestamp (normalize both for comparison)
        new_messages = []
        for msg in messages:
            # Check both 'ts' (compact format) and 'timestamp' (legacy format) fields
            msg_timestamp = msg.get('ts') or msg.get('timestamp')
            if msg_timestamp is not None:
                normalized_timestamp = self._normalize_timestamp(msg_timestamp)
                # Use >= instead of > to exclude messages with same timestamp as last AI response
                if normalized_timestamp is not None and normalized_last_timestamp is not None and normalized_timestamp > normalized_last_timestamp:
                    new_messages.append(msg)
            else:
                # Include messages without timestamps (they're always considered "new")
                new_messages.append(msg)
        
        # Note: Timestamp should only be updated when AI responses are stored in AI service
        # NOT when user messages come in via delta filtering
        # This prevents overwriting AI response timestamp with newer user message timestamp
        logger.debug(f"Session {session_id}: {len(new_messages)}/{len(messages)} new messages since timestamp {last_timestamp}")
        
        return new_messages
    
    def get_delta_stats(self, session_id: str, original_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about delta filtering for debugging/monitoring
        
        Args:
            session_id: Session identifier
            original_messages: Original message list before filtering
            
        Returns:
            Dictionary with delta statistics
        """
        if not original_messages:
            return {
                'session_id': session_id,
                'original_count': 0,
                'filtered_count': 0,
                'delta_ratio': 0.0,
                'has_timestamp_data': False
            }
        
        # Get session timestamp for comparison
        last_timestamp = self.ai_session_manager.get_session_timestamp(session_id)
        
        if last_timestamp is None:
            # New session - all messages are "new"
            return {
                'session_id': session_id,
                'original_count': len(original_messages),
                'filtered_count': len(original_messages),
                'delta_ratio': 1.0,
                'has_timestamp_data': False,
                'is_new_session': True
            }
        
        # Normalize stored timestamp to milliseconds for comparison
        normalized_last_timestamp = self._normalize_timestamp(last_timestamp)
        
        # Count messages newer than timestamp (using normalized timestamps)
        new_count = 0
        for msg in original_messages:
            # Check both 'ts' (compact format) and 'timestamp' (legacy format) fields
            msg_timestamp = msg.get('ts') or msg.get('timestamp')
            if msg_timestamp is not None:
                normalized_timestamp = self._normalize_timestamp(msg_timestamp)
                if normalized_timestamp is not None and normalized_last_timestamp is not None and normalized_timestamp > normalized_last_timestamp:
                    new_count += 1
            else:
                # Messages without timestamps are always considered "new"
                new_count += 1
        
        delta_ratio = new_count / len(original_messages) if original_messages else 0.0
        
        return {
            'session_id': session_id,
            'original_count': len(original_messages),
            'filtered_count': new_count,
            'delta_ratio': delta_ratio,
            'has_timestamp_data': True,
            'is_new_session': False,
            'last_timestamp': last_timestamp
        }
    
    def force_full_context(self, session_id: str) -> bool:
        """
        Force next AI call to use full context by clearing session timestamp
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False if session not found
        """
        success = self.ai_session_manager.clear_session_timestamp(session_id)
        if success:
            logger.info(f"Forced full context for session {session_id} - timestamp cleared")
        else:
            logger.warning(f"Failed to clear timestamp for session {session_id}")
        
        return success
    
    def _get_newest_message_timestamp(self, messages: List[Dict[str, Any]]) -> Optional[int]:
        """
        Get the timestamp of the newest message in the list
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Newest timestamp or None if no valid timestamps found
        """
        if not messages:
            return None
        
        # Extract and normalize timestamps
        normalized_timestamps = []
        for msg in messages:
            # Check both 'ts' (compact format) and 'timestamp' (legacy format) fields
            timestamp = msg.get('ts') or msg.get('timestamp')
            if timestamp is not None:
                # Convert timestamp to milliseconds (Unix epoch in milliseconds)
                normalized = self._normalize_timestamp(timestamp)
                if normalized is not None:
                    normalized_timestamps.append(normalized)
        
        if not normalized_timestamps:
            return None
        
        return max(normalized_timestamps)
    
    def _normalize_timestamp(self, timestamp) -> Optional[int]:
        """
        Normalize timestamp to milliseconds since Unix epoch
        
        Args:
            timestamp: Timestamp in various formats (microseconds, milliseconds, seconds)
            
        Returns:
            Normalized timestamp in milliseconds or None if invalid
        """
        try:
            # Convert to int if it's a string
            if isinstance(timestamp, str):
                timestamp = int(timestamp)
            
            # Check if timestamp is in microseconds (very large number, > 10^15)
            # Unix timestamps in microseconds would be > 10^15 (year 1970+)
            if timestamp > 10**15:  # 1 quadrillion = year 1970 in microseconds
                # Convert from microseconds to milliseconds
                normalized = timestamp // 1000
                logger.debug(f"Converted microsecond timestamp {timestamp} to millisecond timestamp {normalized}")
                return normalized
            
            # Check if timestamp is in seconds (reasonable range for seconds, < 10^12)
            # Unix timestamps in seconds would be around 10^9 (year 2001+) to 10^11 (year 5138)
            elif timestamp < 10**12:  # 1 trillion = year 2001 in milliseconds
                # Convert from seconds to milliseconds
                normalized = timestamp * 1000
                logger.debug(f"Converted second timestamp {timestamp} to millisecond timestamp {normalized}")
                return normalized
            
            # Assume timestamp is already in milliseconds
            else:
                logger.debug(f"Using millisecond timestamp {timestamp} as-is")
                return timestamp
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to normalize timestamp {timestamp}: {e}")
            return None
    
    def validate_message_timestamps(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate and analyze timestamp data in messages
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Validation result with statistics
        """
        if not messages:
            return {
                'total_messages': 0,
                'messages_with_timestamps': 0,
                'messages_without_timestamps': 0,
                'oldest_timestamp': None,
                'newest_timestamp': None,
                'has_valid_timestamps': False
            }
        
        messages_with_timestamps = 0
        messages_without_timestamps = 0
        timestamps = []
        
        for msg in messages:
            if msg.get('timestamp') is not None:
                messages_with_timestamps += 1
                timestamps.append(msg['timestamp'])
            else:
                messages_without_timestamps += 1
        
        has_valid_timestamps = len(timestamps) > 0
        oldest_timestamp = min(timestamps) if timestamps else None
        newest_timestamp = max(timestamps) if timestamps else None
        
        return {
            'total_messages': len(messages),
            'messages_with_timestamps': messages_with_timestamps,
            'messages_without_timestamps': messages_without_timestamps,
            'oldest_timestamp': oldest_timestamp,
            'newest_timestamp': newest_timestamp,
            'has_valid_timestamps': has_valid_timestamps
        }


# Global instance for application-wide use
_message_delta_service = None

def get_message_delta_service() -> MessageDeltaService:
    """
    Get the global message delta service instance
    
    Returns:
        MessageDeltaService instance
    """
    global _message_delta_service
    if _message_delta_service is None:
        _message_delta_service = MessageDeltaService()
    return _message_delta_service

def reset_message_delta_service() -> MessageDeltaService:
    """
    Reset the global message delta service (for testing)
    
    Returns:
        New MessageDeltaService instance
    """
    global _message_delta_service
    _message_delta_service = MessageDeltaService()
    return _message_delta_service
