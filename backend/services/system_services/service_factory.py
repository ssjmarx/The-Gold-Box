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

def get_combat_encounter_service() -> Any:
    """
    Get combat encounter service from ServiceRegistry.
    
    Returns:
        CombatEncounterService instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or combat_encounter_service is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('combat_encounter_service'):
        raise RuntimeError(
            "combat_encounter_service is not registered in ServiceRegistry. "
            "Check that combat_encounter_service is properly registered during startup."
        )
    
    return ServiceRegistry.get('combat_encounter_service')

def get_whisper_service() -> Any:
    """
    Get whisper service from ServiceRegistry.
    
    Returns:
        WhisperService instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or whisper_service is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('whisper_service'):
        raise RuntimeError(
            "whisper_service is not registered in ServiceRegistry. "
            "Check that whisper_service is properly registered during startup."
        )
    
    return ServiceRegistry.get('whisper_service')

def get_ai_session_manager() -> Any:
    """
    Get AI session manager from ServiceRegistry.
    
    Returns:
        AISessionManager instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or ai_session_manager is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('ai_session_manager'):
        raise RuntimeError(
            "ai_session_manager is not registered in ServiceRegistry. "
            "Check that ai_session_manager is properly registered during startup."
        )
    
    return ServiceRegistry.get('ai_session_manager')

def get_message_delta_service() -> Any:
    """
    Get message delta service from ServiceRegistry.
    
    Returns:
        MessageDeltaService instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or message_delta_service is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('message_delta_service'):
        raise RuntimeError(
            "message_delta_service is not registered in ServiceRegistry. "
            "Check that message_delta_service is properly registered during startup."
        )
    
    return ServiceRegistry.get('message_delta_service')

def get_ai_orchestrator() -> Any:
    """
    Get AI orchestrator from ServiceRegistry.
    
    Returns:
        AIOrchestrator instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or ai_orchestrator is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('ai_orchestrator'):
        raise RuntimeError(
            "ai_orchestrator is not registered in ServiceRegistry. "
            "Check that ai_orchestrator is properly registered during startup."
        )
    
    return ServiceRegistry.get('ai_orchestrator')

def get_ai_tool_executor() -> Any:
    """
    Get AI tool executor from ServiceRegistry.
    
    Returns:
        AIToolExecutor instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or ai_tool_executor is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('ai_tool_executor'):
        raise RuntimeError(
            "ai_tool_executor is not registered in ServiceRegistry. "
            "Check that ai_tool_executor is properly registered during startup."
        )
    
    return ServiceRegistry.get('ai_tool_executor')

def get_testing_session_manager() -> Any:
    """
    Get testing session manager from ServiceRegistry.
    
    Returns:
        TestingSessionManager instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or testing_session_manager is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('testing_session_manager'):
        raise RuntimeError(
            "testing_session_manager is not registered in ServiceRegistry. "
            "Check that testing_session_manager is properly registered during startup."
        )
    
    return ServiceRegistry.get('testing_session_manager')

def get_testing_harness() -> Any:
    """
    Get testing harness from ServiceRegistry.
    
    Returns:
        TestingHarness instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or testing_harness is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('testing_harness'):
        raise RuntimeError(
            "testing_harness is not registered in ServiceRegistry. "
            "Check that testing_harness is properly registered during startup."
        )
    
    return ServiceRegistry.get('testing_harness')

def get_testing_command_processor() -> Any:
    """
    Get testing command processor from ServiceRegistry.
    
    Returns:
        TestingCommandProcessor instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or testing_command_processor is not registered
    """
    from .registry import ServiceRegistry
    
    if not ServiceRegistry.is_ready():
        raise RuntimeError(
            "ServiceRegistry is not ready. Services must be initialized during server startup. "
            "Check that run_server_startup() completed successfully."
        )
    
    if not ServiceRegistry.is_registered('testing_command_processor'):
        raise RuntimeError(
            "testing_command_processor is not registered in ServiceRegistry. "
            "Check that testing_command_processor is properly registered during startup."
        )
    
    return ServiceRegistry.get('testing_command_processor')
