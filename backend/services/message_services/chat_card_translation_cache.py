"""
Chat Card Translation Cache - Phase 2 Implementation
Manages dynamic code mappings for chat cards with caching and lifecycle management

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from shared.core.simple_attribute_mapper import get_attribute_mapper
from .dynamic_chat_card_analyzer import CardFieldInfo

logger = logging.getLogger(__name__)

@dataclass
class FieldMapping:
    """Represents a mapping between a field name and its generated code"""
    field_name: str
    code: str
    field_type: str
    original_name: str
    confidence: float
    usage_count: int = 0

@dataclass
class CardTypeMapping:
    """Mappings for a specific card type"""
    card_type: str
    field_mappings: Dict[str, FieldMapping] = field(default_factory=dict)
    reverse_mappings: Dict[str, str] = field(default_factory=dict)  # code -> field_name
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    total_fields: int = 0

class ChatCardTranslationCache:
    """
    Manages dynamic code mappings for chat cards
    Integrates with SimpleAttributeMapper for code generation
    Handles caching lifecycle and collision resolution
    """
    
    def __init__(self):
        """Initialize translation cache"""
        self.logger = logging.getLogger(__name__)
        
        # Card type specific mappings
        self.card_mappings: Dict[str, CardTypeMapping] = {}
        
        # Global collision tracking
        self.used_codes: Dict[str, str] = {}  # code -> field_name
        self.collision_history: List[Tuple[str, str, str]] = []  # (code, old_field, new_field)
        
        # SimpleAttributeMapper instance for code generation
        self.attribute_mapper = get_attribute_mapper()
        
        # Cache lifecycle
        self.cache_created_at = time.time()
        self.cache_version = 1
        
        self.logger.info("ChatCardTranslationCache initialized")
    
    def generate_codes(self, card_type: str, fields: Dict[str, CardFieldInfo]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Generate attribute codes for discovered fields
        
        Args:
            card_type: Type of card
            fields: Dictionary of field information
            
        Returns:
            Tuple of (field_to_code, code_to_field) mappings
        """
        self.logger.info(f"Generating codes for {card_type} with {len(fields)} fields")
        
        # Create or get card type mapping
        if card_type not in self.card_mappings:
            self.card_mappings[card_type] = CardTypeMapping(card_type=card_type)
        
        card_mapping = self.card_mappings[card_type]
        field_to_code = {}
        code_to_field = {}
        
        # Sort fields by confidence (highest first) for better code assignment
        sorted_fields = sorted(fields.items(), key=lambda x: x[1].confidence, reverse=True)
        
        for field_name, field_info in sorted_fields:
            # Generate code for this field with context awareness
            code = self._generate_field_code(field_name, field_info, card_type)
            
            if code:
                # Store mapping
                field_to_code[field_name] = code
                code_to_field[code] = field_name
                
                # Update card mapping
                field_mapping = FieldMapping(
                    field_name=field_name,
                    code=code,
                    field_type=field_info.field_type,
                    original_name=field_name,
                    confidence=field_info.confidence
                )
                
                card_mapping.field_mappings[field_name] = field_mapping
                card_mapping.reverse_mappings[code] = field_name
        
        # Update card metadata
        card_mapping.last_used = time.time()
        card_mapping.total_fields = len(card_mapping.field_mappings)
        
        self.logger.info(f"Generated {len(field_to_code)} codes for {card_type}")
        return field_to_code, code_to_field
    
    def get_cached_mapping(self, card_type: str) -> Optional[CardTypeMapping]:
        """
        Get cached mapping for a card type
        
        Args:
            card_type: Type of card
            
        Returns:
            CardTypeMapping if found, None otherwise
        """
        return self.card_mappings.get(card_type)
    
    def get_field_mapping(self, card_type: str, field_name: str) -> Optional[FieldMapping]:
        """
        Get specific field mapping
        
        Args:
            card_type: Type of card
            field_name: Name of the field
            
        Returns:
            FieldMapping if found, None otherwise
        """
        card_mapping = self.get_cached_mapping(card_type)
        if card_mapping:
            return card_mapping.field_mappings.get(field_name)
        return None
    
    def reverse_lookup_code(self, card_type: str, code: str) -> Optional[str]:
        """
        Look up field name by code
        
        Args:
            card_type: Type of card
            code: Attribute code to look up
            
        Returns:
            Field name if found, None otherwise
        """
        card_mapping = self.get_cached_mapping(card_type)
        if card_mapping:
            return card_mapping.reverse_mappings.get(code)
        return None
    
    def get_schema_definitions(self) -> str:
        """
        Generate schema definitions for system prompt
        
        Returns:
            Formatted string with field definitions
        """
        if not self.card_mappings:
            return ""
        
        schema_lines = []
        
        for card_type, card_mapping in self.card_mappings.items():
            if card_mapping.field_mappings:
                # Card type header
                schema_lines.append(f"# {card_type.upper()} Fields")
                
                # Field definitions
                for field_name, field_mapping in card_mapping.field_mappings.items():
                    type_indicator = self._get_type_indicator(field_mapping.field_type)
                    schema_line = f"{field_mapping.code}: {field_name} ({type_indicator})"
                    schema_lines.append(schema_line)
                
                schema_lines.append("")  # Empty line between card types
        
        return "\n".join(schema_lines)
    
    def get_field_abbreviations(self) -> List[str]:
        """
        Get list of all field abbreviations
        
        Returns:
            List of field codes with type indicators
        """
        abbreviations = []
        
        for card_mapping in self.card_mappings.values():
            for field_mapping in card_mapping.field_mappings.values():
                type_indicator = self._get_type_indicator(field_mapping.field_type)
                abbreviations.append(f"{field_mapping.code}: {field_mapping.field_name} ({type_indicator})")
        
        return abbreviations
    
    def update_usage(self, card_type: str, field_name: str = None, code: str = None):
        """
        Update usage statistics for mappings
        
        Args:
            card_type: Type of card
            field_name: Name of field (optional)
            code: Code that was used (optional)
        """
        card_mapping = self.get_cached_mapping(card_type)
        if card_mapping:
            card_mapping.last_used = time.time()
            
            if field_name and field_name in card_mapping.field_mappings:
                card_mapping.field_mappings[field_name].usage_count += 1
            
            elif code and code in card_mapping.reverse_mappings:
                field_name = card_mapping.reverse_mappings[code]
                if field_name in card_mapping.field_mappings:
                    card_mapping.field_mappings[field_name].usage_count += 1
    
    def clear_cache(self):
        """Clear all cached mappings"""
        self.card_mappings.clear()
        self.used_codes.clear()
        self.collision_history.clear()
        self.cache_created_at = time.time()
        self.cache_version += 1
        
        self.logger.info("Translation cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        total_mappings = sum(len(cm.field_mappings) for cm in self.card_mappings.values())
        total_usages = sum(
            fm.usage_count 
            for cm in self.card_mappings.values() 
            for fm in cm.field_mappings.values()
        )
        
        return {
            'cache_version': self.cache_version,
            'created_at': self.cache_created_at,
            'card_types': len(self.card_mappings),
            'total_mappings': total_mappings,
            'total_usages': total_usages,
            'collision_count': len(self.collision_history),
            'card_type_details': {
                ct: {
                    'field_count': len(cm.field_mappings),
                    'last_used': cm.last_used,
                    'total_fields': cm.total_fields
                }
                for ct, cm in self.card_mappings.items()
            }
        }
    
    def _generate_field_code(self, field_name: str, field_info: CardFieldInfo, card_type: str = None) -> Optional[str]:
        """
        Generate a code for a field using SimpleAttributeMapper with context awareness
        
        Args:
            field_name: Name of field
            field_info: Field information
            card_type: Type of card for context
            
        Returns:
            Generated code or None if generation failed
        """
        try:
            # Use SimpleAttributeMapper for code generation
            # Create context for better code generation
            context = {
                'field_type': field_info.field_type,
                'card_type': card_type or 'unknown',
                'confidence': field_info.confidence,
                'original_name': field_name,
                'semantic_group': self._classify_semantically(field_name),
                'frequency': self._get_field_frequency(field_name, card_type)
            }
            
            # Generate multiple code options and pick best
            code_options = []
            
            # Try direct mapping first
            direct_code = self.attribute_mapper.create_attribute_mapping(
                [field_name], 
                max_length=4,
                context=context
            )
            if direct_code:
                code_options.append(direct_code)
            
            # Try with field type suffix
            type_suffix = self._get_type_suffix(field_info.field_type)
            if type_suffix:
                typed_code = self.attribute_mapper.create_attribute_mapping(
                    [field_name], 
                    max_length=3,
                    context=context
                )
                if typed_code:
                    code_options.append(f"{typed_code}{type_suffix}")
            
            # Try abbreviations
            abbrev_code = self.attribute_mapper.create_attribute_mapping(
                field_name.split('_'), 
                max_length=4,
                context=context
            )
            if abbrev_code:
                code_options.append(abbrev_code)
            
            # Select best code (prefer shorter, collision-free codes)
            selected_code = self._select_best_code(code_options, field_name)
            
            if selected_code:
                # Track usage to prevent future collisions
                if selected_code in self.used_codes and self.used_codes[selected_code] != field_name:
                    self._handle_collision(selected_code, self.used_codes[selected_code], field_name)
                
                self.used_codes[selected_code] = field_name
                return selected_code
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to generate code for field '{field_name}': {e}")
            return None
    
    def _classify_semantically(self, field_name: str) -> str:
        """
        Classify field name into semantic groups
        
        Args:
            field_name: Name of field
            
        Returns:
            Semantic group name
        """
        # Define semantic groups based on common field patterns
        semantic_groups = {
            'identifier': ['name', 'title', 'id', 'uuid'],
            'measure': ['range', 'duration', 'distance', 'area', 'radius', 'size'],
            'attribute': ['damage', 'healing', 'armor', 'defense', 'attack', 'bonus', 'penalty'],
            'resource': ['cost', 'charges', 'uses', 'quantity', 'amount', 'slots'],
            'timing': ['action', 'bonus', 'reaction', 'movement', 'speed'],
            'description': ['desc', 'description', 'text', 'flavor', 'note'],
            'classification': ['type', 'category', 'school', 'level', 'rank', 'class']
        }
        
        field_lower = field_name.lower()
        
        for group_name, keywords in semantic_groups.items():
            if any(keyword in field_lower for keyword in keywords):
                return group_name
        
        return 'general'
    
    def _get_field_frequency(self, field_name: str, card_type: str) -> int:
        """
        Get frequency score for field name across card types
        
        Args:
            field_name: Name of field
            card_type: Current card type
            
        Returns:
            Frequency score (higher = more common)
        """
        # Simple frequency calculation based on field name patterns
        frequency_patterns = {
            'name': 10,     # Very common
            'title': 9,      # Very common
            'type': 8,       # Common
            'level': 7,       # Common
            'damage': 6,      # Moderately common
            'range': 6,        # Moderately common
            'duration': 5,     # Less common
            'action': 5,       # Less common
            'cost': 4,         # Uncommon
            'school': 3,       # Rare
            'requirement': 3,  # Rare
        }
        
        return frequency_patterns.get(field_name.lower().split('_')[0], 1)
    
    def _select_best_code(self, code_options: List[str], field_name: str) -> Optional[str]:
        """
        Select best code from options with collision resolution
        
        Args:
            code_options: List of generated code options
            field_name: Original field name
            
        Returns:
            Best code or None
        """
        if not code_options:
            return None
        
        # Score codes based on multiple criteria
        scored_codes = []
        for code in code_options:
            score = 0
            
            # Prefer shorter codes
            score += (4 - len(code)) * 2
            
            # Check for collisions and resolve with numbering
            base_code = code
            collision_count = 0
            while base_code in self.used_codes and self.used_codes[base_code] != field_name:
                collision_count += 1
                # Add number suffix to resolve collision
                base_code = f"{code[:3]}{collision_count + 1}" if len(code) > 3 else f"{code}{collision_count + 1}"
            
            # Apply collision resolution if needed
            final_code = base_code if collision_count > 0 else code
            
            # Prefer codes without collisions
            if final_code not in self.used_codes:
                score += 10
            elif self.used_codes.get(final_code) == field_name:
                score += 5  # Same field, acceptable
            
            # Prefer codes that start with field name letters
            field_initials = ''.join([c for c in field_name if c.isalpha()][:2])
            if final_code.lower().startswith(field_initials.lower()):
                score += 3
            
            # Prefer codes that contain field name parts
            field_parts = field_name.lower().split('_')
            for part in field_parts:
                if part and part in final_code.lower():
                    score += 1
            
            # Prefer codes that match semantic group patterns
            semantic_group = self._classify_semantically(field_name)
            if semantic_group == 'identifier':
                score += 2  # Boost for identifier fields
            elif semantic_group == 'measure':
                score += 1  # Boost for measurement fields
            elif semantic_group == 'attribute':
                score += 1  # Boost for attribute fields
            
            scored_codes.append((score, final_code))
        
        # Return highest scoring code
        scored_codes.sort(key=lambda x: x[0], reverse=True)
        return scored_codes[0][1] if scored_codes else None
    
    def _handle_collision(self, code: str, old_field: str, new_field: str):
        """
        Handle code collision
        
        Args:
            code: The colliding code
            old_field: Existing field using the code
            new_field: New field wanting the code
        """
        collision_info = (code, old_field, new_field)
        self.collision_history.append(collision_info)
        
        self.logger.warning(f"Code collision detected: '{code}' used by '{old_field}' and '{new_field}'")
    
    def _get_type_indicator(self, field_type: str) -> str:
        """
        Get type indicator for field
        
        Args:
            field_type: Type of field
            
        Returns:
            Type indicator string
        """
        type_indicators = {
            'text': 'T',
            'number': '#',
            'boolean': 'B',
            'array': '[]',
            'object': '{}',
            'unknown': '?'
        }
        return type_indicators.get(field_type, '?')
    
    def _get_type_suffix(self, field_type: str) -> str:
        """
        Get type suffix for code generation
        
        Args:
            field_type: Type of field
            
        Returns:
            Type suffix character
        """
        type_suffixes = {
            'text': '',
            'number': 'n',
            'boolean': 'b',
            'array': 'a',
            'object': 'o',
            'unknown': 'x'
        }
        return type_suffixes.get(field_type, '')

# Global cache instance for current AI turn
_current_cache: Optional[ChatCardTranslationCache] = None

def get_current_cache() -> ChatCardTranslationCache:
    """Get current translation cache instance"""
    global _current_cache
    if _current_cache is None:
        _current_cache = ChatCardTranslationCache()
    return _current_cache

def clear_current_cache():
    """Clear current translation cache"""
    global _current_cache
    if _current_cache:
        _current_cache.clear_cache()
    _current_cache = None

def reset_cache():
    """Reset cache for new AI turn"""
    clear_current_cache()
    return get_current_cache()

def is_cache_active() -> bool:
    """Check if cache is currently active"""
    return _current_cache is not None
