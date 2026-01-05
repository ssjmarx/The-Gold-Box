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

class SettingsException(Exception):
    """Exception raised when settings operations fail"""
    pass

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
        'max history tokens': {
            'type': int,
            'required': False,
            'default': 5000,
            'min': 1000,
            'max': 32000,
            'description': 'Maximum tokens to keep in conversation history before cleaning up oldest messages'
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
        'player list': {
            'type': str, 
            'required': False, 
            'default': '',
            'description': 'Comma-separated list of player characters the user is controlling'
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
        },
        'combat ai thinking': {
            'type': bool, 
            'required': False, 
            'default': True,
            'description': 'Enable AI thinking during combat encounters'
        },
        'thinking whisper duration': {
            'type': int, 
            'required': False, 
            'default': 5,
            'min': 1,
            'max': 30,
            'description': 'Duration in seconds for thinking whisper animations'
        },
        'auto tactical mode': {
            'type': bool, 
            'required': False, 
            'default': True,
            'description': 'Automatically use tactical LLM during combat'
        },
        'disable function calling': {
            'type': bool,
            'required': False,
            'default': False,
            'description': 'Disable AI tool usage (get_messages, post_messages). Only enable if your AI provider does not support function calling.'
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
            logger.debug(f"UniversalSettings: Extracting settings for {endpoint_name}")
            
            # Extract settings from request data
            if isinstance(request_data, dict):
                # Check if settings are nested under 'settings' key or are the request data itself
                if 'settings' in request_data:
                    settings = request_data.get('settings', {})
                elif any(key.startswith('general') or key.startswith('tactical') or key in ['max history tokens', 'chat processing mode', 'ai role', 'relay client id', 'backend password', 'disable function calling'] for key in request_data.keys()):
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
                logger.debug(f"UniversalSettings: All settings validated successfully for {endpoint_name}")
            
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
            
        except (TypeError, ValueError, KeyError) as e:
            logger.error(f"UniversalSettings: Settings validation error for {endpoint_name}: {e}")
            raise SettingsException(f"Settings validation failed for {endpoint_name}: {e}")
        except Exception as e:
            logger.error(f"UniversalSettings: Unexpected error for {endpoint_name}: {e}")
            raise SettingsException(f"Unexpected settings error for {endpoint_name}: {e}")
    
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
            elif expected_type == bool:
                # Handle boolean type - accept bool, string, or numeric values
                if isinstance(value, bool):
                    validated = value
                elif isinstance(value, str):
                    # Convert string to bool
                    lower_val = value.strip().lower()
                    if lower_val in ('true', 'yes', '1', 'on', 'enabled'):
                        validated = True
                    elif lower_val in ('false', 'no', '0', 'off', 'disabled'):
                        validated = False
                    else:
                        return schema['default'], f"Cannot convert {field_name} '{value}' to boolean"
                elif isinstance(value, (int, float)):
                    validated = bool(value)
                else:
                    return schema['default'], f"Invalid type for {field_name}: {type(value)}"
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
            
        except (ValueError, TypeError) as e:
            return schema['default'], f"Validation error for {field_name}: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected validation error for {field_name}: {e}")
            raise SettingsException(f"Unexpected validation error for {field_name}: {e}")
    
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
        Extract provider configuration from validated settings
        
        Args:
            settings: Validated settings dictionary (must contain required fields)
            use_tactical: Whether to use tactical or general settings
            
        Returns:
            Provider configuration dictionary for AI service
            
        Raises:
            SettingsException: If required configuration fields are missing
        """
        try:
            # Validate that settings dictionary is provided
            if not settings or not isinstance(settings, dict):
                raise SettingsException("Settings dictionary is required and must be non-empty")
            
            # Define required field mappings based on configuration type
            if use_tactical:
                required_fields = {
                    'tactical llm provider': 'provider',
                    'tactical llm model': 'model'
                }
                optional_fields = {
                    'tactical llm base url': 'base_url',
                    'tactical llm version': 'api_version',
                    'tactical llm timeout': 'timeout',
                    'tactical llm max retries': 'max_retries',
                    'tactical llm custom headers': 'custom_headers'
                }
            else:
                required_fields = {
                    'general llm provider': 'provider',
                    'general llm model': 'model'
                }
                optional_fields = {
                    'general llm base url': 'base_url',
                    'general llm version': 'api_version',
                    'general llm timeout': 'timeout',
                    'general llm max retries': 'max_retries',
                    'general llm custom headers': 'custom_headers'
                }
            
            # Validate required fields are present
            missing_fields = []
            for settings_field, config_field in required_fields.items():
                if settings_field not in settings or settings[settings_field] is None:
                    missing_fields.append(settings_field)
            
            if missing_fields:
                config_type = "tactical" if use_tactical else "general"
                raise SettingsException(f"Required {config_type} configuration fields missing: {', '.join(missing_fields)}")
            
            # Build provider config with explicit field access
            provider_config = {}
            
            # Add required fields (must exist)
            for settings_field, config_field in required_fields.items():
                provider_config[config_field] = settings[settings_field]
            
            # Add optional fields with explicit presence checking
            for settings_field, config_field in optional_fields.items():
                if settings_field in settings and settings[settings_field] is not None:
                    provider_config[config_field] = settings[settings_field]
                else:
                    # Use schema defaults for optional fields if not provided
                    schema_field = cls.SETTINGS_SCHEMA.get(settings_field, {})
                    provider_config[config_field] = schema_field.get('default')
            
            # Parse custom headers if provided
            custom_headers_str = provider_config.get('custom_headers', '{}')
            if custom_headers_str and custom_headers_str.strip() and custom_headers_str != '{}':
                try:
                    provider_config['headers'] = json.loads(custom_headers_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid custom headers JSON: {e}")
                    provider_config['headers'] = {}
            else:
                provider_config['headers'] = {}
            
            logger.debug(f"UniversalSettings: Provider config extracted (use_tactical={use_tactical}): {provider_config}")
            
            return provider_config
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"UniversalSettings: Error extracting provider config: {e}")
            raise SettingsException(f"Provider config extraction failed: {e}")
        except Exception as e:
            logger.error(f"UniversalSettings: Unexpected error extracting provider config: {e}")
            raise SettingsException(f"Unexpected provider config error: {e}")
    
    @classmethod
    def debug_settings(cls, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create debug information for settings with explicit field validation
        
        Args:
            settings: Settings dictionary to debug
            
        Returns:
            Debug information dictionary
            
        Raises:
            SettingsException: If settings dictionary is invalid
        """
        try:
            # Validate input
            if not settings or not isinstance(settings, dict):
                raise SettingsException("Settings dictionary is required for debugging")
            
            # Define debug fields with explicit presence checking
            debug_fields = [
                'general llm provider', 'general llm model', 'general llm base url',
                'tactical llm provider', 'tactical llm model', 'tactical llm base url'
            ]
            
            debug_info = {
                'timestamp': datetime.now().isoformat(),
                'settings_count': len([k for k in settings.keys() if not k.startswith('_')]),
                'metadata': settings.get('_metadata', {}),
                'all_keys': list(settings.keys())
            }
            
            # Add explicit field presence checks
            for field in debug_fields:
                field_key = field.replace(' ', '_')
                if field in settings:
                    debug_info[f'has_{field_key}'] = True
                    debug_info[field_key] = settings[field]
                else:
                    debug_info[f'has_{field_key}'] = False
                    debug_info[field_key] = 'NOT_SET'
            
            return debug_info
            
        except Exception as e:
            logger.error(f"UniversalSettings: Error creating debug info: {e}")
            raise SettingsException(f"Debug settings creation failed: {e}")
    
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
