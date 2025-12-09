"""
The Gold Box - Startup Validation Module

Handles all requirements validation during server startup.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import socket
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def find_available_port(start_port: int = 5000, max_attempts: int = 10) -> Optional[int]:
    """
    Find an available port starting from start_port.
    Returns first available port or None if none found.
    
    Args:
        start_port: Port to start checking from
        max_attempts: Maximum number of ports to check
        
    Returns:
        Available port number or None if none found
    """
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def validate_api_keys(manager) -> bool:
    """
    Validate that API keys are properly configured.
    
    Args:
        manager: MultiKeyManager instance
        
    Returns:
        True if valid API keys exist, False otherwise
    """
    try:
        # Check for valid API keys
        valid_keys_exist = any(key for key in manager.keys_data.values() if key)
        if not valid_keys_exist:
            logger.error("No valid API keys found")
            return False
        
        logger.info(f"Found {len([k for k in manager.keys_data.values() if k])} valid API key(s)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate API keys: {e}")
        return False

def validate_admin_password(manager) -> bool:
    """
    Validate that admin password is set.
    
    Args:
        manager: MultiKeyManager instance
        
    Returns:
        True if admin password is set, False otherwise
    """
    try:
        if not manager.get_password_status():
            logger.error("No admin password set")
            return False
        
        logger.info("Admin password configured")
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate admin password: {e}")
        return False

def validate_server_requirements(manager) -> bool:
    """
    Validate that server has all required configurations.
    
    Args:
        manager: MultiKeyManager instance
        
    Returns:
        True if all requirements are met, False otherwise
    """
    try:
        logger.info("The Gold Box - Validating Server Requirements")
        logger.info("=" * 50)
        
        # Check for valid API keys (but allow server to start without them)
        if not validate_api_keys(manager):
            logger.warning("No valid API keys found - server will start but AI functionality will be limited")
        
        # Check for admin password (but allow server to start without it)
        if not validate_admin_password(manager):
            logger.warning("No admin password set - server will start but security will be limited")
        
        logger.info("Server requirements validation completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate server requirements: {e}")
        return False

def manage_keys(manager, keychange: bool = False) -> bool:
    """
    Enhanced key management function with admin password.
    
    Args:
        manager: MultiKeyManager instance
        keychange: Whether to force key change
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("The Gold Box - Starting Key Management...")
        
        # Check if keychange flag is set or no key file exists
        if keychange or not manager.key_file.exists():
            logger.info("Running key setup wizard...")
            if manager.interactive_setup():
                # Save configuration (password is already set in manager)
                if not manager.save_keys(manager.keys_data):
                    logger.error("Failed to save updated keys")
                    return False
            else:
                logger.error("Key setup cancelled or failed")
                return False
        else:
            logger.info("Loading API keys and admin password...")
            if not manager.load_keys():
                logger.error("Failed to load keys")
                return False
        
        # Load keys into environment variables (only if keys exist)
        if hasattr(manager, 'keys_data') and manager.keys_data:
            if not manager.set_environment_variables():
                logger.error("Failed to load API keys")
                return False
            logger.info("API keys loaded successfully")
        else:
            logger.info("No API keys to load - continuing without keys")
        
        return True
        
    except Exception as e:
        logger.error(f"Key management failed: {e}")
        return False

def manage_admin_password(manager) -> bool:
    """
    Admin password management function.
    
    Args:
        manager: MultiKeyManager instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("The Gold Box - Admin Password Setup")
        logger.info("=" * 50)
        
        if not manager.get_password_status():
            logger.info("No admin password set. Setting up admin password now...")
            if manager.set_password():
                logger.info("Admin password set successfully")
                return True
            else:
                logger.error("Failed to set admin password")
                return False
        else:
            logger.info("Admin password already configured")
            return True
            
    except Exception as e:
        logger.error(f"Admin password management failed: {e}")
        return False

def get_configured_providers(manager) -> list:
    """
    Get list of configured providers with API keys from already loaded data.
    
    Args:
        manager: MultiKeyManager instance
        
    Returns:
        List of configured provider dictionaries
    """
    try:
        # Use the global manager that's already loaded during server startup
        # Don't load from file - just check what's already in memory
        if hasattr(manager, 'keys_data') and manager.keys_data:
            configured_providers = []
            for provider_id, key_value in manager.keys_data.items():
                if key_value and key_value.strip():  # Only include providers with non-empty keys
                    provider_info = manager.provider_manager.get_provider(provider_id)
                    if provider_info:
                        provider_name = provider_info.get('name', provider_id.replace('_', ' ').title())
                    else:
                        provider_name = provider_id.replace('_', ' ').title()
                    configured_providers.append({
                        'provider_id': provider_id,
                        'provider_name': provider_name,
                        'has_key': True
                    })
            return configured_providers
        return []
    except Exception as e:
        logger.error(f"Error getting configured providers: {e}")
        return []

def validate_startup_environment(config: Dict[str, Any]) -> bool:
    """
    Validate the startup environment and configuration.
    
    Args:
        config: Server configuration dictionary
        
    Returns:
        True if environment is valid, False otherwise
    """
    try:
        # Validate port availability
        available_port = find_available_port(config['GOLD_BOX_PORT'])
        if not available_port:
            logger.error(f"No available ports found starting from {config['GOLD_BOX_PORT']}")
            return False
        
        # Validate CORS configuration
        if not config['CORS_ORIGINS']:
            logger.warning("No CORS origins configured")
        else:
            logger.info(f"CORS configured for {len(config['CORS_ORIGINS'])} origins")
        
        # Validate logging configuration
        if not config.get('LOG_FILE'):
            logger.warning("No log file configured")
        
        logger.info("Startup environment validation completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate startup environment: {e}")
        return False
