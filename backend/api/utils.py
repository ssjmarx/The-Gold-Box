#!/usr/bin/env python3
"""
Shared utilities for API endpoints
Common functions used across multiple endpoint modules
"""

import logging
import os
import asyncio
import json
import requests
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def verify_api_key(request):
    """
    Enhanced API key verification for multiple services using service factory
    Returns (is_valid: bool, error_message: str)
    """
    # Get API key from headers
    provided_key = request.headers.get('X-API-Key')
    
    # Check if API key is provided
    if not provided_key:
        logger.warning(f"Missing API key from {request.client.host if request.client else 'unknown'}")
        return False, "API key required"
    
    # Use service factory to get key manager and provider manager
    try:
        from services.system_services.service_factory import get_key_manager, get_provider_manager
        
        key_manager = get_key_manager()
        provider_manager = get_provider_manager()
        
        if not hasattr(key_manager, 'keys_data') or not key_manager.keys_data:
            return False, "No API keys configured on server"
        
        # Check if provided key matches any configured key
        valid_keys = [key for key in key_manager.keys_data.values() if key]
        
        if not valid_keys:
            return False, "No API keys configured on server"
        
        if provided_key not in valid_keys:
            logger.warning(f"Invalid API key from {request.client.host if request.client else 'unknown'}")
            return False, "Invalid API key"
        
        # Determine which service this key belongs to
        service_name = "Unknown"
        for provider_id, key_value in key_manager.keys_data.items():
            if provided_key == key_value:
                provider_info = provider_manager.get_provider(provider_id)
                if provider_info:
                    service_name = provider_info.get('name', provider_id.replace('_', ' ').title())
                else:
                    service_name = provider_id.replace('_', ' ').title()
                break
        
        logger.info(f"Valid {service_name} API key from {request.client.host if request.client else 'unknown'}")
        return True, None
        
    except (RuntimeError, KeyError, AttributeError) as e:
        logger.error(f"Service configuration error during API key verification: {e}")
        return False, f"Service configuration error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during API key verification: {e}")
        raise

def get_configured_providers() -> List[Dict[str, Any]]:
    """Get list of configured providers with API keys using service factory"""
    try:
        from services.system_services.service_factory import get_key_manager, get_provider_manager
        
        key_manager = get_key_manager()
        provider_manager = get_provider_manager()
        
        if hasattr(key_manager, 'keys_data') and key_manager.keys_data:
            configured_providers = []
            for provider_id, key_value in key_manager.keys_data.items():
                if key_value and key_value.strip():  # Only include providers with non-empty keys
                    provider_info = provider_manager.get_provider(provider_id)
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
    except (RuntimeError, KeyError, AttributeError) as e:
        logger.error(f"Service configuration error getting providers: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting providers: {e}")
        raise

# Duplicate collect_chat_messages_api function removed - now using WebSocket-only message collection
