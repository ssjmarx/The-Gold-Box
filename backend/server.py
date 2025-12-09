#!/usr/bin/env python3
"""
The Gold Box - Python Backend Server
AI-powered Foundry VTT Module Backend

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
Dependencies: FastAPI (MIT), Uvicorn (BSD 3-Clause)
"""

from fastapi import FastAPI, Request, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import logging
import sys
import time
import os
import re
import html
import hashlib
import subprocess
import stat
import getpass
import json
import base64
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from pydantic import BaseModel, Field

# Import startup module
from startup import run_server_startup

# Get startup components
startup = run_server_startup()
components = startup.get_startup_components()

# Extract components for easier access
config = components['config']
security_components = components['security_components']
global_services = components['global_services']
app = components['app']
manager = components['manager']

# Set up global variables for backward compatibility
OPENAI_API_KEY = config['OPENAI_API_KEY']
NOVELAI_API_KEY = config['NOVELAI_API_KEY']
GOLD_BOX_PORT = config['GOLD_BOX_PORT']
FLASK_DEBUG = config['FLASK_DEBUG']
FLASK_ENV = config['FLASK_ENV']
LOG_LEVEL = config['LOG_LEVEL']
LOG_FILE = config['LOG_FILE']
RATE_LIMIT_MAX_REQUESTS = config['RATE_LIMIT_MAX_REQUESTS']
RATE_LIMIT_WINDOW_SECONDS = config['RATE_LIMIT_WINDOW_SECONDS']
SESSION_TIMEOUT_MINUTES = config['SESSION_TIMEOUT_MINUTES']
SESSION_WARNING_MINUTES = config['SESSION_WARNING_MINUTES']
CORS_ORIGINS = config['CORS_ORIGINS']
logger = logging.getLogger(__name__)

# Extract security components for backward compatibility
rate_limiter = security_components['rate_limiter']
session_manager = security_components['session_manager']
validator = security_components['validator']

# Extract global services for backward compatibility
websocket_manager = global_services['websocket_manager']
settings_manager = global_services['settings_manager']

# Get absolute path to backend directory (where server.py is located)
BACKEND_DIR = Path(__file__).parent.absolute()

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path based on backend directory.
    This ensures consistent file operations regardless of where script is called from.
    """
    return (BACKEND_DIR / relative_path).resolve()

# Import remaining modules that depend on startup components
from server.key_manager import MultiKeyManager
from endpoints.api_chat import router as api_chat_router, APIChatProcessor
from endpoints.context_chat import ContextChatEndpoint
from endpoints.health import create_health_router
from endpoints.system import create_system_router
from endpoints.session import create_session_router
from endpoints.admin import create_admin_router
from server.client_manager import get_client_manager
from server.message_protocol import MessageProtocol
from server.websocket_handler import WebSocketHandler, get_websocket_connection_manager
from security.security import (
    verify_virtual_environment, verify_file_integrity, verify_file_permissions, 
    verify_dependency_integrity, validate_prompt, get_session_id_from_request
)
from server.universal_settings import extract_universal_settings, get_provider_config, UniversalSettings
from server.message_collector import get_message_collector, add_client_message, add_client_roll

# Pydantic models for FastAPI request/response validation
class PromptRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to send to AI", min_length=1, max_length=10000)
    max_tokens: Optional[int] = Field(100, description="Maximum tokens to generate", ge=1, le=8192)
    temperature: Optional[float] = Field(0.7, description="Sampling temperature", ge=0.0, le=2.0)
    top_p: Optional[float] = Field(1.0, description="Top-p sampling", ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(0.0, description="Frequency penalty", ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(0.0, description="Presence penalty", ge=-2.0, le=2.0)

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    service: str
    api_key_required: bool
    environment: str
    validation_enabled: bool
    universal_validator: bool
    rate_limiting: Dict[str, int]
    cors: Dict[str, Union[int, List[str], bool]]
    configured_providers: Optional[List[Dict[str, Union[str, bool]]]] = None

class InfoResponse(BaseModel):
    name: str
    description: str
    version: str
    status: str
    environment: str
    api_key_required: bool
    validation_features: Dict[str, bool]
    supported_input_types: List[str]
    size_limits: Dict[str, int]
    endpoints: Dict[str, str]
    license: str
    dependencies: Dict[str, str]
    security: Dict[str, Union[bool, str]]

class ErrorResponse(BaseModel):
    error: str
    status: str = "error"
    validation_step: Optional[str] = None
    received_fields: Optional[List[str]] = None

# Register endpoint routers
health_router = create_health_router(config, manager)
system_router = create_system_router(config)
session_router = create_session_router(session_manager, config)
admin_router = create_admin_router(manager, settings_manager, config)

# Include routers in app
app.include_router(health_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

# Initialize context chat endpoint
context_chat_endpoint = None

def get_context_chat_endpoint():
    """Get or create context chat endpoint instance"""
    global context_chat_endpoint
    if context_chat_endpoint is None:
        # Initialize with real services
        from server.ai_service import get_ai_service
        from endpoints.context_chat import RealFoundryClient, RealAIService
        
        ai_service = get_ai_service()
        real_ai_service = RealAIService(ai_service)
        foundry_client = RealFoundryClient()
        context_chat_endpoint = ContextChatEndpoint(
            ai_service=real_ai_service,
            foundry_client=foundry_client
        )
    return context_chat_endpoint

@app.post("/api/context_chat")
async def context_chat_endpoint_handler(request: Request):
    """
    Enhanced context chat endpoint with full board state integration
    New endpoint: /api/context_chat
    Security is handled by UniversalSecurityMiddleware
    """
    try:
        # Get validated data from middleware if available
        if hasattr(request.state, 'validated_body') and request.state.validated_body:
            request_data = request.state.validated_body
            logger.info("Processing context chat request with middleware-validated data")
        else:
            try:
                request_data = await request.json()
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in request body"
                )
            logger.info("Processing context chat request with original request data")
        
        # Get context chat endpoint instance
        endpoint = get_context_chat_endpoint()
        
        # Process the context chat request
        response = await endpoint.handle_context_chat(request_data)
        
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"Context chat response sent to {client_host}: success")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions (security failures already logged by middleware)
        raise
    except Exception as e:
        logger.error(f"Context chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

def get_websocket_connection_manager():
    """Get the global WebSocket connection manager instance"""
    return websocket_manager

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    FastAPI WebSocket endpoint for The Gold Box
    Handles real-time communication with Foundry VTT frontend
    Now uses WebSocketHandler module
    """
    # Create WebSocket handler instance
    ws_handler = WebSocketHandler(websocket_manager)
    
    # Delegate to WebSocket handler
    await ws_handler.handle_websocket_connection(websocket)

async def start_websocket_chat_handler():
    """Initialize WebSocket chat handler (now using FastAPI built-in WebSocket)"""
    try:
        logger.info("WebSocket endpoint /ws registered with FastAPI")
        logger.info("WebSocket chat handler started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start WebSocket chat handler: {e}")
        return False

async def start_relay_server():
    """Start relay server as a subprocess (deprecated, using WebSocket instead)"""
    logger.info("Relay server is deprecated, using native WebSocket server instead")
    return True

def stop_relay_server():
    """Stop relay server process"""
    global relay_server_process
    relay_server_process = None  # Simplified for new implementation
    logger.info("Relay server stopped")

def verify_api_key(request):
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
    valid_keys = [key for key in [OPENAI_API_KEY, NOVELAI_API_KEY] if key]
    
    if not valid_keys:
        return False, "No API keys configured on server"
    
    # Check if provided key matches any configured key
    if provided_key not in valid_keys:
        logger.warning(f"Invalid API key from {request.client.host if request.client else 'unknown'}")
        return False, "Invalid API key"
    
    # Determine which service this key belongs to
    service_name = "Unknown"
    if provided_key == OPENAI_API_KEY:
        service_name = "OpenAI Compatible"
    elif provided_key == NOVELAI_API_KEY:
        service_name = "NovelAI API"
    
    logger.info(f"Valid {service_name} API key from {request.client.host if request.client else 'unknown'}")
    return True, None

def get_configured_providers():
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

# Simple chat endpoint removed - deprecated in favor of API chat endpoint

async def collect_chat_messages_api(count: int, request_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
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
                    stored_settings = settings_manager.get_settings()
                    if stored_settings:
                        client_id = stored_settings.get('relay client id')
                except:
                    pass
                
                if not client_id:
                    client_id = request_data.get('relayClientId')
        else:
            try:
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

# Old endpoint implementations removed - now handled by routers

# FastAPI exception handlers
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            'error': 'Endpoint not found',
            'status': 'error',
            'available_endpoints': ['/api/context_chat', '/api/health', '/api/session/init', '/api/start', '/api/admin'],
            'security': 'Protected by Universal Security Middleware'
        }
    )

@app.exception_handler(405)
async def method_not_allowed(request: Request, exc):
    return JSONResponse(
        status_code=405,
        content={
            'error': 'Method not allowed',
            'status': 'error',
            'allowed_methods': ['GET', 'POST', 'OPTIONS'],
            'security': 'Protected by Universal Security Middleware'
        }
    )

if __name__ == '__main__':
    # Start the server using the startup module
    startup.start_server()
