#!/usr/bin/env python3
"""
Universal Settings Handler for The Gold Box
Centralized settings validation, normalization, and transport

Provides unified settings handling across all endpoints:
- simple_chat, process_chat, api_chat, and future endpoints

License: CC-BY-NC-SA 4.0
"""

import logging
import json
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

logger = logging.getLogger(__name__)

class UniversalSettings:
    """
    Universal settings handler for all The Gold Box endpoints
    
    Provides:
    - Centralized settings validation
    - Type conversion and normalization
    - Default value application
    - Error handling with detailed diagnostics
    - Settings debugging and logging
    """
    
    # Complete settings schema with validation rules
    SETTINGS_SCHEMA = {
        'general llm provider': {
            'type': str, 
            'required': True, 
            'default': 'openai',
            'description': 'LLM provider for general AI tasks'
        },
        'general llm model': {
            'type': str, 
            'required': True, 
            'default': 'gpt-3.5-turbo',
            'description': 'Model name for general LLM'
        },
        'general llm base url': {
            'type': str, 
            'required': False, 
            'default': '',
            'description': 'Base URL for general LLM API'
        },
        'general llm version': {
            'type': str, 
            'required': False, 
            'default': 'v1',
            'description': 'API version for general LLM'
        },
        'general llm timeout': {
            'type': int, 
            'required': False, 
            'default': 30,
            'min': 1,
            'max': 300,
            'description': 'Request timeout in seconds for general LLM'
        },
        'general llm max retries': {
            'type': int, 
            'required': False, 
            'default': 3,
            'min': 0,
            'max': 10,
            'description': 'Maximum retry attempts for general LLM'
        },
        'general llm custom headers': {
            'type': str, 
            'required': False, 
            'default': '{}',
            'description': 'Custom headers JSON string for general LLM'
        },
        'tactical llm provider': {
            'type': str, 
            'required': False, 
            'default': 'openai',
            'description': 'LLM provider for tactical AI tasks'
        },
        'tactical llm base url': {
            'type': str, 
            'required': False, 
            'default': '',
            'description': 'Base URL for tactical LLM API'
        },
        'tactical llm model': {
            'type': str, 
            'required': False, 
            'default': 'gpt-3.5-turbo',
            'description': 'Model name for tactical LLM'
        },
        'tactical llm version': {
            'type': str, 
            'required': False, 
            'default': 'v1',
            'description': 'API version for tactical LLM'
        },
        'tactical llm timeout': {
            'type': int, 
            'required': False, 
            'default': 30,
            'min': 1,
            'max': 300,
            'description': 'Request timeout in seconds for tactical LLM'
        },
        'tactical llm max retries': {
            'type': int, 
            'required': False, 
            'default': 3,
            'min': 0,
            'max': 10,
            'description': 'Maximum retry attempts for tactical LLM'
        },
        'tactical llm custom headers': {
            'type': str, 
            'required': False, 
            'default': '{}',
            'description': 'Custom headers JSON string for tactical LLM'
        },
        'maximum message context': {
            'type': int, 
            'required': False, 
            'default': 50,
            'min': 1,
            'max': 100,
            'description': 'Maximum number of messages to include in context'
        },
        'chat processing mode': {
            'type': str, 
            'required': False, 
            'default': 'general',
            'description': 'Which LLM settings to use (general/tactical)'
        },
        'ai role': {
            'type': str, 
            'required': False, 
            'default': 'AI Assistant for tabletop RPGs',
            'description': 'AI role/personality for responses'
        },
        'relay client id': {
            'type': str, 
            'required': False, 
            'default': '',
            'description': 'Client ID for relay server communication'
        },
        'backend password': {
            'type': str, 
            'required': False, 
            'default': '',
            'description': 'Password for backend admin functions'
        }
    }
    
    @classmethod
    def extract_settings(cls, request_data: Dict[str, Any], endpoint_name: str = "unknown") -> Dict[str, Any]:
        """
        Extract and validate settings from request data
        
        Args:
            request_data: Request data (can be from middleware or raw JSON)
            endpoint_name: Name of the endpoint for logging
            
        Returns:
            Dictionary containing validated and normalized settings
        """
        try:
            logger.info(f"UniversalSettings: Extracting settings for {endpoint_name}")
            
            # Extract settings from request data
            if isinstance(request_data, dict):
                # Check if settings are nested under 'settings' key or are the request data itself
                if 'settings' in request_data:
                    settings = request_data.get('settings', {})
                elif any(key.startswith('general') or key.startswith('tactical') or key in ['maximum message context', 'chat processing mode', 'ai role', 'relay client id', 'backend password'] for key in request_data.keys()):
                    # Settings are directly in request data (not nested)
                    settings = request_data
                else:
                    settings = request_data.get('settings', {})
            else:
                logger.warning(f"UniversalSettings: Invalid request_data type: {type(request_data)}")
                settings = {}
            
            # Validate settings type
            if not isinstance(settings, dict):
                logger.error(f"UniversalSettings: Settings is not a dictionary: {type(settings)}")
                settings = {}
            
            # logger.info(f"UniversalSettings: Raw settings extracted: {settings}")
            
            # Validate and normalize each setting
            validated_settings = {}
            validation_errors = []
            
            for key, schema in cls.SETTINGS_SCHEMA.items():
                value = settings.get(key)
                validated_value, error = cls._validate_field(key, value, schema)
                
                if error:
                    validation_errors.append(f"{key}: {error}")
                    # Use default value on validation error
                    validated_settings[key] = schema['default']
                else:
                    validated_settings[key] = validated_value
            
            # Log validation results
            if validation_errors:
                logger.warning(f"UniversalSettings: Validation errors for {endpoint_name}: {validation_errors}")
            else:
                logger.info(f"UniversalSettings: All settings validated successfully for {endpoint_name}")
            
            # Add metadata
            validated_settings['_metadata'] = {
                'extracted_at': datetime.now().isoformat(),
                'endpoint': endpoint_name,
                'validation_errors': validation_errors,
                'raw_settings_count': len(settings),
                'validated_settings_count': len(validated_settings) - 1  # Subtract metadata
            }
            
            # logger.info(f"UniversalSettings: Final validated settings for {endpoint_name}: {validated_settings}")
            
            return validated_settings
            
        except Exception as e:
            logger.error(f"UniversalSettings: Error extracting settings for {endpoint_name}: {e}")
            # Return defaults on error
            return cls.get_default_settings()
    
    @classmethod
    def _validate_field(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> tuple[Any, str]:
        """
        Validate an individual field against its schema
        
        Args:
            field_name: Name of the field
            value: Value to validate
            schema: Schema definition for the field
            
        Returns:
            Tuple of (validated_value, error_message)
        """
        try:
            # Check if required field is missing
            if schema['required'] and value is None:
                return None, f"Required field '{field_name}' is missing"
            
            # Use default if value is None
            if value is None:
                return schema['default'], None
            
            # Type conversion and validation
            expected_type = schema['type']
            
            # Handle None values
            if value is None:
                return schema['default'], None
            
            # Type-specific validation
            if expected_type == str:
                if not isinstance(value, str):
                    try:
                        validated = str(value)
                    except Exception:
                        return schema['default'], f"Cannot convert {field_name} to string"
                else:
                    validated = value.strip() if hasattr(value, 'strip') else value
            elif expected_type == int:
                if isinstance(value, str):
                    try:
                        validated = int(value)
                    except ValueError:
                        return schema['default'], f"Cannot convert {field_name} '{value}' to integer"
                elif isinstance(value, (int, float)):
                    validated = int(value)
                else:
                    return schema['default'], f"Invalid type for {field_name}: {type(value)}"
                
                # Range validation for integers
                if 'min' in schema and validated < schema['min']:
                    return schema['default'], f"{field_name} {validated} is below minimum {schema['min']}"
                if 'max' in schema and validated > schema['max']:
                    return schema['default'], f"{field_name} {validated} is above maximum {schema['max']}"
            else:
                return schema['default'], f"Unsupported type for {field_name}: {expected_type}"
            
            # Additional validation can be added here
            return validated, None
            
        except Exception as e:
            return schema['default'], f"Validation error for {field_name}: {str(e)}"
    
    @classmethod
    def get_default_settings(cls) -> Dict[str, Any]:
        """
        Get all default settings
        
        Returns:
            Dictionary containing all default values
        """
        defaults = {}
        for key, schema in cls.SETTINGS_SCHEMA.items():
            defaults[key] = schema['default']
        
        # Add metadata
        defaults['_metadata'] = {
            'extracted_at': datetime.now().isoformat(),
            'endpoint': 'defaults',
            'validation_errors': [],
            'raw_settings_count': 0,
            'validated_settings_count': len(defaults) - 1
        }
        
        return defaults
    
    @classmethod
    def get_provider_config(cls, settings: Dict[str, Any], use_tactical: bool = False) -> Dict[str, Any]:
        """
        Extract provider configuration from settings
        
        Args:
            settings: Validated settings dictionary
            use_tactical: Whether to use tactical or general settings
            
        Returns:
            Provider configuration dictionary for AI service
        """
        try:
            if use_tactical:
                provider_config = {
                    'provider': settings.get('tactical llm provider', 'openai'),
                    'model': settings.get('tactical llm model', 'gpt-3.5-turbo'),
                    'base_url': settings.get('tactical llm base url', ''),
                    'api_version': settings.get('tactical llm version', 'v1'),
                    'timeout': settings.get('tactical llm timeout', 30),
                    'max_retries': settings.get('tactical llm max retries', 3),
                    'custom_headers': settings.get('tactical llm custom headers', '{}')
                }
            else:
                provider_config = {
                    'provider': settings.get('general llm provider', 'openai'),
                    'model': settings.get('general llm model', 'gpt-3.5-turbo'),
                    'base_url': settings.get('general llm base url', ''),
                    'api_version': settings.get('general llm version', 'v1'),
                    'timeout': settings.get('general llm timeout', 30),
                    'max_retries': settings.get('general llm max retries', 3),
                    'custom_headers': settings.get('general llm custom headers', '{}')
                }
            
            # Parse custom headers if provided
            custom_headers_str = provider_config['custom_headers']
            if custom_headers_str and custom_headers_str.strip() and custom_headers_str != '{}':
                try:
                    provider_config['headers'] = json.loads(custom_headers_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid custom headers JSON: {e}")
                    provider_config['headers'] = {}
            else:
                provider_config['headers'] = {}
            
            # logger.info(f"UniversalSettings: Provider config extracted (use_tactical={use_tactical}): {provider_config}")
            
            return provider_config
            
        except Exception as e:
            logger.error(f"UniversalSettings: Error extracting provider config: {e}")
            # Return safe defaults
            return {
                'provider': 'openai',
                'model': 'gpt-3.5-turbo',
                'base_url': '',
                'api_version': 'v1',
                'timeout': 30,
                'max_retries': 3,
                'headers': {}
            }
    
    @classmethod
    def debug_settings(cls, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create debug information for settings
        
        Args:
            settings: Settings dictionary to debug
            
        Returns:
            Debug information dictionary
        """
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'settings_count': len([k for k in settings.keys() if not k.startswith('_')]),
            'has_general_provider': bool(settings.get('general llm provider')),
            'has_general_model': bool(settings.get('general llm model')),
            'has_tactical_provider': bool(settings.get('tactical llm provider')),
            'has_tactical_model': bool(settings.get('tactical llm model')),
            'general_provider': settings.get('general llm provider', 'NOT_SET'),
            'general_model': settings.get('general llm model', 'NOT_SET'),
            'general_base_url': settings.get('general llm base url', 'NOT_SET'),
            'tactical_provider': settings.get('tactical llm provider', 'NOT_SET'),
            'tactical_model': settings.get('tactical llm model', 'NOT_SET'),
            'tactical_base_url': settings.get('tactical llm base url', 'NOT_SET'),
            'metadata': settings.get('_metadata', {}),
            'all_keys': list(settings.keys())
        }
        
        return debug_info
    
    @classmethod
    def get_settings_schema(cls) -> Dict[str, Any]:
        """
        Get the complete settings schema
        
        Returns:
            Settings schema dictionary
        """
        return cls.SETTINGS_SCHEMA.copy()

# Global settings handler instance
settings_handler = UniversalSettings()

def extract_universal_settings(request_data: Dict[str, Any], endpoint_name: str = "unknown") -> Dict[str, Any]:
    """
    Convenience function to extract universal settings
    
    Args:
        request_data: Request data from endpoint
        endpoint_name: Name of the endpoint for logging
        
    Returns:
        Validated and normalized settings dictionary
    """
    return UniversalSettings.extract_settings(request_data, endpoint_name)

def get_provider_config(settings: Dict[str, Any], use_tactical: bool = False) -> Dict[str, Any]:
    """
    Convenience function to get provider configuration
    
    Args:
        settings: Validated settings dictionary
        use_tactical: Whether to use tactical or general settings
        
    Returns:
        Provider configuration dictionary for AI service
    """
    return UniversalSettings.get_provider_config(settings, use_tactical)

def debug_settings_info(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to debug settings
    
    Args:
        settings: Settings dictionary to debug
        
    Returns:
        Debug information dictionary
    """
    return UniversalSettings.debug_settings(settings)
