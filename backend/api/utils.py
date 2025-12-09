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

def verify_api_key(request, openai_api_key: str, novelai_api_key: str):
    """
    Enhanced API key verification for multiple services
    Returns (is_valid: bool, error_message: str)
    """
    # Get API key from headers
    provided_key = request.headers.get('X-API-Key')
    
    # Check if API key is provided
    if not provided_key:
        logger.warning(f"Missing API key from {request.client.host if request.client else 'unknown'}")
        return False, "API key required"
    
    # Check against all configured keys
    valid_keys = [key for key in [openai_api_key, novelai_api_key] if key]
    
    if not valid_keys:
        return False, "No API keys configured on server"
    
    # Check if provided key matches any configured key
    if provided_key not in valid_keys:
        logger.warning(f"Invalid API key from {request.client.host if request.client else 'unknown'}")
        return False, "Invalid API key"
    
    # Determine which service this key belongs to
    service_name = "Unknown"
    if provided_key == openai_api_key:
        service_name = "OpenAI Compatible"
    elif provided_key == novelai_api_key:
        service_name = "NovelAI API"
    
    logger.info(f"Valid {service_name} API key from {request.client.host if request.client else 'unknown'}")
    return True, None

def get_configured_providers(manager) -> List[Dict[str, Any]]:
    """Get list of configured providers with API keys from already loaded data"""
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

async def collect_chat_messages_api(count: int, request_data: Dict[str, Any] = None, settings_manager=None) -> List[Dict[str, Any]]:
    """Collect recent chat messages and dice rolls via Foundry REST API"""
    try:
        import requests
        
        # Get client ID from unified settings with better fallback handling
        client_id = None
        if request_data:
            settings = request_data.get('settings', {})
            client_id = settings.get('relay client id')
            if not client_id:
                try:
                    if settings_manager:
                        stored_settings = settings_manager.get_settings()
                        if stored_settings:
                            client_id = stored_settings.get('relay client id')
                except:
                    pass
                
                if not client_id:
                    client_id = request_data.get('relayClientId')
        else:
            try:
                if settings_manager:
                    stored_settings = settings_manager.get_settings()
                    if stored_settings:
                        client_id = stored_settings.get('relay client id')
            except:
                pass
        
        # If no client ID provided, try to get one from relay server
        if not client_id:
            try:
                clients_response = requests.get(
                    f"http://localhost:3010/clients",
                    timeout=5
                )
                if clients_response.status_code == 200:
                    clients = clients_response.json()
                    if clients and len(clients) > 0:
                        client_id = clients[0].get('id')
            except Exception:
                pass
        
        # If still no client ID, try some common defaults
        if not client_id:
            fallback_ids = ["foundry-test", "test-client", "default-client"]
            for fallback_id in fallback_ids:
                try:
                    test_response = requests.get(
                        f"http://localhost:3010/chat/messages",
                        params={"clientId": fallback_id, "limit": 1},
                        timeout=3
                    )
                    if test_response.status_code == 200:
                        client_id = fallback_id
                        break
                except:
                    continue
            
            if not client_id:
                client_id = "generated-test-client"
        
        # Get chat messages from relay server with proper authentication
        headers = {}
        headers["x-api-key"] = "local-dev"  # This works for local memory store mode
        
        # Enhanced delay to allow Foundry module to process changes and store them
        await asyncio.sleep(1.0)
        
        # Collect both chat messages AND rolls for complete context
        chat_messages = []
        roll_messages = []
        
        # Get chat messages
        chat_response = requests.get(
            f"http://localhost:3010/messages",
            params={"clientId": client_id, "limit": count, "sort": "timestamp", "order": "desc", "refresh": True},
            headers=headers,
            timeout=5
        )
        
        if chat_response.status_code == 200:
            try:
                response_data = chat_response.json()
                if isinstance(response_data, dict):
                    if 'messages' in response_data:
                        chat_messages = response_data['messages']
                elif isinstance(response_data, list):
                    chat_messages = response_data
            except json.JSONDecodeError:
                pass
        else:
            logger.error(f"Failed to collect chat messages: {chat_response.status_code}")
        
        # Get roll messages
        await asyncio.sleep(0.5)
        
        rolls_response = requests.get(
            f"http://localhost:3010/rolls",
            params={"clientId": client_id, "limit": count, "sort": "timestamp", "order": "desc", "refresh": True},
            headers=headers,
            timeout=5
        )
        
        if rolls_response.status_code == 200:
            try:
                rolls_data = rolls_response.json()
                if isinstance(rolls_data, dict):
                    if 'data' in rolls_data:
                        roll_messages = rolls_data['data']
                    elif 'rolls' in rolls_data:
                        roll_messages = rolls_data['rolls']
                elif isinstance(rolls_data, list):
                    roll_messages = rolls_data
            except json.JSONDecodeError:
                pass
        else:
            logger.error(f"Failed to collect rolls: {rolls_response.status_code}")
        
        # Merge and sort all messages chronologically
        all_messages = []
        
        # Add chat messages with type marker
        for msg in chat_messages:
            msg['_source'] = 'chat'
            msg['_timestamp'] = msg.get('timestamp', 0)
            all_messages.append(msg)
        
        # Add roll messages with type marker
        for roll in roll_messages:
            roll['_source'] = 'roll'
            roll['_timestamp'] = roll.get('timestamp', 0)
            all_messages.append(roll)
        
        # Sort by timestamp (newest first, then we'll reverse for chronological)
        all_messages.sort(key=lambda x: x.get('_timestamp', 0), reverse=True)
        
        # Take most recent 'count' messages and reverse to chronological order
        merged_messages = list(reversed(all_messages[:count]))
        
        return merged_messages
            
    except Exception as e:
        logger.error(f"Error collecting messages via API: {e}")
        return []
