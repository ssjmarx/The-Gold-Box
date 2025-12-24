#!/usr/bin/env python3
"""
Frontend Settings Handler for The Gold Box
Frontend is the single source of truth for all settings
Backend maintains read-only copies for service access

License: CC-BY-NC-SA 4.0
"""

import logging
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FrontendSettingsException(Exception):
    """Exception raised when frontend settings operations fail"""
    pass

class FrontendSettingsHandler:
    """
    Frontend settings handler - frontend is source of truth
    
    Backend only:
    - Receives settings from frontend via WebSocket
    - Validates settings for service compatibility  
    - Provides read-only access to other services
    - Applies environment variable overrides at startup
    """
    
    # Environment variable overrides (server startup only)
    ENV_OVERRIDES = {
        'GOLD_BOX_PORT': ('general llm port', int, 5000),
        'GOLD_BOX_LOG_LEVEL': ('log_level', str, 'INFO'),
        'GOLD_BOX_MAX_CONTEXT': ('maximum message context', int, None),  # No override by default
        'GOLD_BOX_AI_ROLE': ('ai role', str, None),  # No override by default
    }
    
    def __init__(self):
        """Initialize frontend settings handler"""
        self._frontend_settings = {}
        self._env_overrides = {}
        self._last_updated = None
        self._settings_version = 1
        
        # Apply environment variable overrides at startup
        self._apply_env_overrides()
        
        logger.info("FrontendSettingsHandler initialized - frontend is source of truth")
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides at startup"""
        overrides_applied = 0
        
        for env_var, (setting_key, type_func, default_value) in self.ENV_OVERRIDES.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    if type_func == int:
                        self._env_overrides[setting_key] = int(env_value)
                    else:
                        self._env_overrides[setting_key] = str(env_value)
                    
                    logger.info(f"Environment override applied: {setting_key} = {self._env_overrides[setting_key]} (from {env_var})")
                    overrides_applied += 1
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment override {env_var}={env_value}: {e}")
        
        if overrides_applied > 0:
            logger.info(f"Applied {overrides_applied} environment variable overrides")
    
    def receive_frontend_settings(self, settings: Dict[str, Any], client_id: str = None) -> bool:
        """
        Receive settings from frontend (source of truth)
        
        Args:
            settings: Settings dictionary from frontend
            client_id: Optional client identifier
            
        Returns:
            True if settings were accepted, False otherwise
            
        Raises:
            FrontendSettingsException: If settings are invalid
        """
        try:
            if not settings or not isinstance(settings, dict):
                raise FrontendSettingsException("Invalid settings received from frontend")
            
            # Validate required settings
            validated_settings = self._validate_frontend_settings(settings)
            
            # Store as frontend settings (source of truth)
            self._frontend_settings = validated_settings
            self._last_updated = datetime.now()
            
            logger.info(f"Received settings from frontend{f' (client {client_id})' if client_id else ''}: {len(validated_settings)} settings")
            logger.debug(f"Frontend settings keys: {list(validated_settings.keys())}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to receive frontend settings: {e}")
            raise FrontendSettingsException(f"Settings reception failed: {e}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get setting value (frontend source of truth, with env override)
        
        Args:
            key: Setting key to retrieve
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        # Environment override takes precedence
        if key in self._env_overrides:
            return self._env_overrides[key]
        
        # Frontend settings are source of truth
        return self._frontend_settings.get(key, default)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all current settings (frontend source of truth with env overrides)
        
        Returns:
            Complete settings dictionary
        """
        # Start with frontend settings
        all_settings = self._frontend_settings.copy()
        
        # Apply environment overrides
        all_settings.update(self._env_overrides)
        
        # Add metadata
        all_settings['_metadata'] = {
            'source': 'frontend',
            'last_updated': self._last_updated.isoformat() if self._last_updated else None,
            'settings_version': self._settings_version,
            'env_overrides': list(self._env_overrides.keys()),
            'total_frontend_settings': len(self._frontend_settings)
        }
        
        return all_settings
    
    def _validate_frontend_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate frontend settings for backend compatibility
        
        Args:
            settings: Settings dictionary from frontend
            
        Returns:
            Validated settings dictionary
        """
        validated = {}
        validation_errors = []
        
        # Required settings validation
        required_settings = [
            'general llm provider',
            'general llm model',
            'backend password'
        ]
        
        for setting in required_settings:
            if setting not in settings or not settings[setting]:
                validation_errors.append(f"Required setting missing: {setting}")
            else:
                validated[setting] = settings[setting]
        
        # Optional settings with type validation
        optional_settings = {
            'maximum message context': (int, 1, 100, 50),
            'ai role': (str, None, None, None),
            'general llm timeout': (int, 1, 300, 30),
            'general llm max retries': (int, 0, 10, 3),
            'relay client id': (str, None, None, ''),
            'general llm base url': (str, None, None, ''),
            'general llm version': (str, None, None, 'v1'),
            'general llm custom headers': (str, None, None, '{}'),
            'memorySettings': (dict, None, None, {}),
        }
        
        for setting, (type_func, min_val, max_val, default) in optional_settings.items():
            if setting in settings and settings[setting] is not None:
                try:
                    if type_func == int:
                        validated[setting] = int(settings[setting])
                        
                        # Range validation
                        if min_val is not None and validated[setting] < min_val:
                            validation_errors.append(f"{setting} {validated[setting]} below minimum {min_val}")
                        elif max_val is not None and validated[setting] > max_val:
                            validation_errors.append(f"{setting} {validated[setting]} above maximum {max_val}")
                    else:
                        validated[setting] = str(settings[setting]).strip()
                        
                except (ValueError, TypeError) as e:
                    validation_errors.append(f"Invalid {setting}: {e}")
                    if default is not None:
                        validated[setting] = default
            elif default is not None:
                validated[setting] = default
        
        # Copy other settings through (for extensibility)
        for key, value in settings.items():
            if key not in validated and not key.startswith('_'):
                # Special validation for memorySettings
                if key == 'memorySettings':
                    if isinstance(value, dict):
                        # Validate memorySettings structure
                        memory_validated = {}
                        if 'maxHistoryTokens' in value:
                            try:
                                max_tokens = int(value['maxHistoryTokens'])
                                if max_tokens > 0:
                                    memory_validated['maxHistoryTokens'] = max_tokens
                                else:
                                    validation_errors.append("maxHistoryTokens must be greater than 0")
                            except (ValueError, TypeError):
                                validation_errors.append("maxHistoryTokens must be a valid integer")
                        
                        if 'maxHistoryMessages' in value:
                            try:
                                max_messages = int(value['maxHistoryMessages'])
                                if max_messages > 0:
                                    memory_validated['maxHistoryMessages'] = max_messages
                                else:
                                    validation_errors.append("maxHistoryMessages must be greater than 0")
                            except (ValueError, TypeError):
                                validation_errors.append("maxHistoryMessages must be a valid integer")
                        
                        if 'maxHistoryHours' in value:
                            try:
                                max_hours = int(value['maxHistoryHours'])
                                if max_hours > 0:
                                    memory_validated['maxHistoryHours'] = max_hours
                                else:
                                    validation_errors.append("maxHistoryHours must be greater than 0")
                            except (ValueError, TypeError):
                                validation_errors.append("maxHistoryHours must be a valid integer")
                        
                        # Set default maxHistoryTokens if not provided
                        if 'maxHistoryTokens' not in memory_validated:
                            memory_validated['maxHistoryTokens'] = 5000  # Default 5k tokens
                        
                        validated[key] = memory_validated
                    else:
                        validation_errors.append("memorySettings must be a dictionary")
                        validated[key] = {'maxHistoryTokens': 5000}  # Default fallback
                else:
                    validated[key] = value
        
        if validation_errors:
            logger.warning(f"Frontend settings validation errors: {validation_errors}")
            # Still accept settings but log errors - frontend is source of truth
        
        return validated
    
    def get_provider_config(self, use_tactical: bool = False) -> Dict[str, Any]:
        """
        Get provider configuration from frontend settings
        
        Args:
            use_tactical: Whether to use tactical settings
            
        Returns:
            Provider configuration dictionary
        """
        if use_tactical:
            prefix = 'tactical'
        else:
            prefix = 'general'
        
        config = {
            'provider': self.get_setting(f'{prefix} llm provider', 'openai'),
            'model': self.get_setting(f'{prefix} llm model', 'gpt-3.5-turbo'),
            'base_url': self.get_setting(f'{prefix} llm base url', ''),
            'api_version': self.get_setting(f'{prefix} llm version', 'v1'),
            'timeout': self.get_setting(f'{prefix} llm timeout', 30),
            'max_retries': self.get_setting(f'{prefix} llm max retries', 3),
        }
        
        # Parse custom headers
        custom_headers_str = self.get_setting(f'{prefix} llm custom headers', '{}')
        if custom_headers_str and custom_headers_str.strip() and custom_headers_str != '{}':
            try:
                config['custom_headers'] = json.loads(custom_headers_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid custom headers JSON: {e}")
                config['custom_headers'] = {}
        else:
            config['custom_headers'] = {}
        
        return config
    
    def get_settings_info(self) -> Dict[str, Any]:
        """
        Get settings information for debugging
        
        Returns:
            Settings information dictionary
        """
        return {
            'frontend_settings_count': len(self._frontend_settings),
            'env_overrides_count': len(self._env_overrides),
            'last_updated': self._last_updated.isoformat() if self._last_updated else None,
            'settings_version': self._settings_version,
            'env_overrides': list(self._env_overrides.keys()),
            'frontend_keys': list(self._frontend_settings.keys()),
            'source_of_truth': 'frontend'
        }

# Global instance - frontend settings are single source of truth
frontend_settings_handler = FrontendSettingsHandler()

def get_frontend_settings_handler() -> FrontendSettingsHandler:
    """Get the frontend settings handler instance"""
    return frontend_settings_handler

def receive_frontend_settings(settings: Dict[str, Any], client_id: str = None) -> bool:
    """
    Convenience function to receive frontend settings
    
    Args:
        settings: Settings dictionary from frontend
        client_id: Optional client identifier
        
    Returns:
        True if settings were accepted
    """
    return frontend_settings_handler.receive_frontend_settings(settings, client_id)

def get_frontend_setting(key: str, default: Any = None) -> Any:
    """
    Convenience function to get a frontend setting
    
    Args:
        key: Setting key to retrieve
        default: Default value if not found
        
    Returns:
        Setting value or default
    """
    return frontend_settings_handler.get_setting(key, default)

def get_all_frontend_settings() -> Dict[str, Any]:
    """
    Convenience function to get all frontend settings
    
    Returns:
        Complete settings dictionary
    """
    return frontend_settings_handler.get_all_settings()
