#!/usr/bin/env python3
"""
Service Factory for The Gold Box
Centralized service access to eliminate redundant initialization patterns

Replaces scattered fallback chains with single source of truth for service access.
Provides fail-fast behavior with clear error messages instead of silent fallbacks.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

def get_provider_manager() -> Any:
    """
    Get the provider manager from ServiceRegistry.
    
    Returns:
        ProviderManager instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or provider_manager is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('provider_manager'):
        raise RuntimeError(
            "provider_manager is not registered in ServiceRegistry. "
            "Check that key_manager and provider_manager are properly registered during startup."
        )
    
    return ServiceRegistry.get('provider_manager')

def get_key_manager() -> Any:
    """
    Get the key manager from ServiceRegistry.
    
    Returns:
        KeyManager instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or key_manager is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('key_manager'):
        raise RuntimeError(
            "key_manager is not registered in ServiceRegistry. "
            "Check that key_manager is properly registered during startup."
        )
    
    return ServiceRegistry.get('key_manager')

def get_websocket_manager() -> Any:
    """
    Get the websocket manager from ServiceRegistry.
    
    Returns:
        WebSocketManager instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or websocket_manager is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('websocket_manager'):
        raise RuntimeError(
            "websocket_manager is not registered in ServiceRegistry. "
            "Check that websocket_manager is properly registered during startup."
        )
    
    return ServiceRegistry.get('websocket_manager')

def get_settings_manager() -> Any:
    """
    Get the settings manager from ServiceRegistry.
    
    Returns:
        SettingsManager instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or settings_manager is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('settings_manager'):
        raise RuntimeError(
            "settings_manager is not registered in ServiceRegistry. "
            "Check that settings_manager is properly registered during startup."
        )
    
    return ServiceRegistry.get('settings_manager')

def get_session_manager() -> Any:
    """
    Get the session manager from ServiceRegistry.
    
    Returns:
        SessionManager instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or session_manager is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('session_manager'):
        raise RuntimeError(
            "session_manager is not registered in ServiceRegistry. "
            "Check that session_manager is properly registered during startup."
        )
    
    return ServiceRegistry.get('session_manager')

def get_ai_service() -> Any:
    """
    Get the AI service from ServiceRegistry.
    
    Returns:
        AIService instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or ai_service is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('ai_service'):
        raise RuntimeError(
            "ai_service is not registered in ServiceRegistry. "
            "Check that ai_service is properly registered during startup."
        )
    
    return ServiceRegistry.get('ai_service')

def get_message_collector() -> Any:
    """
    Get the message collector from ServiceRegistry.
    
    Returns:
        MessageCollector instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or message_collector is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('message_collector'):
        raise RuntimeError(
            "message_collector is not registered in ServiceRegistry. "
            "Check that message_collector is properly registered during startup."
        )
    
    return ServiceRegistry.get('message_collector')

def get_client_manager() -> Any:
    """
    Get the client manager from ServiceRegistry.
    
    Returns:
        ClientManager instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or client_manager is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('client_manager'):
        raise RuntimeError(
            "client_manager is not registered in ServiceRegistry. "
            "Check that client_manager is properly registered during startup."
        )
    
    return ServiceRegistry.get('client_manager')

def validate_service_registry(required_services: list = None) -> bool:
    """
    Validate that ServiceRegistry is ready and contains required services.
    
    Args:
        required_services: List of service names that must be registered
        
    Returns:
        True if all validations pass
        
    Raises:
        RuntimeError: If any validation fails
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError("ServiceRegistry is not ready")
    
    if required_services:
        missing_services = []
        for service_name in required_services:
            if not ServiceRegistry.is_registered(service_name):
                missing_services.append(service_name)
        
        if missing_services:
            available_services = ServiceRegistry.list_services()
            raise RuntimeError(
                f"Missing required services: {missing_services}. "
                f"Available services: {available_services}"
            )
    
    return True

def get_rate_limiter() -> Any:
    """
    Get the rate limiter from ServiceRegistry.
    
    Returns:
        RateLimiter instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or rate_limiter is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('rate_limiter'):
        raise RuntimeError(
            "rate_limiter is not registered in ServiceRegistry. "
            "Check that rate_limiter is properly registered during startup."
        )
    
    return ServiceRegistry.get('rate_limiter')

def get_validator() -> Any:
    """
    Get the validator from ServiceRegistry.
    
    Returns:
        Validator instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or validator is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('validator'):
        raise RuntimeError(
            "validator is not registered in ServiceRegistry. "
            "Check that validator is properly registered during startup."
        )
    
    return ServiceRegistry.get('validator')

def get_service_info() -> dict:
    """
    Get information about all registered services for debugging.
    
    Returns:
        Dictionary with service registry information
    """
    from .registry import ServiceRegistry
    
    return {
        'is_ready': ServiceRegistry.is_ready(),
        'registered_services': ServiceRegistry.list_services(),
        'service_info': ServiceRegistry.get_service_info(),
        'startup_order': ServiceRegistry.get_startup_order()
    }

def get_input_validator() -> Any:
    """
    Get input validator from ServiceRegistry.
    
    Returns:
        InputValidator instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or input_validator is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('input_validator'):
        raise RuntimeError(
            "input_validator is not registered in ServiceRegistry. "
            "Check that input_validator is properly registered during startup."
        )
    
    return ServiceRegistry.get('input_validator')

def get_attribute_mapper() -> Any:
    """
    Get attribute mapper from ServiceRegistry.
    
    Returns:
        SimpleAttributeMapper instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or attribute_mapper is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('attribute_mapper'):
        raise RuntimeError(
            "attribute_mapper is not registered in ServiceRegistry. "
            "Check that attribute_mapper is properly registered during startup."
        )
    
    return ServiceRegistry.get('attribute_mapper')

def get_json_optimizer() -> Any:
    """
    Get JSON optimizer from ServiceRegistry.
    
    Returns:
        JSONOptimizer instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or json_optimizer is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('json_optimizer'):
        raise RuntimeError(
            "json_optimizer is not registered in ServiceRegistry. "
            "Check that json_optimizer is properly registered during startup."
        )
    
    return ServiceRegistry.get('json_optimizer')
