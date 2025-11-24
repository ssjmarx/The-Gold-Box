"""
API Chat Processor for Gold Box v0.3.0
Converts REST API chat data to compact JSON format for AI processing
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class APIChatProcessor:
    """Convert Foundry REST API chat data to token-efficient compact format"""
    
    def __init__(self):
        self.type_codes = {
            "chat-message": "cm",
            "dice-roll": "dr", 
            "whisper": "wp",
            "gm-message": "gm",
            "card": "cd"
        }
    
    def process_api_messages(self, api_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Foundry REST API chat messages to compact JSON format
        
        Args:
            api_messages: List of chat messages from Foundry REST API
            
        Returns:
            List of compact JSON messages for AI processing
        """
        compact_messages = []
        
        for msg in api_messages:
            try:
                compact_msg = self._convert_to_compact(msg)
                if compact_msg:
                    compact_messages.append(compact_msg)
            except Exception as e:
                logger.warning(f"Failed to process message {msg.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(compact_messages)} messages from API data")
        return compact_messages
    
    def _convert_to_compact(self, api_message: Dict[str, Any]) -> Dict[str, Any]:
        """Convert single API message to compact format"""
        # Determine message type
        msg_type = self._detect_message_type(api_message)
        
        if msg_type not in self.type_codes:
            return None  # Skip unsupported message types
        
        compact_msg = {"t": self.type_codes[msg_type]}
        
        # Extract common fields
        if "content" in api_message:
            compact_msg["c"] = api_message["content"]
        
        if "author" in api_message:
            compact_msg["s"] = api_message["author"]["name"] if isinstance(api_message["author"], dict) else api_message["author"]
        
        if "timestamp" in api_message:
            compact_msg["ts"] = api_message["timestamp"]
        
        # Handle specific message types
        if msg_type == "dice-roll" and "roll" in api_message:
            compact_msg.update(self._process_dice_roll(api_message["roll"]))
        
        elif msg_type == "whisper" and "whisperTo" in api_message:
            compact_msg["tg"] = api_message["whisperTo"]
        
        return compact_msg
    
    def _detect_message_type(self, api_message: Dict[str, Any]) -> str:
        """Detect message type from API message structure"""
        if "roll" in api_message:
            return "dice-roll"
        elif "whisperTo" in api_message:
            return "whisper"
        elif "author" in api_message and api_message.get("author", {}).get("role") == "gm":
            return "gm-message"
        elif "card" in api_message:
            return "card"
        else:
            return "chat-message"
    
    def _process_dice_roll(self, roll_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process dice roll data into compact format"""
        compact_roll = {}
        
        if "formula" in roll_data:
            compact_roll["f"] = roll_data["formula"]
        
        if "result" in roll_data:
            compact_roll["r"] = roll_data["result"]
        
        if "total" in roll_data:
            compact_roll["tt"] = roll_data["total"]
        
        return compact_roll
