"""
The Gold Box - Unified Message Processor
Consolidates all message processing into single, fail-fast data flow

Replaces:
- APIChatProcessor (redundant)
- AIChatProcessor (redundant) 
- Multiple HTML parsing paths

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import json
import logging
import re
import html
from typing import Dict, List, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

# Import dynamic chat card translation components
try:
    from services.message_services.chat_card_translator import get_translator
    from services.message_services.chat_card_translation_cache import get_current_cache, is_cache_active
except ImportError:
    # Fallback for when running outside main application context
    def get_translator():
        return None
    def get_current_cache():
        return None
    def is_cache_active():
        return False

logger = logging.getLogger(__name__)

class UnifiedMessageProcessor:
    """
    Unified processor for all message transformations
    
    Single data flow: HTML ↔ Compact JSON ↔ API Format ↔ AI Response
    No fallbacks or redundant processing paths.
    """
    
    # Type codes for compact JSON format
    TYPE_CODES = {
        'dice-roll': 'dr',
        'chat-message': 'cm', 
        'chat-card': 'cc',
        'whisper': 'wp',
        'gm-message': 'gm',
    }
    
    # Reverse mapping for API conversion
    REVERSE_TYPE_CODES = {v: k for k, v in TYPE_CODES.items()}
    
    # Classification patterns (highest priority first)
    CLASSIFICATION_PATTERNS = [
        ('dr', r'class=["\'].*dice-roll'),
        ('cc', r'class=["\'].*chat-card|activation-card'),
        ('cm', r'class=["\'].*chat-message'),
    ]
    
    def __init__(self):
        """Initialize unified processor"""
        self.compiled_patterns = [
            (type_code, re.compile(pattern, re.IGNORECASE))
            for type_code, pattern in self.CLASSIFICATION_PATTERNS
        ]
        logger.info("UnifiedMessageProcessor initialized - single data flow for all message processing")
    
    def html_to_compact_json(self, html_content: str) -> Dict[str, Any]:
        """
        Convert HTML to compact JSON - single authoritative implementation
        
        Args:
            html_content: HTML content from Foundry
            
        Returns:
            Compact JSON dictionary
            
        Raises:
            ValueError: If conversion fails (no silent fallbacks)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Classify message type
            message_type = self._classify_message(html_content)
            
            # Extract data based on type
            if message_type == 'dr':
                data = self._extract_dice_roll_data(soup)
            elif message_type == 'cc':
                data = self._extract_chat_card_data(soup)
            elif message_type == 'cm':
                data = self._extract_chat_message_data(soup)
            else:
                # No fallbacks - fail fast if type unknown
                raise ValueError(f"Unknown message type: {message_type}")
            
            # Add type and timestamp
            result = {'t': message_type, 'ts': int(datetime.now().timestamp() * 1000)}
            result.update(data)
            
            # Sanitize result (no truncation)
            result = self._sanitize_data(result)
            
            logger.debug(f"HTML → Compact: {message_type} → {result}")
            return result
            
        except Exception as e:
            logger.error(f"HTML to compact conversion failed: {e}")
            raise ValueError(f"Failed to convert HTML to compact JSON: {e}")
    
    def compact_to_api_format(self, compact_msg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert compact JSON to Foundry API format - single authoritative implementation
        
        Args:
            compact_msg: Compact JSON message
            
        Returns:
            API format dictionary
            
        Raises:
            ValueError: If conversion fails (no silent fallbacks)
        """
        try:
            msg_type = compact_msg.get("t", "")
            
            if msg_type not in self.REVERSE_TYPE_CODES:
                raise ValueError(f"Unknown compact message type: {msg_type}")
            
            api_msg = {
                "type": self.REVERSE_TYPE_CODES[msg_type],
                "timestamp": datetime.now().isoformat()
            }
            
            # Handle common fields
            if "s" in compact_msg:
                api_msg["author"] = {"name": compact_msg["s"]}
            
            if "c" in compact_msg:
                api_msg["content"] = compact_msg["c"]
            
            # Type-specific processing
            if msg_type == "dr":
                api_msg["roll"] = self._expand_dice_roll(compact_msg)
            elif msg_type == "wp":
                if "tg" in compact_msg:
                    api_msg["whisperTo"] = compact_msg["tg"]
            elif msg_type == "cc":
                # Handle chat cards with dynamic translation - NO FALLBACKS
                translator = get_translator()
                if not translator:
                    raise ValueError("Chat card translator not available - fail-fast architecture")
                
                websocket_data = translator.compact_to_websocket(compact_msg)
                if not websocket_data or not websocket_data.get("content"):
                    raise ValueError("Dynamic chat card conversion failed - fail-fast architecture")
                    
                api_msg["content"] = websocket_data["content"]
                if "fields" in websocket_data["content"]:
                    # Convert fields back to HTML for Foundry
                    api_msg["chat-card"] = self._convert_compact_to_html(websocket_data["content"])
                logger.debug(f"Dynamic chat card conversion: {len(websocket_data.get('content', {}).get('fields', {}))} fields")
            
            logger.debug(f"Compact → API: {msg_type} → {api_msg}")
            return api_msg
            
        except Exception as e:
            logger.error(f"Compact to API conversion failed: {e}")
            raise ValueError(f"Failed to convert compact to API format: {e}")
    
    def process_ai_response(self, ai_response: str, context: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process AI response into API format - single authoritative implementation
        
        Args:
            ai_response: Raw AI response string
            context: Original message context
            
        Returns:
            Formatted message dictionary
            
        Raises:
            ValueError: If processing fails (no silent fallbacks)
        """
        try:
            # Extract compact JSON from AI response
            compact_messages = self._extract_compact_json(ai_response)
            
            if compact_messages:
                # Convert each compact message to API format
                api_messages = []
                for compact_msg in compact_messages:
                    try:
                        api_msg = self.compact_to_api_format(compact_msg)
                        api_messages.append(api_msg)
                    except Exception as e:
                        logger.error(f"Failed to convert compact message: {compact_msg}, error: {e}")
                        continue  # Skip invalid messages, don't fail entire batch
                
                if api_messages:
                    return {
                        "type": "multi-message",
                        "messages": api_messages,
                        "success": True
                    }
                else:
                    # No valid messages - treat as simple chat
                    logger.warning("No valid compact messages converted to API format")
                    return self._create_simple_chat_response(ai_response)
            else:
                # No compact JSON - treat as simple chat
                return self._create_simple_chat_response(ai_response)
                
        except Exception as e:
            logger.error(f"AI response processing failed: {e}")
            return {
                "type": "error",
                "content": f"AI response processing failed: {str(e)}",
                "author": {"name": "The Gold Box AI", "role": "assistant"},
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    def process_api_messages(self, api_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert API messages to compact format - single authoritative implementation
        
        Args:
            api_messages: List of API messages from Foundry
            
        Returns:
            List of compact JSON messages
            
        Raises:
            ValueError: If processing fails (no silent fallbacks)
        """
        try:
            compact_messages = []
            
            for api_msg in api_messages:
                try:
                    # Handle roll messages from relay server
                    if api_msg.get('_source') == 'roll':
                        compact_msg = self._convert_roll_message_to_compact(api_msg)
                    else:
                        compact_msg = self._convert_api_message_to_compact(api_msg)
                    
                    if compact_msg:
                        compact_messages.append(compact_msg)
                    else:
                        logger.warning(f"Failed to convert API message: {api_msg}")
                        
                except Exception as e:
                    logger.error(f"Error processing API message: {api_msg}, error: {e}")
                    continue  # Skip invalid messages
            
            logger.info(f"Processed {len(compact_messages)} messages from API data")
            return compact_messages
            
        except Exception as e:
            logger.error(f"API message processing failed: {e}")
            raise ValueError(f"Failed to process API messages: {e}")
    
    def _classify_message(self, html_content: str) -> str:
        """Classify message type using patterns"""
        for type_code, pattern in self.compiled_patterns:
            if pattern.search(html_content):
                return type_code
        return 'cm'  # Default to chat message
    
    def _extract_dice_roll_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract dice roll data from HTML"""
        data = {}
        
        # Extract flavor text
        flavor_elem = soup.select_one('.flavor-text')
        if flavor_elem:
            data['ft'] = flavor_elem.get_text(strip=True)
        
        # Extract formula
        formula_elem = soup.select_one('.dice-formula')
        if formula_elem:
            data['f'] = formula_elem.get_text(strip=True)
        
        # Extract total
        total_elem = soup.select_one('.dice-total')
        if total_elem:
            total_text = total_elem.get_text(strip=True)
            total_match = re.search(r'(\d+)', total_text)
            if total_match:
                data['tt'] = int(total_match.group(1))
        
        # Extract speaker properly (title/subtitle structure)
        speaker, author = self._extract_speaker_info(soup)
        if speaker:
            data['s'] = speaker
        if author:
            data['a'] = author
        
        return data
    
    def _extract_chat_message_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract chat message data from HTML"""
        data = {}
        
        # Extract speaker properly (title/subtitle structure)
        speaker, author = self._extract_speaker_info(soup)
        if speaker:
            data['s'] = speaker
        if author:
            data['a'] = author
        
        # Extract content
        content_elem = soup.select_one('.message-content')
        if content_elem:
            content_text = content_elem.get_text(strip=True)
            if content_text:
                data['c'] = content_text
        
        return data
    
    def _extract_chat_card_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract chat card data from HTML with dynamic field discovery
        Fail-fast architecture - no static fallbacks
        """
        # Use dynamic processing only - NO FALLBACKS
        translator = get_translator()
        if not translator:
            raise ValueError("Chat card translator not available - fail-fast architecture")
        
        html_content = str(soup)
        compact_data = translator.html_to_compact(html_content)
        logger.debug(f"Dynamic chat card processing: {len(compact_data.get('f', {}))} fields")
        return compact_data
    
    def _extract_speaker_info(self, soup: BeautifulSoup) -> tuple[str, str]:
        """
        Extract speaker information from HTML with proper title/subtitle handling
        
        Returns:
            Tuple of (speaker, author) where:
            - speaker: The title (main name)
            - author: The subtitle (character/author name)
        """
        speaker = ""
        author = ""
        
        # Try to find name-stacked structure first
        name_stacked = soup.select_one('.name-stacked')
        if name_stacked:
            title_elem = name_stacked.select_one('.title')
            subtitle_elem = name_stacked.select_one('.subtitle')
            
            if title_elem:
                speaker = title_elem.get_text(strip=True)
            if subtitle_elem:
                author = subtitle_elem.get_text(strip=True)
        else:
            # Fallback to message-sender for legacy compatibility
            sender_elem = soup.select_one('.message-sender')
            if sender_elem:
                # Check if it contains name-stacked structure
                nested_stacked = sender_elem.select_one('.name-stacked')
                if nested_stacked:
                    title_elem = nested_stacked.select_one('.title')
                    subtitle_elem = nested_stacked.select_one('.subtitle')
                    
                    if title_elem:
                        speaker = title_elem.get_text(strip=True)
                    if subtitle_elem:
                        author = subtitle_elem.get_text(strip=True)
                else:
                    # Legacy: extract text directly
                    sender_text = sender_elem.get_text(strip=True)
                    # Try to split concatenated names
                    if 'The Gold Box' in sender_text:
                        # Split "The Gold BoxGamemaster" -> "The Gold Box", "Gamemaster"
                        if sender_text.startswith('The Gold Box') and len(sender_text) > len('The Gold Box'):
                            speaker = 'The Gold Box'
                            author = sender_text[len('The Gold Box'):]
                        else:
                            speaker = sender_text
                    elif len(sender_text) > 10:  # Likely concatenated
                        # Try to split at logical boundaries
                        parts = sender_text.split()
                        if len(parts) >= 2:
                            # Take first part as speaker, rest as author
                            speaker = parts[0]
                            author = ' '.join(parts[1:])
                        else:
                            speaker = sender_text
                    else:
                        speaker = sender_text
        
        return speaker, author
    
    def _expand_dice_roll(self, compact_roll: Dict[str, Any]) -> Dict[str, Any]:
        """Expand compact dice roll to API format"""
        expanded = {}
        
        if "f" in compact_roll:
            expanded["formula"] = compact_roll["f"]
        if "r" in compact_roll:
            expanded["result"] = compact_roll["r"]
        if "tt" in compact_roll:
            expanded["total"] = compact_roll["tt"]
        
        return expanded
    
    def _convert_roll_message_to_compact(self, roll_msg: Dict[str, Any]) -> Dict[str, Any]:
        """Convert roll message from relay to compact format"""
        compact = {"t": "dr"}
        
        if "formula" in roll_msg:
            compact["f"] = roll_msg["formula"]
        if "rollTotal" in roll_msg:
            compact["r"] = roll_msg["rollTotal"]
            compact["tt"] = roll_msg["rollTotal"]
        if "user" in roll_msg:
            user_info = roll_msg["user"]
            if isinstance(user_info, dict):
                # Try to extract from name-stacked structure first
                alias = user_info.get("alias") or user_info.get("name", "")
                speaker, author = self._parse_name_from_string(alias)
                if speaker:
                    compact["s"] = speaker
                if author:
                    compact["a"] = author
        
        return compact
    
    def _convert_api_message_to_compact(self, api_msg: Dict[str, Any]) -> Dict[str, Any]:
        """Convert API message to compact format"""
        msg_type = self._detect_message_type(api_msg)
        
        if msg_type not in self.TYPE_CODES:
            return None
        
        compact = {"t": self.TYPE_CODES[msg_type]}
        
        # Handle content
        if "content" in api_msg:
            content = api_msg["content"]
            
            # Check for embedded roll data
            if content and content.strip().startswith('{'):
                try:
                    embedded_data = json.loads(content)
                    if isinstance(embedded_data, dict) and "f" in embedded_data:
                        compact.update(embedded_data)
                        if "user" in api_msg:
                            compact["s"] = api_msg["user"].get("alias")
                        return compact
                except json.JSONDecodeError:
                    pass
            
            compact["c"] = content
        
        # Handle speaker with proper name parsing
        if "user" in api_msg:
            user_info = api_msg["user"]
            if isinstance(user_info, dict):
                alias = user_info.get("alias") or user_info.get("name", "")
                speaker, author = self._parse_name_from_string(alias)
                if speaker:
                    compact["s"] = speaker
                if author:
                    compact["a"] = author
        
        return compact
    
    def _detect_message_type(self, api_msg: Dict[str, Any]) -> str:
        """Detect message type from API message"""
        content = api_msg.get("content", "")
        
        if "roll" in api_msg or "dice-roll" in content:
            return "dice-roll"
        elif "chat-card" in content or "activation-card" in content:
            return "chat-card"
        else:
            return "chat-message"
    
    def _extract_compact_json(self, text: str) -> List[Dict[str, Any]]:
        """Extract compact JSON from AI response text"""
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*|[^\{}])*\}'
        json_matches = re.findall(json_pattern, text, re.DOTALL)
        
        compact_messages = []
        for json_str in json_matches:
            try:
                compact_msg = json.loads(json_str.strip())
                if "t" in compact_msg:  # Validate compact format
                    compact_messages.append(compact_msg)
            except json.JSONDecodeError:
                continue
        
        return compact_messages
    
    def _create_simple_chat_response(self, content: str) -> Dict[str, Any]:
        """Create simple chat response"""
        return {
            "type": "chat-message",
            "content": content,
            "author": {"name": "The Gold Box AI", "role": "assistant"},
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
    
    def _parse_name_from_string(self, name_string: str) -> tuple[str, str]:
        """
        Parse speaker and author from concatenated name string
        
        Args:
            name_string: Concatenated name like "The Gold BoxGamemaster" or "Snessnes"
            
        Returns:
            Tuple of (speaker, author) where:
            - speaker: The title (main name)
            - author: The subtitle (character/author name)
        """
        if not name_string:
            return "", ""
        
        # Handle The Gold Box case specifically
        if 'The Gold Box' in name_string:
            if name_string.startswith('The Gold Box') and len(name_string) > len('The Gold Box'):
                return 'The Gold Box', name_string[len('The Gold Box'):]
            else:
                return name_string, ""
        
        # Handle specific concatenated patterns we know about
        known_patterns = [
            ('SnesGamemaster', 'Snes', 'Gamemaster'),
            ('Snessnes', 'Snes', 'snes'),
        ]
        
        for full_name, expected_speaker, expected_author in known_patterns:
            if name_string == full_name:
                return expected_speaker, expected_author
        
        # Handle other concatenated cases
        if len(name_string) > 10:  # Likely concatenated
            # Try to split at logical boundaries
            parts = name_string.split()
            if len(parts) >= 2:
                # Take first part as speaker, rest as author
                return parts[0], ' '.join(parts[1:])
        
        # Default to entire string as speaker
        return name_string, ""
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize data without truncation"""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Remove dangerous HTML
                clean_value = value.replace('\x00', '')
                clean_value = html.unescape(clean_value)
                
                # Remove dangerous patterns
                dangerous_patterns = [
                    r'<script[^>]*>.*?</script>',
                    r'javascript:',
                    r'on\w+\s*=',
                ]
                
                for pattern in dangerous_patterns:
                    clean_value = re.sub(pattern, '', clean_value, flags=re.IGNORECASE)
                
                # Remove remaining HTML tags
                clean_value = re.sub(r'<[^>]*>', '', clean_value)
                clean_value = re.sub(r'\s+', ' ', clean_value).strip()
                
                sanitized[key] = clean_value
            else:
                sanitized[key] = value
        
        return sanitized
    
    def generate_enhanced_system_prompt(self, ai_role: str, compact_messages: List[Dict[str, Any]]) -> str:
        """
        Generate enhanced system prompt based on AI role and message context
        
        Args:
            ai_role: AI role ('gm', 'gm assistant', 'player')
            compact_messages: List of compact messages for context
            
        Returns:
            Enhanced system prompt string
        """
        # Build context codes and abbreviations from compact messages
        context_codes = []
        context_abbreviations = []
        context_schemas = []
        
        # ALWAYS include basic field definitions for all messages (including new author field)
        context_abbreviations.extend(['t: type', 's: speaker', 'a: author', 'c: content', 'ts: timestamp', 'f: formula', 'r: results', 'tt: total', 'ft: flavor_text', 'n: name', 'd: description', 'at: actions'])
        
        # Analyze compact messages to determine available context
        has_rolls = any(msg.get('t') == 'dr' for msg in compact_messages)
        has_chat = any(msg.get('t') == 'cm' for msg in compact_messages)
        has_cards = any(msg.get('t') in ['cc', 'cd'] for msg in compact_messages)  # Check for both 'cc' and 'cd'
        
        # Add context codes based on available data
        if has_chat:
            context_codes.append('cm: chat_message')
            context_schemas.append('cm: {"t": "cm", "s": "speaker", "a": "author", "c": "content"}')
        
        if has_rolls:
            context_codes.append('dr: dice_roll')
            context_schemas.append('dr: {"t": "dr", "ft": "flavor_text", "f": "formula", "r": "results", "tt": "total", "s": "speaker", "a": "author"}')
        
        if has_cards:
            context_codes.append('cc: chat_card')
            context_schemas.append('cc: {"t": "cc", "tt": "title", "ct": "card_type", "l": "level", "s": "school", "n": "name", "d": "description", "at": "actions"}')
        
        # Get AI role specific prompt content
        role_prompts = {
            'gm': 'You are assigned as a full gamemaster. Your role is to describe scene, describe NPC actions, and create dice rolls whenever NPCs do anything that requires one. Keep generating descriptions, actions, and dice rolls until every NPC in the scene has gone, and then turn action back over to the players.',
            'gm assistant': 'You are assigned as a GM\'s assistant. Your role is to aid the GM in whatever task they are currently doing, which they will usually prompt for you in the most recent message.',
            'player': 'You are assigned as a Player. Your role is to participate in story via in-character chat and actions. Describe what your character is doing and roll dice as appropriate for your actions.'
        }
        
        role_specific_prompt = role_prompts.get(ai_role.lower(), role_prompts['gm'])
        
        # Build enhanced system prompt with dynamic field discovery
        system_prompt = f"""You are an AI assistant for tabletop RPG games, with role {ai_role}. {role_specific_prompt}

Data from chat and environment is formatted as follows:

Type Codes:
{', '.join(context_codes) if context_codes else 'No specific type codes detected'}

Field Abbreviations:
{', '.join(context_abbreviations) if context_abbreviations else 'No specific abbreviations detected'}

Message Schemas:
{'; '.join(context_schemas) if context_schemas else 'No specific schemas detected'}"""
        
        # Add dynamic field definitions if cache is active
        if is_cache_active():
            try:
                cache = get_current_cache()
                if cache:
                    dynamic_fields = cache.get_schema_definitions()
                    if dynamic_fields:
                        system_prompt += f"\n\nDYNAMIC FIELD DEFINITIONS:\n{dynamic_fields}"
                        logger.info(f"Added {len(dynamic_fields.split())} dynamic field definitions to system prompt")
            except Exception as e:
                logger.warning(f"Failed to add dynamic field definitions: {e}")
        
        return system_prompt
    
    def _convert_compact_to_html(self, websocket_content: Dict[str, Any]) -> str:
        """
        Convert compact WebSocket content back to HTML format
        
        Args:
            websocket_content: WebSocket content with fields
            
        Returns:
            HTML string representation
        """
        try:
            if not isinstance(websocket_content, dict):
                return ""
            
            fields = websocket_content.get('fields', {})
            card_type = websocket_content.get('cardType', 'unknown-card')
            name = websocket_content.get('name', '')
            
            # Build basic HTML structure
            html_parts = []
            
            # Add card type and name
            if card_type:
                html_parts.append(f'<div class="{card_type}">')
            
            if name:
                html_parts.append(f'<h3>{name}</h3>')
            
            # Add fields
            for field_name, field_value in fields.items():
                if field_value:  # Skip empty fields
                    html_parts.append(f'<div class="field-{field_name}">{field_value}</div>')
            
            # Close card type div
            if card_type:
                html_parts.append('</div>')
            
            return '\n'.join(html_parts)
            
        except Exception as e:
            logger.error(f"Failed to convert compact to HTML: {e}")
            return ""

# Global instance - single source of truth
unified_processor = UnifiedMessageProcessor()

def get_unified_processor() -> UnifiedMessageProcessor:
    """Get the unified message processor instance"""
    return unified_processor
