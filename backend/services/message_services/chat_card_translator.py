"""
Chat Card Translator - Phase 2 Implementation
Handles bidirectional translation of chat cards between HTML and compact JSON

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from bs4 import BeautifulSoup, Tag

from services.message_services.chat_card_translation_cache import ChatCardTranslationCache, get_current_cache
from services.message_services.dynamic_chat_card_analyzer import CardFieldInfo, analyze_chat_card

logger = logging.getLogger(__name__)

class ChatCardTranslator:
    """
    Handles bidirectional translation of chat cards
    Converts raw HTML fields to compact JSON and back
    Integrates with translation cache for code mappings
    """
    
    def __init__(self, cache: Optional[ChatCardTranslationCache] = None):
        """
        Initialize translator
        
        Args:
            cache: Translation cache to use (creates new if None)
        """
        self.logger = logging.getLogger(__name__)
        self.cache = cache or get_current_cache()
        
        # Standard message type codes
        self.message_types = {
            'chat_card': 'cc',
            'chat_message': 'cm', 
            'dice_roll': 'dr'
        }
        
        self.logger.info("ChatCardTranslator initialized")
    
    def html_to_compact(self, html_content: str, card_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert HTML chat card to compact JSON format
        
        Args:
            html_content: Raw HTML from Foundry chat card
            card_type: Optional card type (auto-detected if None)
            
        Returns:
            Compact JSON representation
        """
        try:
            self.logger.debug(f"Converting HTML to compact format")
            
            # Analyze card structure
            analysis = analyze_chat_card(html_content)
            detected_card_type = analysis['card_type']
            fields = analysis['fields']
            
            # Use provided card type or detected type
            target_card_type = card_type or detected_card_type
            
            # Generate or get cached codes
            field_to_code, code_to_field = self.cache.generate_codes(target_card_type, fields)
            
            # Build compact representation
            compact_data = {
                't': self.message_types.get('chat_card', 'cc'),
                'ct': target_card_type,  # card type
                'f': {}  # fields
            }
            
            # Convert fields to compact format
            for field_name, field_info in fields.items():
                if field_name in field_to_code:
                    code = field_to_code[field_name]
                    compact_data['f'][code] = field_info.value
                else:
                    # Fallback: use field name directly if no code generated
                    self.logger.warning(f"No code generated for field '{field_name}', using fallback")
                    compact_data['f'][field_name] = field_info.value
            
            # Add metadata if available
            if analysis.get('metadata'):
                metadata = analysis['metadata']
                if 'title' in metadata:
                    compact_data['n'] = metadata['title']  # name/title
            
            # Add confidence score for debugging
            if analysis.get('confidence_score'):
                compact_data['cs'] = round(analysis['confidence_score'], 2)
            
            self.logger.info(f"Converted {len(fields)} fields to compact format for {target_card_type}")
            return compact_data
            
        except Exception as e:
            self.logger.error(f"Failed to convert HTML to compact format: {e}")
            raise ValueError(f"HTML to compact conversion failed: {e}")
    
    def compact_to_websocket(self, compact_data: Dict[str, Any], card_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Convert compact JSON back to WebSocket message format
        
        Args:
            compact_data: Compact representation from AI
            card_type: Expected card type (extracted from compact_data if None)
            
        Returns:
            WebSocket format message for Foundry
        """
        try:
            self.logger.debug(f"Converting compact to WebSocket format")
            
            # Extract basic information
            message_type = compact_data.get('t', 'cc')
            target_card_type = card_type or compact_data.get('ct', 'unknown-card')
            fields = compact_data.get('f', {})
            
            # Get cached mappings for this card type
            card_mapping = self.cache.get_cached_mapping(target_card_type)
            
            if not card_mapping:
                self.logger.warning(f"No cached mapping for card type '{target_card_type}', using fallback")
                return self._fallback_to_websocket(compact_data)
            
            # Build WebSocket format message
            websocket_data = {
                'type': 'chat_card',
                'cardType': target_card_type,
                'content': {
                    'fields': {}
                }
            }
            
            # Convert compact codes back to field names
            for code, value in fields.items():
                field_name = self.cache.reverse_lookup_code(target_card_type, code)
                
                if field_name:
                    # Found mapping, use it
                    websocket_data['content']['fields'][field_name] = value
                    
                    # Update usage statistics
                    self.cache.update_usage(target_card_type, field_name=field_name)
                else:
                    # No mapping found, treat as direct field name
                    websocket_data['content']['fields'][code] = value
                    self.logger.debug(f"No mapping found for code '{code}' in {target_card_type}")
            
            # Add other metadata
            if 'n' in compact_data:
                websocket_data['content']['name'] = compact_data['n']
            
            if 'ct' in compact_data:
                websocket_data['content']['cardType'] = compact_data['ct']
            
            self.logger.info(f"Converted compact data to WebSocket format for {target_card_type}")
            return websocket_data
            
        except Exception as e:
            self.logger.error(f"Failed to convert compact to WebSocket format: {e}")
            raise ValueError(f"Compact to WebSocket conversion failed: {e}")
    
    def generate_field_documentation(self, card_type: str) -> str:
        """
        Generate field documentation for system prompt
        
        Args:
            card_type: Type of card to document
            
        Returns:
            Formatted documentation string
        """
        card_mapping = self.cache.get_cached_mapping(card_type)
        if not card_mapping:
            return f"# No fields documented for {card_type}"
        
        doc_lines = [f"## {card_type.upper()} Field Mappings"]
        doc_lines.append("")
        
        for field_name, field_mapping in card_mapping.field_mappings.items():
            type_indicator = self._get_type_indicator(field_mapping.field_type)
            doc_lines.append(f"- `{field_mapping.code}`: {field_name} ({type_indicator})")
            
            # Add confidence if low
            if field_mapping.confidence < 0.7:
                doc_lines.append(f"  - Confidence: {field_mapping.confidence:.2f}")
        
        doc_lines.append("")
        return "\n".join(doc_lines)
    
    def translate_chat_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate a regular chat message (not a card)
        
        Args:
            message_data: Chat message data
            
        Returns:
            Compact format
        """
        return {
            't': self.message_types.get('chat_message', 'cm'),
            's': message_data.get('speaker', ''),
            'a': message_data.get('author', ''),
            'c': message_data.get('content', ''),
            'ts': message_data.get('timestamp', '')
        }
    
    def translate_dice_roll(self, roll_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate dice roll data
        
        Args:
            roll_data: Dice roll data
            
        Returns:
            Compact format
        """
        return {
            't': self.message_types.get('dice_roll', 'dr'),
            'ft': roll_data.get('flavor_text', ''),
            'f': roll_data.get('formula', ''),
            'r': roll_data.get('results', []),
            'tt': roll_data.get('total', 0),
            's': roll_data.get('speaker', ''),
            'a': roll_data.get('author', '')
        }
    
    def get_supported_card_types(self) -> List[str]:
        """
        Get list of supported card types
        
        Returns:
            List of card type names
        """
        return list(self.cache.card_mappings.keys())
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get translation cache statistics
        
        Returns:
            Cache statistics dictionary
        """
        return self.cache.get_cache_stats()
    
    def validate_compact_format(self, compact_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate compact format data
        
        Args:
            compact_data: Compact format data to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        if 't' not in compact_data:
            errors.append("Missing message type field 't'")
        
        if 'f' not in compact_data:
            errors.append("Missing fields field 'f'")
        elif not isinstance(compact_data['f'], dict):
            errors.append("Fields field 'f' must be a dictionary")
        
        # Check card type if present
        if 'ct' in compact_data and not isinstance(compact_data['ct'], str):
            errors.append("Card type field 'ct' must be a string")
        
        # Validate field codes
        if 'f' in compact_data and isinstance(compact_data['f'], dict):
            card_type = compact_data.get('ct', 'unknown')
            card_mapping = self.cache.get_cached_mapping(card_type)
            
            if card_mapping:
                for code in compact_data['f'].keys():
                    if code not in card_mapping.reverse_mappings:
                        errors.append(f"Unknown field code '{code}' for card type '{card_type}'")
        
        return len(errors) == 0, errors
    
    def _fallback_to_websocket(self, compact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback conversion when no cached mapping is available
        
        Args:
            compact_data: Compact data to convert
            
        Returns:
            WebSocket format with minimal conversion
        """
        self.logger.warning("Using fallback conversion for compact data")
        
        websocket_data = {
            'type': 'chat_card',
            'cardType': compact_data.get('ct', 'unknown-card'),
            'content': {
                'fields': compact_data.get('f', {})
            }
        }
        
        # Add name if present
        if 'n' in compact_data:
            websocket_data['content']['name'] = compact_data['n']
        
        return websocket_data
    
    def _get_type_indicator(self, field_type: str) -> str:
        """
        Get type indicator for documentation
        
        Args:
            field_type: Type of field
            
        Returns:
            Type indicator string
        """
        type_indicators = {
            'text': 'text',
            'number': 'number',
            'boolean': 'boolean',
            'array': 'array',
            'object': 'object',
            'unknown': 'unknown'
        }
        return type_indicators.get(field_type, 'unknown')

# Global translator instance
_translator: Optional[ChatCardTranslator] = None

def get_translator() -> ChatCardTranslator:
    """Get the global translator instance"""
    global _translator
    if _translator is None:
        _translator = ChatCardTranslator()
    return _translator

def reset_translator():
    """Reset the global translator for new session"""
    global _translator
    _translator = None
    return get_translator()

def translate_html_to_compact(html_content: str, card_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to translate HTML to compact format
    
    Args:
        html_content: Raw HTML from Foundry chat card
        card_type: Optional card type
        
    Returns:
        Compact JSON representation
    """
    translator = get_translator()
    return translator.html_to_compact(html_content, card_type)

def translate_compact_to_websocket(compact_data: Dict[str, Any], card_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to translate compact to WebSocket format
    
    Args:
        compact_data: Compact representation from AI
        card_type: Optional card type
        
    Returns:
        WebSocket format message
    """
    translator = get_translator()
    return translator.compact_to_websocket(compact_data, card_type)
