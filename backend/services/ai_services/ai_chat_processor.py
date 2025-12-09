"""
AI Chat Processor for The Gold Box v0.3.0
Converts AI responses to Foundry REST API format
"""

import json
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AIChatProcessor:
    """Convert AI responses to Foundry REST API format"""
    
    def __init__(self):
        self.reverse_type_codes = {
            "cm": "chat-message",
            "dr": "dice-roll", 
            "wp": "whisper",
            "gm": "gm-message",
            "cd": "card"
        }
    
    def process_ai_response(self, ai_response: str, context: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert AI response to Foundry REST API format
        
        Args:
            ai_response: Raw AI response string
            context: Original message context for reference
            
        Returns:
            Formatted message ready for Foundry REST API
        """
        try:
            # Try to parse compact JSON from AI response
            compact_messages = self._extract_compact_json(ai_response)
            
            if compact_messages:
                # Convert compact JSON to API format
                api_messages = []
                for compact_msg in compact_messages:
                    api_msg = self._convert_compact_to_api(compact_msg)
                    if api_msg:
                        api_messages.append(api_msg)
                
                return {
                    "type": "multi-message",
                    "messages": api_messages,
                    "success": True
                }
            else:
                # No compact JSON found, treat as simple chat message
                return {
                    "type": "chat-message",
                    "content": ai_response,
                    "author": {
                        "name": "The Gold Box AI",
                        "role": "assistant"
                    },
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }
                
        except Exception as e:
            logger.error(f"Failed to process AI response: {e}")
            return {
                "type": "chat-message",
                "content": ai_response,
                "author": {
                    "name": "The Gold Box AI",
                    "role": "assistant"
                },
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "error": f"Processing error: {e}"
            }
    
    def _extract_compact_json(self, text: str) -> List[Dict[str, Any]]:
        """Extract compact JSON objects from AI response text"""
        import re
        
        # Handle multiple JSON objects that might be concatenated
        # Pattern matches complete JSON objects
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*|[^\{}])*\}'
        json_matches = re.findall(json_pattern, text, re.DOTALL)
        
        compact_messages = []
        for json_str in json_matches:
            try:
                # Clean up the JSON string
                cleaned_json = json_str.strip()
                compact_msg = json.loads(cleaned_json)
                
                # Validate that this looks like our compact format
                if "t" in compact_msg:
                    compact_messages.append(compact_msg)
                    logger.debug(f"Successfully parsed compact message: {compact_msg}")
                else:
                    logger.debug(f"Skipping non-compact JSON: {compact_msg}")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {json_str}, error: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error processing JSON: {json_str}, error: {e}")
                continue
        
        # If no valid compact messages found, log the original text for debugging
        if not compact_messages:
            logger.debug(f"No valid compact JSON found in AI response. Original text: {text[:200]}...")
        
        return compact_messages
    
    def _convert_compact_to_api(self, compact_msg: Dict[str, Any]) -> Dict[str, Any]:
        """Convert compact message to Foundry REST API format"""
        msg_type = compact_msg.get("t", "")
        
        if msg_type not in self.reverse_type_codes:
            return None
        
        api_msg = {
            "type": self.reverse_type_codes[msg_type],
            "timestamp": datetime.now().isoformat()
        }
        
        # Handle common fields
        if "s" in compact_msg:
            api_msg["author"] = {"name": compact_msg["s"]}
        
        if "c" in compact_msg:
            api_msg["content"] = compact_msg["c"]
        
        # Handle specific message types
        if msg_type == "dr":  # dice roll
            api_msg["roll"] = self._expand_dice_roll(compact_msg)
        elif msg_type == "wp":  # whisper
            if "tg" in compact_msg:
                api_msg["whisperTo"] = compact_msg["tg"]
        
        return api_msg
    
    def _expand_dice_roll(self, compact_roll: Dict[str, Any]) -> Dict[str, Any]:
        """Expand compact dice roll to full API format"""
        expanded = {}
        
        if "f" in compact_roll:
            expanded["formula"] = compact_roll["f"]
        
        if "r" in compact_roll:
            expanded["result"] = compact_roll["r"]
        
        if "tt" in compact_roll:
            expanded["total"] = compact_roll["tt"]
        
        return expanded
