"""
API Chat Processor for Gold Box v0.3.0
Converts REST API chat data to compact JSON format for AI processing
"""

import json
import logging
import re
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
            "card": "cd",
            "roll": "rl",
            "damage": "dm"
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
        
        # Handle roll messages from relay server (highest priority)
        if msg_type == "dice-roll" and api_message.get('_source') == 'roll':
            return self._convert_roll_message_to_compact(api_message)
        
        # Extract common fields
        if "content" in api_message:
            content = api_message["content"]
            # Check if content contains embedded roll data (JSON format)
            if content and content.strip().startswith('{') and content.strip().endswith('}'):
                try:
                    # Try to parse as JSON for embedded roll data
                    import json
                    embedded_data = json.loads(content)
                    if isinstance(embedded_data, dict) and any(key in embedded_data for key in ["f", "r", "tt", "crit", "fumble", "dice"]):
                        # This is embedded roll data, extract it
                        if "f" in embedded_data:
                            compact_msg["f"] = embedded_data["f"]
                        if "r" in embedded_data or "rollTotal" in embedded_data:
                            result = embedded_data.get("r") or embedded_data.get("rollTotal")
                            compact_msg["r"] = result
                            compact_msg["tt"] = result
                        if "tt" in embedded_data:
                            compact_msg["tt"] = embedded_data["tt"]
                        if "crit" in embedded_data:
                            compact_msg["crit"] = embedded_data["crit"]
                        if "fumble" in embedded_data:
                            compact_msg["fumble"] = embedded_data["fumble"]
                        if "dice" in embedded_data:
                            compact_msg["dice"] = embedded_data["dice"]
                        if "fl" in embedded_data:
                            compact_msg["fl"] = embedded_data["fl"]
                        # Extract speaker if present in embedded data
                        if "s" in embedded_data:
                            compact_msg["s"] = embedded_data["s"]
                        logger.info(f"DEBUG: Extracted embedded roll data from content: {embedded_data}")
                        return compact_msg
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning(f"DEBUG: Failed to parse embedded roll data from content: {e}")
                    # Fall through to normal processing if JSON parsing fails
            # For card messages, extract structured data
            if msg_type in ["card", "activation-card"]:
                structured_data = self._extract_structured_data(content, msg_type)
                if structured_data:
                    # Create compact card with extracted data at top level
                    compact_msg["tt"] = structured_data.get("title", "")
                    compact_msg["st"] = structured_data.get("subtitle", "")
                    if "buttons" in structured_data:
                        compact_msg["btn"] = structured_data["buttons"]
                    if "pills" in structured_data:
                        compact_msg["pl"] = structured_data["pills"]
                    # Don't store raw content - cards should be fully structured
                else:
                    # Fallback to raw content if extraction fails
                    compact_msg["c"] = content
            else:
                compact_msg["c"] = content
        
        # Extract speaker information (priority: user.alias > user.name > user.id)
        if "user" in api_message:
            user_info = api_message["user"]
            if isinstance(user_info, dict):
                speaker = user_info.get("alias") or user_info.get("name") or user_info.get("id")
            else:
                speaker = str(user_info)
            compact_msg["s"] = speaker
        
        # Extract speaker from dedicated speaker field if available
        elif "speaker" in api_message:
            speaker_info = api_message["speaker"]
            if isinstance(speaker_info, dict):
                # Priority: alias > scene/actor > token > name > id
                speaker = (speaker_info.get("alias") or 
                         speaker_info.get("actor") or 
                         speaker_info.get("token") or 
                         speaker_info.get("name") or 
                         str(speaker_info.get("id")))
            else:
                speaker = str(speaker_info)
            compact_msg["s"] = speaker
        
        # Fallback speaker extraction
        elif "user" not in api_message and "speaker" not in api_message:
            # Try to extract from content for some message types
            content = api_message.get("content", "")
            if "Gamemaster" in content:
                compact_msg["s"] = "Gamemaster"
            elif "snes" in content:
                compact_msg["s"] = "snes"
        
        if "timestamp" in api_message:
            compact_msg["ts"] = api_message["timestamp"]
        
        # Handle specific message types
        if msg_type == "dice-roll":
            # Try to extract roll data from HTML content if no structured roll data
            if "roll" in api_message:
                compact_msg.update(self._process_dice_roll(api_message["roll"]))
            else:
                # Extract roll data from HTML content
                roll_data = self._extract_structured_data(api_message.get("content", ""), msg_type)
                if roll_data:
                    compact_msg.update(roll_data)
                    # Don't store raw HTML if we have extracted roll data
                else:
                    # Check for embedded roll data in JSON format within content
                    content = api_message.get("content", "")
                    if content and content.strip().startswith('{') and content.strip().endswith('}'):
                        try:
                            import json
                            embedded_data = json.loads(content)
                            if isinstance(embedded_data, dict) and any(key in embedded_data for key in ["f", "r", "tt", "crit", "fumble", "dice"]):
                                # This is embedded roll data, extract it
                                if "f" in embedded_data:
                                    compact_msg["f"] = embedded_data["f"]
                                if "r" in embedded_data or "rollTotal" in embedded_data:
                                    result = embedded_data.get("r") or embedded_data.get("rollTotal")
                                    compact_msg["r"] = result
                                    compact_msg["tt"] = result
                                if "tt" in embedded_data:
                                    compact_msg["tt"] = embedded_data["tt"]
                                if "crit" in embedded_data:
                                    compact_msg["crit"] = embedded_data["crit"]
                                if "fumble" in embedded_data:
                                    compact_msg["fumble"] = embedded_data["fumble"]
                                if "dice" in embedded_data:
                                    compact_msg["dice"] = embedded_data["dice"]
                                if "fl" in embedded_data:
                                    compact_msg["fl"] = embedded_data["fl"]
                                # Extract speaker if present in embedded data
                                if "s" in embedded_data:
                                    compact_msg["s"] = embedded_data["s"]
                                logger.info(f"DEBUG: Extracted embedded roll data from content: {embedded_data}")
                                return compact_msg
                        except (json.JSONDecodeError, Exception) as e:
                            logger.warning(f"DEBUG: Failed to parse embedded roll data from content: {e}")
                    # Keep as dice-roll type but with processed content
                    compact_msg["c"] = api_message.get("content", "")
        
        elif msg_type == "whisper" and "whisperTo" in api_message:
            compact_msg["tg"] = api_message["whisperTo"]
        
        return compact_msg
    
    def _convert_roll_message_to_compact(self, roll_message: Dict[str, Any]) -> Dict[str, Any]:
        """Convert roll message from relay server to compact format"""
        compact_msg = {"t": "dr"}  # dice-roll type
        
        # Extract roll formula
        if "formula" in roll_message:
            compact_msg["f"] = roll_message["formula"]
        
        # Extract roll result
        if "rollTotal" in roll_message:
            compact_msg["r"] = roll_message["rollTotal"]
            compact_msg["tt"] = roll_message["rollTotal"]  # Also store as total for consistency
        elif "total" in roll_message:
            compact_msg["r"] = roll_message["total"]
            compact_msg["tt"] = roll_message["total"]
        
        # Extract speaker information
        if "user" in roll_message:
            user_info = roll_message["user"]
            if isinstance(user_info, dict):
                speaker = user_info.get("alias") or user_info.get("name") or user_info.get("id")
            else:
                speaker = str(user_info)
            compact_msg["s"] = speaker
        elif "speaker" in roll_message:
            speaker_info = roll_message["speaker"]
            if isinstance(speaker_info, dict):
                # Priority: alias > scene/actor > token > name > id
                speaker = (speaker_info.get("alias") or 
                         speaker_info.get("actor") or 
                         speaker_info.get("token") or 
                         speaker_info.get("name") or 
                         str(speaker_info.get("id")))
            else:
                speaker = str(speaker_info)
            compact_msg["s"] = speaker
        
        # Extract timestamp
        if "timestamp" in roll_message:
            compact_msg["ts"] = roll_message["timestamp"]
        
        # Extract additional roll information
        if "isCritical" in roll_message:
            compact_msg["crit"] = roll_message["isCritical"]
        
        if "isFumble" in roll_message:
            compact_msg["fumble"] = roll_message["isFumble"]
        
        # Extract dice details if available
        if "dice" in roll_message:
            dice_info = roll_message["dice"]
            if isinstance(dice_info, list) and len(dice_info) > 0:
                # Extract key dice information for AI context
                compact_dice = []
                for die in dice_info:
                    die_info = {}
                    if "faces" in die:
                        die_info["f"] = die["faces"]
                    if "results" in die:
                        die_info["r"] = [r.get("result", r.get("active", 0)) for r in die["results"]]
                    compact_dice.append(die_info)
                compact_msg["dice"] = compact_dice
        
        # Extract flavor text if available
        if "flavor" in roll_message:
            compact_msg["fl"] = roll_message["flavor"]
        
        return compact_msg
    
    def _detect_message_type(self, api_message: Dict[str, Any]) -> str:
        """Detect message type from API message structure with enhanced type detection"""
        
        # Check if this is a roll message from the relay server (highest priority)
        if api_message.get('_source') == 'roll':
            return "dice-roll"
        
        content = api_message.get("content", "")
        
        # Check for CARDS FIRST (highest priority) - cards can contain roll indicators
        if ("chat-card" in content or 
            "activation-card" in content or
            "item-card" in content):
            return "card"
        
        # Check for actual dice rolls SECONDARY
        if ("roll-result" in content or 
            "dice-roll" in content or
            re.search(r'\b\d+d\d+\b', content)):  # Regex for dice notation like 1d20, 2d6
            return "dice-roll"
        
        # Check for inline rolls within cards (but still cards)
        if ("inline-roll" in content and "chat-card" in content):
            return "card"
        
        # Check for structured data
        if "roll" in api_message:
            return "dice-roll"
        elif "whisperTo" in api_message:
            return "whisper"
        elif "author" in api_message and api_message.get("author", {}).get("role") == "gm":
            return "gm-message"
        elif "card" in api_message:
            return "card"
        
        # Check HTML content for message type indicators
        if "chat-damage" in content:
            return "damage"
        
        return "chat-message"
    
    def _extract_structured_data(self, content: str, message_type: str) -> Dict[str, Any]:
        """Extract structured data from HTML content based on message type"""
        structured_data = {}
        
        if message_type == "card":
            structured_data = self._extract_card_data(content)
        elif message_type == "roll":
            structured_data = self._extract_roll_data(content)
        elif message_type == "damage":
            structured_data = self._extract_damage_data(content)
        
        return structured_data
        
    def _extract_card_data(self, content: str) -> Dict[str, Any]:
        """Extract structured data from chat card HTML"""
        structured_data = {}
        
        # Extract card title
        title_match = re.search(r'<span class="title"[^>]*>([^<]+)</span>', content, re.IGNORECASE)
        if title_match:
            structured_data["title"] = title_match.group(1).strip()
        
        # Extract card subtitle
        subtitle_match = re.search(r'<span class="subtitle"[^>]*>([^<]+)</span>', content, re.IGNORECASE)
        if subtitle_match:
            structured_data["subtitle"] = subtitle_match.group(1).strip()
        
        # Extract card icon
        icon_match = re.search(r'<img[^>]*src="([^"]+)"', content, re.IGNORECASE)
        if icon_match:
            structured_data["icon"] = icon_match.group(1)
        
        # Extract action buttons
        button_matches = re.findall(r'<button[^>]*data-action="([^"]+)"', content, re.IGNORECASE)
        if button_matches:
            structured_data["buttons"] = button_matches
        
        # Extract pill data
        pill_matches = re.findall(r'<li[^>]*>([^<]+)</li>', content, re.IGNORECASE)
        if pill_matches:
            structured_data["pills"] = pill_matches
        
        return structured_data
    
    def _extract_roll_data(self, content: str) -> Dict[str, Any]:
        """Extract structured data from roll HTML"""
        structured_data = {}
        
        # Extract roll formula
        formula_match = re.search(r'data-formula="([^"]+)"', content, re.IGNORECASE)
        if formula_match:
            structured_data["f"] = formula_match.group(1)
        
        # Extract roll result from various patterns
        result_patterns = [
            r'<a[^>]*class="roll-link"[^>]*>([^<]+)</a>',  # Standard roll link
            r'data-tooltip-text="([^"]+)"',  # Tooltip text
            r'<strong>(\d+)</strong>',  # Strong/bold numbers
            r'= (\d+)',  # Simple = numbers
        ]
        
        for pattern in result_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                structured_data["r"] = match.group(1)
                break
        
        # Extract roll total if present
        total_match = re.search(r'data-total="([^"]+)"', content, re.IGNORECASE)
        if total_match:
            structured_data["tt"] = int(total_match.group(1))
        
        return structured_data
    
    def _extract_damage_data(self, content: str) -> Dict[str, Any]:
        """Extract structured data from damage roll HTML"""
        structured_data = {}
        
        # Extract damage amount
        damage_match = re.search(r'(\d+)\s*<span[^>]*class="damage"[^>]*>(\d+)</span>', content, re.IGNORECASE)
        if damage_match:
            structured_data["damage"] = damage_match.group(2)
        else:
            # Fallback: just find numbers in damage spans
            damage_match = re.search(r'<span[^>]*damage[^>]*>(\d+)</span>', content, re.IGNORECASE)
            if damage_match:
                structured_data["damage"] = damage_match.group(1)
        
        # Extract damage type
        type_match = re.search(r'data-damage-types="([^"]+)"', content, re.IGNORECASE)
        if type_match:
            structured_data["damageType"] = type_match.group(1)
        
        return structured_data
    
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
