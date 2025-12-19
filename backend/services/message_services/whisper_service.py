#!/usr/bin/env python3
"""
Whisper Service for The Gold Box
Handles GM whisper creation and delivery for AI thinking

License: CC-BY-NC-SA 4.0
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class WhisperService:
    """
    Service for creating and managing GM whispers
    Handles AI thinking extraction and delivery to Foundry
    """
    
    def __init__(self):
        """Initialize whisper service"""
        self.whisper_history: list[Dict[str, Any]] = []
        self.max_whisper_history = 50
        
        logger.info("WhisperService initialized")
    
    def create_thinking_whisper(self, thinking: str, original_prompt: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a GM whisper for AI thinking
        
        Args:
            thinking: AI thinking content
            original_prompt: Original prompt that generated the thinking
            metadata: Additional metadata for the whisper
            
        Returns:
            Formatted whisper dictionary
        """
        try:
            # Format thinking content
            formatted_thinking = self._format_thinking_content(thinking)
            
            # Create whisper message
            whisper = {
                "type": "gm_whisper",
                "content": formatted_thinking,
                "sender": "AI Assistant",
                "timestamp": int(time.time() * 1000),
                "metadata": {
                    "is_thinking": True,
                    "original_prompt": original_prompt,
                    "whisper_type": "ai_thinking",
                    **(metadata or {})
                }
            }
            
            # Add to history
            self.whisper_history.append(whisper)
            if len(self.whisper_history) > self.max_whisper_history:
                self.whisper_history = self.whisper_history[-self.max_whisper_history:]
            
            logger.debug(f"Created thinking whisper: {len(thinking)} characters")
            return whisper
            
        except Exception as e:
            logger.error(f"Error creating thinking whisper: {e}")
            return self._create_error_whisper("Failed to create thinking whisper")
    
    def create_system_whisper(self, message: str, whisper_type: str = "system") -> Dict[str, Any]:
        """
        Create a system GM whisper
        
        Args:
            message: System message content
            whisper_type: Type of system whisper
            
        Returns:
            Formatted whisper dictionary
        """
        try:
            whisper = {
                "type": "gm_whisper",
                "content": message,
                "sender": "System",
                "timestamp": int(time.time() * 1000),
                "metadata": {
                    "is_thinking": False,
                    "whisper_type": whisper_type,
                    "system_message": True
                }
            }
            
            # Add to history
            self.whisper_history.append(whisper)
            if len(self.whisper_history) > self.max_whisper_history:
                self.whisper_history = self.whisper_history[-self.max_whisper_history:]
            
            logger.debug(f"Created system whisper: {whisper_type}")
            return whisper
            
        except Exception as e:
            logger.error(f"Error creating system whisper: {e}")
            return self._create_error_whisper("Failed to create system whisper")
    
    def extract_ai_thinking(self, ai_response: Dict[str, Any], response_object: Any = None) -> str:
        """
        Extract thinking content from AI response
        
        Args:
            ai_response: AI response dictionary
            response_object: Raw response object from LiteLLM
            
        Returns:
            Extracted thinking content or empty string
        """
        try:
            thinking = ""
            
            # Extract from different response formats
            if response_object:
                # Try different attributes that might contain thinking
                if hasattr(response_object, 'reasoning_content'):
                    thinking = response_object.reasoning_content
                elif hasattr(response_object, 'thinking'):
                    thinking = response_object.thinking
                elif hasattr(response_object, 'chain_of_thought'):
                    thinking = response_object.chain_of_thought
                
                # Check message object
                if hasattr(response_object, 'choices') and response_object.choices:
                    choice = response_object.choices[0]
                    if hasattr(choice, 'message') and choice.message:
                        if hasattr(choice.message, 'reasoning_content'):
                            thinking = choice.message.reasoning_content
                        elif hasattr(choice.message, 'thinking'):
                            thinking = choice.message.thinking
            
            # Check response metadata
            if not thinking and 'metadata' in ai_response:
                metadata = ai_response['metadata']
                if 'thinking' in metadata:
                    thinking = metadata['thinking']
                elif 'reasoning' in metadata:
                    thinking = metadata['reasoning']
            
            # Check response data directly
            if not thinking and 'thinking' in ai_response:
                thinking = ai_response['thinking']
            elif not thinking and 'reasoning_content' in ai_response:
                thinking = ai_response['reasoning_content']
            
            # Clean up thinking content
            if thinking:
                thinking = str(thinking).strip()
                if thinking.lower().startswith('thinking:'):
                    thinking = thinking[9:].strip()
            
            logger.debug(f"Extracted thinking: {len(thinking)} characters" if thinking else "No thinking found")
            return thinking
            
        except Exception as e:
            logger.error(f"Error extracting AI thinking: {e}")
            return ""
    
    def format_whisper_for_foundry(self, whisper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format whisper for Foundry consumption
        
        Args:
            whisper: Whisper dictionary
            
        Returns:
            Foundry-compatible message dictionary
        """
        try:
            return {
                "type": "whisper",
                "content": whisper["content"],
                "sender": whisper["sender"],
                "timestamp": whisper["timestamp"],
                "whisper_to": "gm",  # Send to GM only
                "style": "thinking" if whisper["metadata"].get("is_thinking", False) else "system",
                "metadata": whisper["metadata"]
            }
            
        except Exception as e:
            logger.error(f"Error formatting whisper for Foundry: {e}")
            return self._create_error_foundry_message()
    
    def get_whisper_history(self, limit: int = 20) -> list[Dict[str, Any]]:
        """
        Get recent whisper history
        
        Args:
            limit: Maximum number of whispers to return
            
        Returns:
            List of recent whispers
        """
        return self.whisper_history[-limit:] if len(self.whisper_history) > limit else self.whisper_history
    
    def clear_whisper_history(self) -> bool:
        """
        Clear whisper history
        
        Returns:
            True if cleared successfully
        """
        try:
            self.whisper_history.clear()
            logger.info("Whisper history cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing whisper history: {e}")
            return False
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get service statistics
        
        Returns:
            Service statistics dictionary
        """
        return {
            "total_whispers": len(self.whisper_history),
            "max_whisper_history": self.max_whisper_history,
            "service_active": True,
            "last_whisper_timestamp": self.whisper_history[-1]["timestamp"] if self.whisper_history else None
        }
    
    def _format_thinking_content(self, thinking: str) -> str:
        """
        Format thinking content for GM whisper
        
        Args:
            thinking: Raw thinking content
            
        Returns:
            Formatted thinking string
        """
        if not thinking or not thinking.strip():
            return "Thinking: No thinking content available"
        
        # Clean up the thinking content
        thinking = thinking.strip()
        
        # Add prefix if not already present
        if not thinking.lower().startswith('thinking:'):
            thinking = f"Thinking: {thinking}"
        
        # Add visual separation
        if len(thinking) > 100:
            thinking = f"{thinking}\n---"
        
        return thinking
    
    def _create_error_whisper(self, error_message: str) -> Dict[str, Any]:
        """
        Create an error whisper
        
        Args:
            error_message: Error message
            
        Returns:
            Error whisper dictionary
        """
        return {
            "type": "gm_whisper",
            "content": f"Error: {error_message}",
            "sender": "System",
            "timestamp": int(time.time() * 1000),
            "metadata": {
                "is_thinking": False,
                "whisper_type": "error",
                "system_message": True,
                "error": True
            }
        }
    
    def _create_error_foundry_message(self) -> Dict[str, Any]:
        """
        Create an error message for Foundry
        
        Returns:
            Error message dictionary
        """
        return {
            "type": "whisper",
            "content": "Error: Failed to format whisper message",
            "sender": "System",
            "timestamp": int(time.time() * 1000),
            "whisper_to": "gm",
            "style": "error",
            "metadata": {
                "error": True,
                "system_message": True
            }
        }

# Global instance
whisper_service = WhisperService()

def get_whisper_service() -> WhisperService:
    """Get the whisper service instance"""
    return whisper_service

def create_thinking_whisper(thinking: str, original_prompt: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a GM whisper for AI thinking
    
    Args:
        thinking: AI thinking content
        original_prompt: Original prompt that generated the thinking
        metadata: Additional metadata
        
    Returns:
        Formatted whisper dictionary
    """
    return whisper_service.create_thinking_whisper(thinking, original_prompt, metadata)

def create_system_whisper(message: str, whisper_type: str = "system") -> Dict[str, Any]:
    """
    Create a system GM whisper
    
    Args:
        message: System message content
        whisper_type: Type of system whisper
        
    Returns:
        Formatted whisper dictionary
    """
    return whisper_service.create_system_whisper(message, whisper_type)

def extract_ai_thinking(ai_response: Dict[str, Any], response_object: Any = None) -> str:
    """
    Extract thinking content from AI response
    
    Args:
        ai_response: AI response dictionary
        response_object: Raw response object from LiteLLM
        
    Returns:
        Extracted thinking content
    """
    return whisper_service.extract_ai_thinking(ai_response, response_object)

def format_whisper_for_foundry(whisper: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format whisper for Foundry consumption
    
    Args:
        whisper: Whisper dictionary
        
    Returns:
        Foundry-compatible message dictionary
    """
    return whisper_service.format_whisper_for_foundry(whisper)
