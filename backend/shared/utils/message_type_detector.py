"""
Message Type Detector - Unified message type detection and classification
Eliminates redundant message type detection logic across services
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from shared.exceptions import MessageValidationException


class MessageType(Enum):
    """Standardized message types"""
    CHAT = "chat"
    DICE = "dice"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class MessageDetector:
    """
    Unified message type detection and classification
    Single source of truth for message type logic
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Define detection patterns for different message types
        self._dice_indicators = [
            'roll', 'dice', 'd20', 'd6', 'd8', 'd10', 'd12', 'd100',
            'damage', 'attack', 'skill check', 'saving throw', 'ability check'
        ]
        
        self._system_indicators = [
            'system', 'server', 'admin', 'broadcast', 'announcement'
        ]
    
    def detect_message_type(self, message: Dict[str, Any]) -> MessageType:
        """
        Detect the type of a message using unified logic
        
        Args:
            message: Message dictionary to classify
            
        Returns:
            MessageType enum value
            
        Raises:
            MessageValidationException: When message is invalid
        """
        if not message or not isinstance(message, dict):
            raise MessageValidationException("Message must be a non-empty dictionary")
        
        # Check explicit type field first
        explicit_type = message.get('type') or message.get('message_type')
        if explicit_type:
            return self._normalize_type(explicit_type)
        
        # Check for dice-specific fields
        if self._has_dice_fields(message):
            return MessageType.DICE
        
        # Check content-based detection
        content = self._extract_content(message)
        if content:
            content_lower = content.lower()
            
            if self._contains_dice_indicators(content_lower):
                return MessageType.DICE
            
            if self._contains_system_indicators(content_lower):
                return MessageType.SYSTEM
        
        # Default to chat
        return MessageType.CHAT
    
    def _normalize_type(self, type_str: str) -> MessageType:
        """
        Normalize explicit type to MessageType enum
        
        Args:
            type_str: String type from message
            
        Returns:
            MessageType enum value
        """
        if not type_str or not isinstance(type_str, str):
            return MessageType.UNKNOWN
        
        type_lower = type_str.lower().strip()
        
        type_mapping = {
            'chat': MessageType.CHAT,
            'message': MessageType.CHAT,
            'text': MessageType.CHAT,
            'dice': MessageType.DICE,
            'roll': MessageType.DICE,
            'rolling': MessageType.DICE,
            'system': MessageType.SYSTEM,
            'server': MessageType.SYSTEM,
            'admin': MessageType.SYSTEM,
            'broadcast': MessageType.SYSTEM,
            'announcement': MessageType.SYSTEM
        }
        
        return type_mapping.get(type_lower, MessageType.UNKNOWN)
    
    def _has_dice_fields(self, message: Dict[str, Any]) -> bool:
        """
        Check if message has dice-specific fields
        
        Args:
            message: Message dictionary
            
        Returns:
            True if dice fields are present
        """
        dice_fields = [
            'roll', 'dice', 'result', 'total', 'formula', 
            'critical', 'fumble', 'success', 'flavor'
        ]
        
        return any(field in message for field in dice_fields)
    
    def _extract_content(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Extract text content from message
        
        Args:
            message: Message dictionary
            
        Returns:
            Content string or None
        """
        content_fields = ['content', 'text', 'message', 'roll', 'flavor']
        
        for field in content_fields:
            if field in message:
                value = message[field]
                if isinstance(value, str) and value.strip():
                    return value.strip()
        
        return None
    
    def _contains_dice_indicators(self, content: str) -> bool:
        """
        Check if content contains dice-related indicators
        
        Args:
            content: Lowercase content string
            
        Returns:
            True if dice indicators are found
        """
        return any(indicator in content for indicator in self._dice_indicators)
    
    def _contains_system_indicators(self, content: str) -> bool:
        """
        Check if content contains system-related indicators
        
        Args:
            content: Lowercase content string
            
        Returns:
            True if system indicators are found
        """
        return any(indicator in content for indicator in self._system_indicators)
    
    def is_dice_message(self, message: Dict[str, Any]) -> bool:
        """
        Quick check if message is a dice message
        
        Args:
            message: Message dictionary
            
        Returns:
            True if message is dice type
        """
        try:
            return self.detect_message_type(message) == MessageType.DICE
        except MessageValidationException:
            return False
    
    def is_chat_message(self, message: Dict[str, Any]) -> bool:
        """
        Quick check if message is a chat message
        
        Args:
            message: Message dictionary
            
        Returns:
            True if message is chat type
        """
        try:
            return self.detect_message_type(message) == MessageType.CHAT
        except MessageValidationException:
            return False
    
    def classify_messages(self, messages: List[Dict[str, Any]]) -> Dict[MessageType, List[Dict[str, Any]]]:
        """
        Classify a list of messages by type
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dictionary mapping MessageType to list of messages
            
        Raises:
            MessageValidationException: When any message is invalid
        """
        if not messages:
            return {msg_type: [] for msg_type in MessageType}
        
        classified = {msg_type: [] for msg_type in MessageType}
        
        for message in messages:
            if not message or not isinstance(message, dict):
                raise MessageValidationException("All messages must be non-empty dictionaries")
            
            try:
                msg_type = self.detect_message_type(message)
                classified[msg_type].append(message)
            except MessageValidationException:
                # Add to unknown category if detection fails
                classified[MessageType.UNKNOWN].append(message)
        
        return classified
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about message detection
        
        Returns:
            Dictionary with detection configuration
        """
        return {
            'dice_indicators': self._dice_indicators,
            'system_indicators': self._system_indicators,
            'supported_types': [t.value for t in MessageType]
        }


# Global detector instance for convenience
_detector = MessageDetector()


def detect_message_type(message: Dict[str, Any]) -> MessageType:
    """
    Convenience function for message type detection
    
    Args:
        message: Message dictionary to classify
        
    Returns:
        MessageType enum value
    """
    return _detector.detect_message_type(message)


def is_dice_message(message: Dict[str, Any]) -> bool:
    """
    Convenience function to check if message is dice
    
    Args:
        message: Message dictionary
        
    Returns:
        True if message is dice type
    """
    return _detector.is_dice_message(message)


def is_chat_message(message: Dict[str, Any]) -> bool:
    """
    Convenience function to check if message is chat
    
    Args:
        message: Message dictionary
        
    Returns:
        True if message is chat type
    """
    return _detector.is_chat_message(message)


def classify_messages(messages: List[Dict[str, Any]]) -> Dict[MessageType, List[Dict[str, Any]]]:
    """
    Convenience function to classify messages
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Dictionary mapping MessageType to list of messages
    """
    return _detector.classify_messages(messages)
