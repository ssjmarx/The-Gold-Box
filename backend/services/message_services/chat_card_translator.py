"""
Chat Card Translator - Phase 2 Implementation
Handles bidirectional translation of chat cards between HTML and compact JSON

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import defaultdict
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
    
    def detect_and_consolidate_patterns(self, compact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect numbered patterns in field codes and consolidate them into arrays
        
        Args:
            compact_data: Compact data with fields to process
            
        Returns:
            Updated compact data with consolidated patterns
        """
        if 'f' not in compact_data:
            return compact_data
        
        fields = compact_data['f']
        if not isinstance(fields, dict):
            return compact_data
        
        # Pattern to detect numbered field codes: base_name + number
        numbered_pattern = re.compile(r'^([a-zA-Z_]+)(\d+)$')
        
        # Group fields by base name
        pattern_groups = defaultdict(list)
        non_pattern_fields = {}
        
        for code, value in fields.items():
            match = numbered_pattern.match(code)
            if match:
                base_name = match.group(1)
                number = int(match.group(2))
                pattern_groups[base_name].append((number, code, value))
            else:
                # Keep non-pattern fields as-is
                non_pattern_fields[code] = value
        
        # Process each pattern group
        consolidated_fields = dict(non_pattern_fields)
        
        for base_name, items in pattern_groups.items():
            # Sort by number to ensure correct order
            items.sort(key=lambda x: x[0])
            
            # Consolidate ALL numbered fields into one array (no sequential requirement)
            if len(items) > 1:
                # Create array field
                array_values = [item[2] for item in items]
                consolidated_fields[f"{base_name}_array"] = array_values
                
                self.logger.debug(f"Consolidated {len(items)} {base_name} fields into array")
            else:
                # Keep original field if only one item
                for _, original_code, value in items:
                    consolidated_fields[original_code] = value
        
        # Return updated compact data
        result = compact_data.copy()
        result['f'] = consolidated_fields
        return result
    
    def detect_and_abbreviate_duplicates(self, message_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Detect duplicate values across cards and replace with abbreviations
        
        Args:
            message_data: List of compact card data
            
        Returns:
            Tuple of (updated_cards, value_dictionary)
        """
        if not message_data:
            return message_data, {}
        
        # Count occurrences of each value across all cards
        value_counts = defaultdict(int)
        value_locations = []  # Track where each value appears
        
        for card_idx, card in enumerate(message_data):
            if 'f' not in card or not isinstance(card['f'], dict):
                continue
                
            for code, value in card['f'].items():
                # Convert value to hashable form for counting
                value_key = self._make_value_hashable(value)
                value_counts[value_key] += 1
                value_locations.append((card_idx, code, value_key, value))
        
        # Find values that appear more than once
        duplicate_values = {k: v for k, v in value_counts.items() if v > 1}
        
        if not duplicate_values:
            return message_data, {}
        
        # Assign abbreviations to duplicate values
        value_dict = {}
        abbreviation_counter = 1
        
        for value_key, count in duplicate_values.items():
            if count > 1:
                abbreviation = f"@v{abbreviation_counter}"
                # Find the actual value for this key
                for _, _, _, actual_value in value_locations:
                    if self._make_value_hashable(actual_value) == value_key:
                        value_dict[abbreviation] = actual_value
                        break
                abbreviation_counter += 1
        
        # Create reverse lookup: value_key -> abbreviation
        value_to_abbreviation = {}
        for abbreviation, actual_value in value_dict.items():
            value_key = self._make_value_hashable(actual_value)
            value_to_abbreviation[value_key] = abbreviation
        
        # Update cards with abbreviations
        updated_cards = []
        for card in message_data:
            updated_card = card.copy()
            
            if 'f' in updated_card and isinstance(updated_card['f'], dict):
                updated_fields = {}
                
                for code, value in updated_card['f'].items():
                    value_key = self._make_value_hashable(value)
                    
                    if value_key in value_to_abbreviation:
                        # Replace with abbreviation
                        updated_fields[code] = value_to_abbreviation[value_key]
                    else:
                        # Keep original value
                        updated_fields[code] = value
                
                updated_card['f'] = updated_fields
            
            updated_cards.append(updated_card)
        
        duplicates_found = len(value_dict)
        self.logger.debug(f"Created {duplicates_found} value abbreviations across {len(message_data)} cards")
        
        return updated_cards, value_dict
    
    def detect_and_remove_redundancy(self, message_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect and remove redundant fields within each card (90% containment threshold)
        
        Args:
            message_data: List of compact card data
            
        Returns:
            Updated cards with redundant fields removed
        """
        if not message_data:
            return message_data
        
        processed_cards = []
        
        for card in message_data:
            if 'f' not in card or not isinstance(card['f'], dict):
                processed_cards.append(card)
                continue
            
            fields = card['f']
            redundant_codes = set()
            
            # Compare each field against every other field within same card
            for code1, value1 in fields.items():
                # Skip non-text fields, numbers, booleans
                if not self._is_redundancy_candidate(value1):
                    continue
                    
                for code2, value2 in fields.items():
                    if code1 == code2:
                        continue
                    
                    # Skip non-text fields for comparison
                    if not self._is_redundancy_candidate(value2):
                        continue
                    
                    # Check if value1 is 90%+ contained in value2
                    if self._is_contained(value1, value2, 0.9):
                        # Special case: if both fields are 100% identical, prefer the longer field name
                        if (len(str(value1)) == len(str(value2)) and 
                            len(str(code1)) != len(str(code2))):
                            # Prefer longer field name, mark shorter for removal
                            if len(str(code1)) < len(str(code2)):
                                redundant_codes.add(code1)
                                self.logger.debug(f"Field '{code1}' identical to '{code2}', preferring longer name '{code2}'")
                            else:
                                redundant_codes.add(code2)
                                self.logger.debug(f"Field '{code2}' identical to '{code1}', preferring longer name '{code1}'")
                            break
                        else:
                            redundant_codes.add(code1)
                            self.logger.debug(f"Field '{code1}' is 90%+ contained in '{code2}', marked for removal")
                            break
            
            # Remove redundant fields, keeping preferred one
            cleaned_fields = {}
            for code, value in fields.items():
                if code not in redundant_codes:
                    cleaned_fields[code] = value
                else:
                    self.logger.debug(f"Removed redundant field '{code}' from card")
            
            # Create cleaned card
            cleaned_card = card.copy()
            cleaned_card['f'] = cleaned_fields
            processed_cards.append(cleaned_card)
        
        return processed_cards
    
    def _is_redundancy_candidate(self, value: Any) -> bool:
        """
        Check if a value is a candidate for redundancy detection
        
        Args:
            value: Value to check
            
        Returns:
            True if value should be checked for redundancy
        """
        # Only check text fields for redundancy
        if isinstance(value, str):
            # Must be substantial enough to compare
            return len(value.strip()) > 20
        elif isinstance(value, (list, dict)):
            # Check arrays and objects if they contain substantial text
            text_content = str(value)
            return len(text_content.strip()) > 20
        
        # Skip numbers, booleans, null, short text
        return False
    
    def _is_contained(self, smaller_value: Any, larger_value: Any, threshold: float = 0.9) -> bool:
        """
        Check if smaller_value is contained in larger_value with given threshold
        
        Args:
            smaller_value: Value that might be contained
            larger_value: Value that might contain the other
            threshold: Containment threshold (0.9 = 90%)
            
        Returns:
            True if smaller_value is threshold% contained in larger_value
        """
        if not isinstance(smaller_value, str) or not isinstance(larger_value, str):
            return False
        
        smaller_clean = smaller_value.strip().lower()
        larger_clean = larger_value.strip().lower()
        
        # If smaller is empty or very short, not considered contained
        if len(smaller_clean) < 10:
            return False
        
        # Check if smaller string is contained in larger string
        if smaller_clean in larger_clean:
            # Calculate containment ratio
            containment_ratio = len(smaller_clean) / len(larger_clean)
            return containment_ratio >= threshold
        
        return False
    
    def apply_post_processing(self, message_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply all post-processing optimizations to a list of cards
        
        Args:
            message_data: List of compact card data
            
        Returns:
            Processed message with optimizations applied
        """
        if not message_data:
            return {'cards': [], 'value_dict': {}}
        
        # Step 1: Apply pattern consolidation to each card
        processed_cards = []
        for card in message_data:
            consolidated_card = self.detect_and_consolidate_patterns(card)
            processed_cards.append(consolidated_card)
        
        # Step 2: Apply duplicate value abbreviation
        deduped_cards, value_dict = self.detect_and_abbreviate_duplicates(processed_cards)
        
        # Step 3: Apply redundancy detection (NEW)
        final_cards = self.detect_and_remove_redundancy(deduped_cards)
        
        result = {
            'cards': final_cards
        }
        
        # Add value dictionary only if we have abbreviations
        if value_dict:
            result['value_dict'] = value_dict
        
        # Calculate and log optimization stats
        original_field_count = sum(len(card.get('f', {})) for card in message_data)
        optimized_field_count = sum(len(card.get('f', {})) for card in final_cards)
        
        abbreviations_count = len(value_dict)
        fields_saved = original_field_count - optimized_field_count
        
        # if fields_saved > 0 or abbreviations_count > 0:
        #     self.logger.info(f"Post-processing: saved {fields_saved} fields, created {abbreviations_count} abbreviations")
        
        return result
    
    def _make_value_hashable(self, value: Any) -> Any:
        """
        Convert a value to a hashable form for counting duplicates
        
        Args:
            value: Any value (string, number, dict, list, etc.)
            
        Returns:
            Hashable representation of value
        """
        if isinstance(value, dict):
            # Sort keys for consistent hashing
            return tuple(sorted((k, self._make_value_hashable(v)) for k, v in value.items()))
        elif isinstance(value, list):
            return tuple(self._make_value_hashable(item) for item in value)
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        else:
            # Convert other objects to string
            return str(value)
    
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
            
            # self.logger.info(f"Converted {len(fields)} fields to compact format for {target_card_type}")
            return compact_data
            
        except Exception as e:
            self.logger.error(f"Failed to convert HTML to compact format: {e}")
            raise ValueError(f"HTML to compact conversion failed: {e}")
    
    def compact_to_websocket(self, compact_data: Dict[str, Any], card_type: Optional[str] = None, value_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert compact JSON back to WebSocket message format
        
        Args:
            compact_data: Compact representation from AI
            card_type: Expected card type (extracted from compact_data if None)
            value_dict: Optional value dictionary for abbreviations
            
        Returns:
            WebSocket format message for Foundry
        """
        try:
            self.logger.debug(f"Converting compact to WebSocket format")
            
            # Extract basic information
            message_type = compact_data.get('t', 'cc')
            target_card_type = card_type or compact_data.get('ct', 'unknown-card')
            fields = compact_data.get('f', {})
            
            # Resolve abbreviations if value_dict provided
            if value_dict and isinstance(fields, dict):
                resolved_fields = {}
                for code, value in fields.items():
                    if isinstance(value, str) and value.startswith('@v'):
                        # Resolve abbreviation
                        resolved_value = value_dict.get(value, value)
                        resolved_fields[code] = resolved_value
                    else:
                        resolved_fields[code] = value
                fields = resolved_fields
            
            # Get cached mappings for this card type
            card_mapping = self.cache.get_cached_mapping(target_card_type)
            
            if not card_mapping:
                self.logger.warning(f"No cached mapping for card type '{target_card_type}', using fallback")
                return self._fallback_to_websocket(compact_data, value_dict)
            
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
            
            # self.logger.info(f"Converted compact data to WebSocket format for {target_card_type}")
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
    
    def _fallback_to_websocket(self, compact_data: Dict[str, Any], value_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fallback conversion when no cached mapping is available
        
        Args:
            compact_data: Compact data to convert
            value_dict: Optional value dictionary for abbreviations
            
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
        
        # Add cardType to content as well for consistency
        if 'ct' in compact_data:
            websocket_data['content']['cardType'] = compact_data['ct']
        
        # Resolve abbreviations if value_dict provided
        if value_dict and isinstance(websocket_data['content']['fields'], dict):
            resolved_fields = {}
            for code, value in websocket_data['content']['fields'].items():
                if isinstance(value, str) and value.startswith('@v'):
                    # Resolve abbreviation
                    resolved_value = value_dict.get(value, value)
                    resolved_fields[code] = resolved_value
                else:
                    resolved_fields[code] = value
            websocket_data['content']['fields'] = resolved_fields
        
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
