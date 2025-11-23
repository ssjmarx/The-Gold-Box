#!/usr/bin/env python3
"""
The Gold Box - Input Validator Module
Comprehensive input validation with support for Foundry VTT HTML structures

License: CC-BY-NC-SA 4.0
"""

import re
import html
import json
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

class FoundryHTMLParser(HTMLParser):
    """Custom HTML parser for Foundry VTT compatibility"""
    
    def __init__(self, allowed_tags: set, allowed_attrs: set):
        super().__init__()
        self.allowed_tags = allowed_tags
        self.allowed_attrs = allowed_attrs
        self.output = []
        self.current_tag = None
        self.errors = []
    
    def handle_starttag(self, tag, attrs):
        if tag.lower() not in self.allowed_tags:
            self.errors.append(f"Disallowed tag: {tag}")
            return
        
        # Filter attributes
        valid_attrs = []
        for attr_name, attr_value in attrs:
            if self._is_allowed_attr(attr_name):
                # Escape attribute values
                if attr_value:
                    escaped_value = html.escape(attr_value, quote=True)
                    valid_attrs.append(f'{attr_name}="{escaped_value}"')
                else:
                    valid_attrs.append(attr_name)
            else:
                self.errors.append(f"Disallowed attribute: {attr_name} on {tag}")
        
        # Rebuild tag
        if valid_attrs:
            attr_str = ' ' + ' '.join(valid_attrs)
        else:
            attr_str = ''
        
        self.output.append(f'<{tag.lower()}{attr_str}>')
        self.current_tag = tag.lower()
    
    def handle_endtag(self, tag):
        if tag.lower() not in self.allowed_tags:
            self.errors.append(f"Disallowed end tag: {tag}")
            return
        
        self.output.append(f'</{tag.lower()}>')
        self.current_tag = None
    
    def handle_data(self, data):
        # Escape text content
        escaped_data = html.escape(data)
        self.output.append(escaped_data)
    
    def handle_comment(self, data):
        # Remove comments entirely
        pass
    
    def handle_entityref(self, name):
        # Preserve valid HTML entities
        self.output.append(f'&{name};')
    
    def handle_charref(self, name):
        # Preserve character references
        self.output.append(f'&#{name};')
    
    def _is_allowed_attr(self, attr_name: str) -> bool:
        """Check if attribute is allowed"""
        attr_lower = attr_name.lower()
        
        # Allow data-* attributes
        if attr_lower.startswith('data-'):
            return True
        
        # Allow specific safe attributes
        allowed_attrs = {
            'class', 'id', 'style', 'alt', 'src', 'href', 'title', 
            'type', 'action', 'method'
        }
        
        return attr_lower in allowed_attrs
    
    def get_output(self) -> str:
        return ''.join(self.output)
    
    def get_errors(self) -> List[str]:
        return self.errors

class UniversalInputValidator:
    """
    Universal input validation system for The Gold Box
    Handles various input types and prepares for AI API integration
    Supports three validation levels: none, basic, strict
    """
    
    # Security patterns for dangerous content (more specific to avoid false positives)
    DANGEROUS_PATTERNS = [
        # Script injection patterns
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'on\w+\s*=',  # All event handlers
        # SQL injection patterns (more specific to avoid false positives like "D&D")
        r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\s+(?:\*|\w+)\s+(?:FROM|INTO|TABLE)',
        r"[';]\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\s+(?:\*|\w+)",
        # Command injection patterns
        r'[;&|`$(){}[\]]\s*(rm|del|format|shutdown|reboot|cat)',
        r'\|\s*(rm|del|format|shutdown|reboot)',
        # Path traversal patterns
        r'\.\.[\\/]',
        r'[\\/]\.\.[\\/]',
        # XSS patterns
        r'expression\s*\(',
        r'@import',
        # Data exfiltration patterns (more specific)
        r'base64\s*decode',
        r'hex\s*:\s*[0-9a-fA-F]{20,}',  # Only flag long hex strings
    ]
    
    # Foundry VTT allowed HTML elements
    FOUNDRY_ALLOWED_TAGS = {
        'div', 'span', 'section', 'header', 'footer', 'p', 'h4', 'strong', 'em',
        'ul', 'ol', 'li', 'button', 'a', 'img', 'dl', 'dt', 'dd'
    }
    
    # Foundry VTT allowed attributes (plus data-* attributes)
    FOUNDRY_ALLOWED_ATTRS = {
        'class', 'id', 'style', 'alt', 'src', 'href', 'title', 'type', 'action', 'method'
    }
    
    # Allowed characters for different input types
    ALLOWED_CHAR_PATTERNS = {
        'text': r'^[\w\s\.\,\!\?\;\:\-\(\)\[\]\"\'\/\n\r\t]*$',  # Text with punctuation
        'prompt': r'^[\s\S]*$',  # Prompts allow ANY characters (including newlines, Unicode, etc.)
        'api_key': r'^[a-zA-Z0-9\-_\.]+$',  # API keys
        'config': r'^[a-zA-Z0-9\-_\.\/\:\s]*$',  # Configuration values
    }
    
    # Size limits for different input types
    SIZE_LIMITS = {
        'prompt': 10000,  # AI prompts can be longer
        'text': 50000,     # General text
        'api_key': 500,    # API keys
        'config': 1000,     # Configuration values
        'url': 2048,        # URLs
        'email': 254,       # Email addresses
        'filename': 255,     # Filenames
    }
    
    def __init__(self):
        """Initialize validator with compiled regex patterns"""
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL) 
                               for pattern in self.DANGEROUS_PATTERNS]
        self.compiled_allowed = {key: re.compile(pattern) 
                              for key, pattern in self.ALLOWED_CHAR_PATTERNS.items()}
    
    def validate_input(self, 
                   input_data: Any, 
                   input_type: str = 'text',
                   field_name: str = 'input',
                   required: bool = True,
                   min_length: int = 0,
                   max_length: Optional[int] = None,
                   validation_level: str = 'strict') -> Tuple[bool, str, Any]:
        """
        Universal input validation function with support for validation levels
        
        Args:
            input_data: The input data to validate
            input_type: Type of input ('text', 'prompt', 'api_key', 'config', 'url', 'email', 'filename')
            field_name: Name of the field for error messages
            required: Whether the field is required
            min_length: Minimum allowed length
            max_length: Maximum allowed length (overrides default)
            validation_level: Validation level ('none', 'basic', 'strict')
            
        Returns:
            Tuple[bool, str, Any]: (is_valid, error_message, sanitized_data)
        """
        
        # Skip validation entirely if level is 'none'
        if validation_level == 'none':
            if isinstance(input_data, (dict, list)):
                return True, "", input_data
            return True, "", input_data
        
        # Type checking and conversion
        if input_data is None:
            if required:
                return False, f"{field_name} is required", None
            return True, "", None
        
        # Convert to string if not already
        try:
            if isinstance(input_data, (dict, list)):
                # Handle structured data
                return self._validate_structured_data(input_data, input_type, field_name, validation_level)
            else:
                input_str = str(input_data).strip()
        except Exception as e:
            return False, f"{field_name}: Invalid data format", None
        
        # Length validation
        if max_length is None:
            max_length = self.SIZE_LIMITS.get(input_type, 1000)
        
        if len(input_str) < min_length:
            return False, f"{field_name} must be at least {min_length} characters", None
        
        if len(input_str) > max_length:
            return False, f"{field_name} too long (max {max_length} characters)", None
        
        # Allow empty strings for non-required fields
        if required and not input_str:
            return False, f"{field_name} cannot be empty", None
        
        if not required and not input_str:
            return True, "", None
        
        # Level-specific validation
        if validation_level == 'basic' and input_type in ['text', 'prompt']:
            # Basic level allows Foundry HTML structures
            return self._validate_foundry_html(input_str, input_type, field_name)
        
        # Security validation (strict level and other types)
        is_safe, security_error = self._check_security(input_str)
        if not is_safe:
            return False, f"{field_name}: {security_error}", None
        
        # Character pattern validation
        pattern_error = self._check_allowed_characters(input_str, input_type)
        if pattern_error:
            return False, f"{field_name}: {pattern_error}", None
        
        # Type-specific validation
        type_error = self._validate_type_specific(input_str, input_type)
        if type_error:
            return False, f"{field_name}: {type_error}", None
        
        # Sanitization
        sanitized = self._sanitize_input(input_str, input_type)
        
        return True, "", sanitized
    
    def _validate_foundry_html(self, input_str: str, input_type: str, field_name: str) -> Tuple[bool, str, str]:
        """
        Validate input with Foundry VTT HTML compatibility (basic level)
        """
        # First check for dangerous patterns that should never be allowed
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',  # All event handlers
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<form[^>]*>[^<]*<input[^>]*type\s*=\s*["\']file["\']',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, input_str, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                return False, f"{field_name}: Contains dangerous HTML content", None
        
        # Parse and validate HTML structure
        parser = FoundryHTMLParser(self.FOUNDRY_ALLOWED_TAGS, self.FOUNDRY_ALLOWED_ATTRS)
        
        try:
            parser.feed(input_str)
            parser.close()
        except Exception as e:
            return False, f"{field_name}: Invalid HTML structure - {str(e)}", None
        
        # Check for parsing errors
        errors = parser.get_errors()
        if errors:
            # Log errors but don't necessarily fail validation
            logger.debug(f"HTML validation warnings for {field_name}: {errors}")
        
        # Get the cleaned HTML output
        sanitized_html = parser.get_output()
        
        # Apply final size limit
        max_length = self.SIZE_LIMITS.get(input_type, 1000)
        if len(sanitized_html) > max_length:
            sanitized_html = sanitized_html[:max_length]
        
        return True, "", sanitized_html
    
    def _validate_structured_data(self, 
                               data: Union[Dict, List], 
                               input_type: str, 
                               field_name: str,
                               validation_level: str = 'strict') -> Tuple[bool, str, Any]:
        """Validate structured data (dict/list) with validation level support"""
        if isinstance(data, dict):
            # Validate each key-value pair
            sanitized_dict = {}
            for key, value in data.items():
                # All settings fields should be optional
                is_optional_field = key.startswith('general llm') or key.startswith('tactical llm')
                field_required = not is_optional_field
                
                is_valid, error, sanitized_value = self.validate_input(
                    value, input_type, f"{field_name}.{key}", 
                    required=field_required, validation_level=validation_level
                )
                if not is_valid:
                    return False, error, None
                sanitized_dict[key] = sanitized_value
            return True, "", sanitized_dict
        
        elif isinstance(data, list):
            # Validate each item in list
            sanitized_list = []
            for i, item in enumerate(data):
                # Chat messages should use 'prompt' type for longer content
                validation_type = 'prompt' if isinstance(item, dict) and 'content' in item else input_type
                is_valid, error, sanitized_value = self.validate_input(
                    item, validation_type, f"{field_name}[{i}]", validation_level=validation_level
                )
                if not is_valid:
                    return False, error, None
                sanitized_list.append(sanitized_value)
            return True, "", sanitized_list
        
        else:
            return False, f"{field_name}: Unsupported data structure", None
    
    def _check_security(self, input_str: str) -> Tuple[bool, str]:
        """Check for dangerous patterns"""
        for pattern in self.compiled_patterns:
            if pattern.search(input_str):
                return False, "Contains potentially dangerous content"
        return True, ""
    
    def _check_allowed_characters(self, input_str: str, input_type: str) -> str:
        """Check if input contains only allowed characters"""
        if input_type in self.compiled_allowed:
            pattern = self.compiled_allowed[input_type]
            if not pattern.fullmatch(input_str):
                return "Contains invalid characters"
        return ""
    
    def _validate_type_specific(self, input_str: str, input_type: str) -> str:
        """Type-specific validation"""
        if input_type == 'url':
            # Basic URL validation
            url_pattern = re.compile(
                r'^https?://[^\s/$.?#].[^\s]*$',
                re.IGNORECASE
            )
            if not url_pattern.match(input_str):
                return "Invalid URL format"
        
        elif input_type == 'email':
            # Basic email validation
            email_pattern = re.compile(
                r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                re.IGNORECASE
            )
            if not email_pattern.match(input_str):
                return "Invalid email format"
        
        elif input_type == 'filename':
            # Filename validation
            if input_str in ['.', '..', '/', '\\', '']:
                return "Invalid filename"
            # Check for reserved names (Windows)
            reserved_names = [
                'CON', 'PRN', 'AUX', 'NUL',
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
            ]
            base_name = os.path.splitext(input_str)[0].upper()
            if base_name in reserved_names:
                return "Reserved filename"
        
        return ""
    
    def _sanitize_input(self, input_str: str, input_type: str) -> str:
        """Sanitize input based on type"""
        # HTML escaping for text types
        if input_type in ['text', 'prompt', 'config']:
            input_str = html.escape(input_str)
        
        # Remove null bytes
        input_str = input_str.replace('\x00', '')
        
        # Normalize whitespace
        if input_type in ['text', 'prompt']:
            input_str = ' '.join(input_str.split())
        
        # Trim based on type
        max_length = self.SIZE_LIMITS.get(input_type, 1000)
        if len(input_str) > max_length:
            input_str = input_str[:max_length]
        
        return input_str
    
    def validate_ai_request(self, request_data: Dict, validation_level: str = 'strict') -> Tuple[bool, str, Dict]:
        """
        Validate AI-specific request data with validation level support
        Prepares for future AI API integration
        """
        sanitized_request = {}
        
        # Validate prompt (required)
        prompt = request_data.get('prompt')
        is_valid, error, sanitized_prompt = self.validate_input(
            prompt, 'prompt', 'prompt', required=True, validation_level=validation_level
        )
        if not is_valid:
            return False, error, None
        sanitized_request['prompt'] = sanitized_prompt
        
        # Validate optional parameters
        optional_params = {
            'max_tokens': ('int', 100, 8192),
            'temperature': ('float', 0.7, 0.0, 2.0),
            'top_p': ('float', 1.0, 0.0, 1.0),
            'frequency_penalty': ('float', 0.0, -2.0, 2.0),
            'presence_penalty': ('float', 0.0, -2.0, 2.0),
        }
        
        for param, (param_type, default_val, *ranges) in optional_params.items():
            value = request_data.get(param, default_val)
            
            try:
                if param_type == 'int':
                    value = int(float(value))  # Handle string numbers
                    if ranges and len(ranges) == 1 and (value < 0 or value > ranges[0]):
                        return False, f"{param} must be between 0 and {ranges[0]}", None
                elif param_type == 'float':
                    value = float(value)
                    if ranges and len(ranges) == 2 and (value < ranges[0] or value > ranges[1]):
                        return False, f"{param} must be between {ranges[0]} and {ranges[1]}", None
                
                sanitized_request[param] = value
                
            except (ValueError, TypeError):
                return False, f"{param} must be a valid {param_type}", None
        
        return True, "", sanitized_request
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, str]:
        """Validate API key format"""
        if not api_key:
            return True, ""  # Empty API key is allowed in development mode
        
        is_valid, error, sanitized = self.validate_input(
            api_key, 'api_key', 'API key', required=True, min_length=8
        )
        return is_valid, error

# Legacy function for backward compatibility
def validate_prompt(prompt, validator=None, validation_level='strict'):
    """
    Legacy function for backward compatibility
    Uses universal validator if provided, otherwise basic validation
    """
    if validator is None:
        validator = UniversalInputValidator()
    
    is_valid, error, sanitized = validator.validate_input(
        prompt, 'prompt', 'prompt', required=True, validation_level=validation_level
    )
    if not is_valid:
        raise ValueError(error)
    return sanitized
