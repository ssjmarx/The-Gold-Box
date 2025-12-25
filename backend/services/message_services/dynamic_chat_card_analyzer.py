"""
Dynamic Chat Card Analyzer - Phase 2 Implementation
Game-agnostic dynamic discovery and mapping of chat card fields

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CardFieldInfo:
    """Information about a discovered card field"""
    name: str
    value: Any
    field_type: str  # 'text', 'number', 'boolean', 'array', 'object'
    css_class: str
    data_attributes: Dict[str, str]
    html_path: str  # CSS selector path to the element
    confidence: float  # 0.0 to 1.0, how confident we are about this field

class DynamicChatCardAnalyzer:
    """
    Dynamically analyzes chat card HTML to discover all fields
    Works with any Foundry VTT game system or module
    """
    
    def __init__(self):
        """Initialize the dynamic analyzer"""
        self.logger = logging.getLogger(__name__)
        
        # Common CSS patterns for field identification
        self.field_patterns = [
            r'.*field.*',
            r'.*stat.*',
            r'.*value.*',
            r'.*label.*',
            r'.*data.*',
            r'.*property.*',
            r'.*attribute.*',
            r'.*info.*',
            r'.*detail.*',
            r'.*desc.*',  # description
            r'.*name.*',
            r'.*title.*',
            r'.*type.*',
            r'.*level.*',
            r'.*rank.*',
            r'.*category.*',
            r'.*school.*',
            r'.*duration.*',
            r'.*range.*',
            r'.*target.*',
            r'.*damage.*',
            r'.*healing.*',
            r'.*effect.*',
            r'.*action.*',
            r'.*cost.*',
            r'.*requirement.*',
            r'.*condition.*',
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.field_patterns]
        
        # Data attribute patterns to extract
        self.data_patterns = [
            r'data-(.*)',
            r'data_(.*)',
        ]
        
        # HTML5 semantic tags that might contain fields
        self.semantic_tags = [
            'dt', 'dd',  # Definition lists
            'th', 'td',  # Table cells
            'li',       # List items
            'span',      # Inline elements
            'div',       # Block elements
            'p',         # Paragraphs
        ]
        
        self.logger.info("DynamicChatCardAnalyzer initialized")
    
    def analyze_card_structure(self, html_content: str) -> Dict[str, Any]:
        """
        Main entry point - analyze complete card structure
        
        Args:
            html_content: Raw HTML from Foundry chat card
            
        Returns:
            Dictionary with card analysis results
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Classify card type using universal method
            card_type = self.classify_card_type_universal(soup)
            
            # Extract all fields
            fields = self.extract_all_fields(soup)
            
            # Extract metadata
            metadata = self._extract_metadata(soup)
            
            # Build result
            result = {
                'card_type': card_type,
                'fields': fields,
                'metadata': metadata,
                'field_count': len(fields),
                'confidence_score': self._calculate_confidence_score(fields)
            }
            
            self.logger.debug(f"Card analysis complete: {card_type}, {len(fields)} fields")
            return result
            
        except Exception as e:
            self.logger.error(f"Card structure analysis failed: {e}")
            raise ValueError(f"Failed to analyze card structure: {e}")
    
    def extract_all_fields(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """
        Extract all discoverable fields from the card
        
        Args:
            soup: BeautifulSoup object of the card
            
        Returns:
            Dictionary mapping field names to CardFieldInfo objects
        """
        fields = {}
        
        # Method 1: Extract from data attributes (highest confidence)
        fields.update(self._extract_from_data_attributes(soup))
        
        # Method 2: Extract from CSS class patterns
        fields.update(self._extract_from_css_classes(soup))
        
        # Method 3: Extract from semantic HTML structure
        fields.update(self._extract_from_semantic_structure(soup))
        
        # Method 4: Extract from text patterns and pairs
        fields.update(self._extract_from_text_patterns(soup))
        
        # Method 5: Extract from table structures
        fields.update(self._extract_from_tables(soup))
        
        # Method 6: Extract from card footer pills (NEW)
        fields.update(self._extract_pill_fields(soup))
        
        # Method 7: Extract from roll data (NEW)
        fields.update(self._extract_roll_data(soup))
        
        # Method 8: Extract from effect data (NEW)
        fields.update(self._extract_effect_data(soup))
        
        # Method 9: Extract from enchantment data (NEW)
        fields.update(self._extract_enchantment_data(soup))
        
        # Remove duplicates and merge field information
        merged_fields = self._merge_duplicate_fields(fields)
        
        # self.logger.info(f"Extracted {len(merged_fields)} unique fields from chat card")
        return merged_fields
    
    def classify_card_type_universal(self, soup: BeautifulSoup) -> str:
        """
        Classify type of chat card using universal, game-agnostic logic
        
        Args:
            soup: BeautifulSoup object of the card
            
        Returns:
            String representing card type
        """
        # Primary: CSS class patterns
        card_type = self._extract_type_from_classes(soup)
        
        # Secondary: Data attributes
        if not card_type:
            card_type = self._extract_type_from_data_attributes(soup)
        
        # Tertiary: Structural patterns
        if not card_type:
            card_type = self._infer_type_from_structure(soup)
        
        return card_type or 'generic-card'
    
    def _extract_type_from_classes(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract card type from CSS classes"""
        # Look for the main chat card element
        card_elem = soup.select_one('.chat-card')
        if not card_elem:
            return None
        
        # Extract card type from CSS classes
        classes = card_elem.get('class', [])
        
        # Look for specific type patterns in CSS classes
        for class_name in classes:
            class_lower = class_name.lower()
            
            # Direct card type indicators
            if 'activation-card' in class_lower:
                return 'activation-card'
            elif 'item-card' in class_lower:
                return 'item-card'
            elif 'spell-card' in class_lower:
                return 'spell-card'
            elif 'character-card' in class_lower:
                return 'character-card'
            elif 'vehicle-card' in class_lower:
                return 'vehicle-card'
            elif 'chat-card' in class_lower:
                # Generic chat card, infer from other indicators
                continue
        
        # If no specific type found, check for generic chat-card and infer
        if 'chat-card' in ' '.join(classes).lower():
            return self._infer_generic_type(soup)
        
        return None
    
    def _extract_type_from_data_attributes(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract card type from data attributes"""
        card_elem = soup.select_one('.chat-card')
        if not card_elem:
            return None
        
        # Check for data attributes that indicate type
        for attr_name in card_elem.attrs:
            if attr_name.startswith('data-'):
                attr_value = card_elem[attr_name]
                if 'type' in attr_name.lower():
                    return f"{attr_value}-card"
                elif 'category' in attr_name.lower():
                    return f"{attr_value}-card"
                elif 'action' in attr_name.lower():
                    return f"{attr_value}-card"
        
        return None
    
    def _infer_type_from_structure(self, soup: BeautifulSoup) -> Optional[str]:
        """Infer card type from structural patterns"""
        # Look for structural indicators
        card_content = soup.select_one('.chat-card')
        if not card_content:
            return None
        
        # Check for buttons to infer type
        buttons = card_content.select('.card-buttons button[data-action]')
        if buttons:
            actions = [btn.get('data-action', '') for btn in buttons]
            
            if any('rollAttack' in action for action in actions):
                return 'attack-card'
            elif any('rollDamage' in action for action in actions):
                return 'damage-card'
            elif any('placeTemplate' in action for action in actions):
                return 'area-effect-card'
        
        # Check for specific elements
        if card_content.select_one('.card-footer .pill'):
            # Has footer pills, likely an activation/item card
            return 'activation-card'
        
        # Check for subtitle patterns
        subtitle = card_content.select_one('.subtitle')
        if subtitle:
            subtitle_text = subtitle.get_text(strip=True).lower()
            if any(term in subtitle_text for term in ['feature', 'feat']):
                return 'feature-card'
            elif any(term in subtitle_text for term in ['spell', 'cantrip']):
                return 'spell-card'
        
        return None
    
    def _infer_generic_type(self, soup: BeautifulSoup) -> str:
        """Infer type from generic chat card structure"""
        # Look for key structural elements
        card_content = soup.select_one('.chat-card')
        if not card_content:
            return 'generic-card'
        
        # Check for title and subtitle
        title_elem = card_content.select_one('.title')
        subtitle_elem = card_content.select_one('.subtitle')
        
        title = title_elem.get_text(strip=True).lower() if title_elem else ''
        subtitle = subtitle_elem.get_text(strip=True).lower() if subtitle_elem else ''
        
        # Check for specific patterns in content
        content_text = card_content.get_text().lower()
        
        # Look for roll links
        roll_links = card_content.select('.roll-link-group[data-formulas]')
        if roll_links:
            return 'roll-card'
        
        # Look for effect applications
        effects = card_content.select('.effect')
        if effects:
            return 'effect-card'
        
        # Look for enchantment applications
        enchantments = card_content.select('enchantment-application')
        if enchantments:
            return 'enchantment-card'
        
        # Default based on content analysis
        if 'spell' in content_text or 'magic' in content_text:
            return 'spell-card'
        elif any(term in content_text for term in ['attack', 'damage', 'weapon']):
            return 'attack-card'
        elif any(term in content_text for term in ['feature', 'ability', 'skill']):
            return 'feature-card'
        elif any(term in content_text for term in ['item', 'equipment', 'gear']):
            return 'item-card'
        
        return 'generic-card'
    
    def _extract_pill_fields(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract fields from card footer pills"""
        fields = {}
        
        # Find all pills in card footer
        pills = soup.select('.card-footer .pill .label')
        
        for i, pill in enumerate(pills):
            pill_text = self._clean_extracted_text(pill.get_text(strip=True))
            if pill_text:
                field_name = f"pill_{i}_{self._clean_field_name(pill_text)}"
                fields[field_name] = CardFieldInfo(
                    name=field_name,
                    value=pill_text,
                    field_type=self._determine_field_type(pill_text),
                    css_class='pill-label',
                    data_attributes={},
                    html_path=self._generate_css_path(pill),
                    confidence=0.8  # High confidence for structured pills
                )
        
        return fields
    
    def _extract_roll_data(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract roll data from roll-link-groups"""
        fields = {}
        
        # Find all roll groups with formulas
        roll_groups = soup.select('.roll-link-group[data-formulas]')
        
        for i, group in enumerate(roll_groups):
            formula = group.get('data-formulas', '')
            roll_type = group.get('data-type', '')
            roll_text = group.get_text(strip=True)
            
            if formula or roll_text:
                field_name = f"roll_{i}"
                field_value = {
                    'formula': formula,
                    'type': roll_type,
                    'text': roll_text
                }
                
                fields[field_name] = CardFieldInfo(
                    name=field_name,
                    value=field_value,
                    field_type='object',
                    css_class='roll-link-group',
                    data_attributes={
                        'formulas': formula,
                        'type': roll_type
                    },
                    html_path=self._generate_css_path(group),
                    confidence=0.9  # Very high confidence for structured roll data
                )
        
        return fields
    
    def _extract_effect_data(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract effect data from effect applications"""
        fields = {}
        
        # Find all effect elements
        effects = soup.select('.effect')
        
        for i, effect in enumerate(effects):
            name_elem = effect.select_one('.title')
            subtitle_elem = effect.select_one('.subtitle')
            icon_elem = effect.select_one('.gold-icon')
            
            if name_elem:
                effect_name = name_elem.get_text(strip=True)
                effect_subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ''
                icon_src = icon_elem.get('src', '') if icon_elem else ''
                
                field_name = f"effect_{i}"
                field_value = {
                    'name': effect_name,
                    'duration': effect_subtitle,
                    'icon': icon_src
                }
                
                fields[field_name] = CardFieldInfo(
                    name=field_name,
                    value=field_value,
                    field_type='object',
                    css_class='effect',
                    data_attributes={},
                    html_path=self._generate_css_path(effect),
                    confidence=0.85  # High confidence for structured effect data
                )
        
        return fields
    
    def _extract_enchantment_data(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract enchantment data from enchantment applications"""
        fields = {}
        
        # Find enchantment applications
        enchantments = soup.select('enchantment-application')
        
        for i, enchantment in enumerate(enchantments):
            preview_elem = enchantment.select_one('.preview')
            name_elem = preview_elem.select_one('.name') if preview_elem else None
            icon_elem = preview_elem.select_one('.gold-icon') if preview_elem else None
            
            if name_elem:
                enchant_name = name_elem.get_text(strip=True)
                icon_src = icon_elem.get('src', '') if icon_elem else ''
                
                field_name = f"enchantment_{i}"
                field_value = {
                    'name': enchant_name,
                    'icon': icon_src
                }
                
                fields[field_name] = CardFieldInfo(
                    name=field_name,
                    value=field_value,
                    field_type='object',
                    css_class='enchantment',
                    data_attributes={},
                    html_path=self._generate_css_path(enchantment),
                    confidence=0.85  # High confidence for structured enchantment data
                )
        
        return fields
    
    def detect_field_patterns(self, soup: BeautifulSoup) -> List[str]:
        """
        Detect field patterns in the HTML structure
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of detected CSS class patterns
        """
        patterns = []
        
        # Get all elements with classes
        elements_with_classes = soup.find_all(class_=True)
        
        for element in elements_with_classes:
            classes = element.get('class', [])
            for class_name in classes:
                # Check if this class matches our field patterns
                for pattern in self.compiled_patterns:
                    if pattern.match(class_name):
                        patterns.append(class_name)
                        break
        
        # Remove duplicates while preserving order
        unique_patterns = list(dict.fromkeys(patterns))
        return unique_patterns
    
    def _extract_from_data_attributes(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract fields from HTML5 data attributes"""
        fields = {}
        
        # Find all elements with data attributes
        elements_with_data = soup.find_all(attrs={'data': True})
        
        for element in elements_with_data:
            for attr_name, attr_value in element.attrs.items():
                if attr_name.startswith('data-') or attr_name.startswith('data_'):
                    # Clean up attribute name
                    clean_name = attr_name.replace('data-', '').replace('data_', '')
                    
                    # Extract field name and value
                    field_name = self._clean_field_name(clean_name)
                    field_value = self._extract_element_value(element)
                    
                    if field_name and field_value is not None:
                        fields[field_name] = CardFieldInfo(
                            name=field_name,
                            value=field_value,
                            field_type=self._determine_field_type(field_value),
                            css_class=' '.join(element.get('class', [])),
                            data_attributes={k: v for k, v in element.attrs.items() if k.startswith('data')},
                            html_path=self._generate_css_path(element),
                            confidence=0.9  # High confidence for data attributes
                        )
        
        return fields
    
    def _extract_from_css_classes(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract fields from CSS class patterns"""
        fields = {}
        
        # Find elements matching our field patterns
        for element in soup.find_all():
            classes = element.get('class', [])
            
            for class_name in classes:
                # Check if this class matches our field patterns
                for pattern in self.compiled_patterns:
                    if pattern.match(class_name):
                        field_name = self._clean_field_name(class_name)
                        field_value = self._extract_element_value(element)
                        
                        # Apply text cleaning to the field value if it's a string
                        if isinstance(field_value, str):
                            field_value = self._clean_extracted_text(field_value)
                        
                        if field_name and field_value is not None:
                            # Only add if we don't already have this field
                            if field_name not in fields:
                                fields[field_name] = CardFieldInfo(
                                    name=field_name,
                                    value=field_value,
                                    field_type=self._determine_field_type(field_value),
                                    css_class=class_name,
                                    data_attributes={},
                                    html_path=self._generate_css_path(element),
                                    confidence=0.7  # Medium confidence for CSS classes
                                )
                            break
        
        return fields
    
    def _extract_from_semantic_structure(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract fields from semantic HTML structure"""
        fields = {}
        
        # Look for definition lists (dt/dd pairs)
        dt_elements = soup.find_all('dt')
        for dt in dt_elements:
            dt_text = self._clean_extracted_text(dt.get_text(strip=True))
            dd = dt.find_next_sibling('dd')
            
            if dd and dt_text:
                field_name = self._clean_field_name(dt_text)
                field_value = self._extract_element_value(dd)
                
                # Apply text cleaning to field value if it's a string
                if isinstance(field_value, str):
                    field_value = self._clean_extracted_text(field_value)
                
                if field_name and field_value is not None:
                    fields[field_name] = CardFieldInfo(
                        name=field_name,
                        value=field_value,
                        field_type=self._determine_field_type(field_value),
                        css_class='definition-pair',
                        data_attributes={},
                        html_path=self._generate_css_path(dd),
                        confidence=0.8  # High confidence for semantic pairs
                    )
        
        # Look for table structures
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            table_fields = self._extract_table_fields(table, f"table_{i}")
            fields.update(table_fields)
        
        return fields
    
    def _extract_from_text_patterns(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract fields from text patterns (colon-separated pairs)"""
        fields = {}
        
        # Look for text patterns like "Name: Value", "Damage: 1d6", etc.
        text_elements = soup.find_all(string=True)
        
        for text in text_elements:
            text_str = text.strip()
            if ':' in text_str and len(text_str.split(':')) == 2:
                name_part, value_part = text_str.split(':', 1)
                field_name = self._clean_field_name(name_part.strip())
                field_value = self._clean_extracted_text(value_part.strip())
                
                if field_name and field_value:
                    # Get the parent element for path
                    parent = text.parent
                    if parent:
                        fields[field_name] = CardFieldInfo(
                            name=field_name,
                            value=field_value,
                            field_type=self._determine_field_type(field_value),
                            css_class='text-pattern',
                            data_attributes={},
                            html_path=self._generate_css_path(parent),
                            confidence=0.5  # Lower confidence for text patterns
                        )
        
        return fields
    
    def _extract_from_tables(self, soup: BeautifulSoup) -> Dict[str, CardFieldInfo]:
        """Extract fields from table structures"""
        fields = {}
        
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            table_fields = self._extract_table_fields(table, f"table_{i}")
            fields.update(table_fields)
        
        return fields
    
    def _extract_table_fields(self, table: Tag, table_prefix: str) -> Dict[str, CardFieldInfo]:
        """Extract fields from a single table"""
        fields = {}
        
        rows = table.find_all('tr')
        if not rows:
            return fields
        
        # Check if first row is header
        first_row = rows[0]
        header_cells = first_row.find_all(['th', 'td'])
        
        if len(header_cells) == 2 and header_cells[0].name == 'th':
            # Treat as key-value pairs
            data_rows = rows[1:]  # Skip header row
            
            for row in data_rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key_text = cells[0].get_text(strip=True)
                    value_text = cells[1].get_text(strip=True)
                    
                    if key_text and value_text:
                        field_name = self._clean_field_name(f"{table_prefix}_{key_text}")
                        fields[field_name] = CardFieldInfo(
                            name=field_name,
                            value=value_text,
                            field_type=self._determine_field_type(value_text),
                            css_class='table-key-value',
                            data_attributes={},
                            html_path=self._generate_css_path(cells[1]),
                            confidence=0.8
                        )
        else:
            # Treat as simple data rows
            for i, row in enumerate(rows):
                row_text = row.get_text(strip=True)
                if row_text:
                    field_name = self._clean_field_name(f"{table_prefix}_row_{i}")
                    fields[field_name] = CardFieldInfo(
                        name=field_name,
                        value=row_text,
                        field_type='text',
                        css_class='table-row',
                        data_attributes={},
                        html_path=self._generate_css_path(row),
                        confidence=0.6
                    )
        
        return fields
    
    def _merge_duplicate_fields(self, fields: Dict[str, CardFieldInfo]) -> Dict[str, CardFieldInfo]:
        """Merge duplicate fields, keeping highest confidence"""
        merged = {}
        
        for field_name, field_info in fields.items():
            if field_name in merged:
                # Keep the one with higher confidence
                if field_info.confidence > merged[field_name].confidence:
                    merged[field_name] = field_info
                else:
                    # Merge additional info
                    existing = merged[field_name]
                    if field_info.css_class and field_info.css_class != existing.css_class:
                        existing.css_class += f", {field_info.css_class}"
            else:
                merged[field_name] = field_info
        
        return merged
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata about the card"""
        metadata = {}
        
        # Extract title/header
        title_elem = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if title_elem:
            metadata['title'] = title_elem.get_text(strip=True)
        
        # Extract card classes
        card_elem = soup.find(class_=lambda x: x and 'card' in str(x).lower())
        if card_elem:
            metadata['card_classes'] = card_elem.get('class', [])
        
        # Extract any explicit data
        for attr in ['data-type', 'data-category', 'data-system']:
            if card_elem and card_elem.has_attr(attr):
                metadata[attr.replace('data-', '')] = card_elem[attr]
        
        return metadata
    
    def _calculate_confidence_score(self, fields: Dict[str, CardFieldInfo]) -> float:
        """Calculate overall confidence score for the analysis"""
        if not fields:
            return 0.0
        
        total_confidence = sum(field.confidence for field in fields.values())
        return min(total_confidence / len(fields), 1.0)
    
    def _clean_field_name(self, name: str) -> str:
        """Clean and normalize field name"""
        if not name:
            return ""
        
        # Remove special characters except spaces, convert to lowercase
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        clean_name = re.sub(r'\s+', '_', clean_name.strip())
        clean_name = clean_name.lower()
        
        # Remove common prefixes
        prefixes_to_remove = ['field_', 'stat_', 'data_', 'val_']
        for prefix in prefixes_to_remove:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):]
        
        return clean_name
    
    def _extract_element_value(self, element: Tag) -> Any:
        """Extract value from an HTML element"""
        if not element:
            return None
        
        # Check for value attribute first
        if element.has_attr('value'):
            return element['value']
        
        # Check for data-value attribute
        if element.has_attr('data-value'):
            return element['data-value']
        
        # Get text content
        text = element.get_text(strip=True)
        if text:
            # Apply text cleaning to text content
            cleaned_text = self._clean_extracted_text(text)
            
            # Try to convert to number
            if cleaned_text.isdigit():
                return int(cleaned_text)
            try:
                return float(cleaned_text)
            except ValueError:
                pass
            
            # Try to convert to boolean
            if cleaned_text.lower() in ['true', 'yes', 'on', '1']:
                return True
            if cleaned_text.lower() in ['false', 'no', 'off', '0']:
                return False
            
            return cleaned_text
        
        # Check for children with values
        children_with_values = element.find_all(attrs={'value': True})
        if children_with_values:
            values = [child['value'] for child in children_with_values]
            if len(values) == 1:
                return values[0]
            else:
                return values
        
        return None
    
    def _determine_field_type(self, value: Any) -> str:
        """Determine the data type of a field value"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'number'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        elif isinstance(value, str):
            # Check if string represents a different type
            if value.isdigit():
                return 'number'
            try:
                float(value)
                return 'number'
            except ValueError:
                pass
            
            if value.lower() in ['true', 'false', 'yes', 'no', 'on', 'off']:
                return 'boolean'
            
            if value.startswith('[') and value.endswith(']'):
                return 'array'
            
            if value.startswith('{') and value.endswith('}'):
                return 'object'
            
            return 'text'
        else:
            return 'unknown'
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean extracted text to fix common formatting issues
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text with proper spacing
        """
        if not text:
            return text
        
        cleaned = text
        
        # Fix missing spaces after punctuation
        cleaned = re.sub(r'([.!?])([A-Z])', r'\1 \2', cleaned)
        cleaned = re.sub(r'([.,;:])([a-z])', r'\1 \2', cleaned)
        
        # Fix concatenated common D&D terms
        dnd_terms = {
            'Attackaction': 'Attack action',
            'Bonusaction': 'Bonus action',
            'Incapacitatedcondition': 'Incapacitated condition',
            'Proficiencybonus': 'Proficiency bonus',
            'Longrest': 'Long rest',
            'Shortrest': 'Short rest',
            'Spellcastingfocus': 'Spellcasting focus',
            'Spellslots': 'Spell slots',
            'Cantrips': 'Cantrips',  # Capitalize properly
            'Feat': 'Feat',
            'DC8plus': 'DC 8 plus',
            'Proficiency Bonusto': 'Proficiency Bonus to',
            'ASorcerer,Warlock, orWizard': 'A Sorcerer, Warlock, or Wizard',
        }
        
        for wrong_term, correct_term in dnd_terms.items():
            cleaned = cleaned.replace(wrong_term, correct_term)
        
        # Fix spaces around capitalized words in sequences
        cleaned = re.sub(r'([a-z])([A-Z][a-z])', r'\1 \2', cleaned)
        
        # Fix spacing between numbers and letters (e.g., "1d8damage" -> "1d8 damage")
        cleaned = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', cleaned)
        
        # Fix spacing around common D&D terms with numbers
        cleaned = re.sub(r'(DC)(\d+)', r'\1 \2', cleaned)
        cleaned = re.sub(r'(level)(\d+)', r'\1 \2', cleaned)
        cleaned = re.sub(r'(\d+d)(for each)', r'\1 for each', cleaned)
        
        # Fix multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _generate_css_path(self, element: Tag) -> str:
        """Generate a CSS selector path to an element"""
        if not element:
            return ""
        
        path_parts = []
        current = element
        
        while current and current.name:
            # Add tag name
            selector = current.name
            
            # Add ID if present
            if current.get('id'):
                selector += f"#{current['id']}"
            
            # Add classes if present
            classes = current.get('class', [])
            if classes:
                class_selector = '.'.join(classes[:2])  # Limit to first 2 classes
                selector += f".{class_selector}"
            
            path_parts.append(selector)
            current = current.parent
        
        # Reverse to get root-to-element path
        return ' > '.join(reversed(path_parts[-5:]))  # Limit depth to 5

# Global instance for convenience
_dynamic_analyzer = DynamicChatCardAnalyzer()

def get_dynamic_analyzer() -> DynamicChatCardAnalyzer:
    """Get the global dynamic analyzer instance"""
    return _dynamic_analyzer

def analyze_chat_card(html_content: str) -> Dict[str, Any]:
    """
    Convenience function to analyze a chat card
    
    Args:
        html_content: Raw HTML from Foundry chat card
        
    Returns:
        Dictionary with card analysis results
    """
    return _dynamic_analyzer.analyze_card_structure(html_content)
