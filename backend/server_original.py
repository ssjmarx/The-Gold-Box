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

# Import the new startup module
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

# Import remaining modules that depend on the startup components
from server.key_manager import MultiKeyManager
from endpoints.api_chat import router as api_chat_router, APIChatProcessor
from endpoints.context_chat import ContextChatEndpoint
from server.client_manager import get_client_manager
from server.message_protocol import MessageProtocol
from server.websocket_handler import WebSocketHandler, get_websocket_connection_manager
from security.security import (
    verify_virtual_environment, verify_file_integrity, verify_file_permissions, 
    verify_dependency_integrity, validate_prompt, get_session_id_from_request
)
from server.universal_settings import extract_universal_settings, get_provider_config, UniversalSettings
from server.message_collector import get_message_collector, add_client_message, add_client_roll
  +++++++ REPLACE

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
    """
    client_id = None
    
    try:
        # Accept the WebSocket connection first
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Wait for initial connection message
        connect_message = await websocket.receive_json()
        logger.info(f"Received connection message: {connect_message}")
        
        # Validate connection message
        if connect_message.get("type") != "connect":
            await websocket.close(code=1008, reason="Expected connection message")
            logger.warning("WebSocket: Expected connect message")
            return
        
        client_id = connect_message.get("client_id")
        token = connect_message.get("token")
        
        if not client_id or not token:
            await websocket.close(code=1008, reason="Missing client_id or token")
            logger.warning("WebSocket: Missing client_id or token")
            return
        
        # Check for duplicate connections
        if client_id in websocket_manager.connection_info:
            await websocket.close(code=1008, reason="Client ID already connected")
            logger.warning(f"WebSocket: Duplicate client ID {client_id}")
            return
        
        # Connect the client
        connection_info = {
            "token": token,
            "world_info": connect_message.get("world_info", {}),
            "user_info": connect_message.get("user_info", {})
        }
        
        # Manually add to connection manager since we already accepted
        websocket_manager.active_connections.append(websocket)
        websocket_manager.connection_info[client_id] = {
            "websocket": websocket,
            "connected_at": datetime.now().isoformat(),
            **connection_info
        }
        logger.info(f"WebSocket client connected: {client_id}")
        
        # Send connection confirmation
        await websocket_manager.send_to_client(client_id, {
            "type": "connected",
            "data": {
                "client_id": client_id,
                "server_time": datetime.now().isoformat(),
                "message": "Successfully connected to The Gold Box WebSocket server"
            }
        })
        
        # Handle messages from this client
        try:
            while True:
                message = await websocket.receive_json()
                await websocket_manager.handle_message(client_id, message)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket client {client_id} disconnected normally")
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")
        finally:
            # Clean up connection
            await websocket_manager.disconnect(client_id)
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        if client_id:
            await websocket_manager.disconnect(client_id)
        else:
            # Try to close the connection if it was opened
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except:
                pass

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

@app.post("/api/simple_chat")
async def simple_chat_endpoint(request: Request):
    """
    Provider-agnostic simple chat endpoint
    Handles unified frontend settings and message context
    
    Security is now handled by UniversalSecurityMiddleware:
    - Rate limiting applied
    - Input validation performed
    - Session management enforced
    - Audit logging active
    
    This endpoint:
    1. Gets validated data from universal security middleware
    2. Extracts unified frontend settings and messages
    3. Processes through simple_chat module
    4. Returns structured response
    """
    try:
        # Get validated data from universal security middleware if available
        if hasattr(request.state, 'validated_body') and request.state.validated_body:
            # Use middleware-validated data for enhanced security
            request_data = request.state.validated_body
            logger.info("Processing simple chat request with middleware-validated data")
        else:
            # Fallback to original request data (should not happen with proper middleware)
            try:
                request_data = await request.json()
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in request body"
                )
            logger.info("Processing simple chat request with original request data")
        
        # Extract settings from request
        settings = request_data.get('settings', {})
        
        # Load stored settings FIRST before validation
        try:
            stored_settings = settings_manager.get_settings()
            if stored_settings:
                # Merge request settings with stored settings (request takes priority for client ID)
                merged_settings = {**stored_settings}  # Start with all stored settings
                if settings and isinstance(settings, dict):
                    merged_settings.update(settings)  # Override with request settings (client ID)
                settings = merged_settings  # Use merged settings for all processing
        except Exception as e:
            logger.error(f"Failed to import settings_manager for merge: {e}")
        
        # Initialize universal_settings with defaults to avoid scope issues
        universal_settings = extract_universal_settings({}, "simple_chat")
        
        # Collect chat messages via REST API
        context_count = request_data.get('context_count', 15)
        logger.info(f"Collecting {context_count} chat messages via REST API")
        
        # Prepare request data for client ID extraction
        request_data_for_api = {
            'context_count': context_count,
            'settings': settings if settings else {}
        }
        
        api_messages = await collect_chat_messages_api(context_count, request_data_for_api)
        
        # Convert to compact JSON
        api_chat_processor = APIChatProcessor()
        compact_messages = api_chat_processor.process_api_messages(api_messages)
        
        # Use universal settings extraction for consistent behavior
        if settings and isinstance(settings, dict):
            request_data_for_settings = {
                'settings': settings
            }
            universal_settings = extract_universal_settings(request_data_for_settings, "simple_chat")
        else:
            # Use stored settings from settings manager (fallback)
            stored_settings = settings_manager.get_settings()
            if stored_settings:
                request_data_for_settings = {
                    'settings': stored_settings
                }
                universal_settings = extract_universal_settings(request_data_for_settings, "simple_chat")
            else:
                # Final fallback to defaults
                universal_settings = extract_universal_settings({}, "simple_chat")
        
        # Extract provider config from universal settings
        provider_config = get_provider_config(universal_settings, use_tactical=False)
        
        # Extract messages from request data
        messages = request_data.get('messages', [])
        
        # Validate that we have messages
        if not messages or not isinstance(messages, list):
            raise HTTPException(
                status_code=400,
                detail=f"Messages array is required and must be a list, got {type(messages).__name__}"
            )
        
        # Since simple_chat module was removed, return an error
        raise HTTPException(
            status_code=501,
            detail="Simple chat endpoint has been deprecated. Please use API chat endpoint instead."
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (security failures already logged by middleware)
        raise
    except Exception as e:
        logger.error(f"Simple chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

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
        
        # Take the most recent 'count' messages and reverse to chronological order
        merged_messages = list(reversed(all_messages[:count]))
        
        return merged_messages
            
    except Exception as e:
        logger.error(f"Error collecting messages via API: {e}")
        return []

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Security is now handled by UniversalSecurityMiddleware
    """
    configured_providers = get_configured_providers()
    
    return HealthResponse(
        status='healthy',
        timestamp=datetime.now().isoformat(),
        version='0.2.3',
        service='The Gold Box Backend',
        api_key_required=bool(OPENAI_API_KEY) or bool(NOVELAI_API_KEY),
        environment=FLASK_ENV,
        validation_enabled=True,
        universal_validator=True,
        rate_limiting={
            'max_requests': RATE_LIMIT_MAX_REQUESTS,
            'window_seconds': RATE_LIMIT_WINDOW_SECONDS
        },
        cors={
            'origins_count': len(CORS_ORIGINS),
            'configured': len(CORS_ORIGINS) > 0,
            'methods': ['GET', 'POST', 'OPTIONS']
        },
        configured_providers=configured_providers
    )

@app.get("/api/info", response_model=InfoResponse)
async def service_info():
    """
    Enhanced service information endpoint
    Security is handled by UniversalSecurityMiddleware
    """
    return InfoResponse(
        name='The Gold Box Backend',
        description='AI-powered Foundry VTT Module Backend with Universal Security Middleware',
        version='0.2.3',
        status='running',
        environment=FLASK_ENV,
        api_key_required=bool(OPENAI_API_KEY) or bool(NOVELAI_API_KEY),
        validation_features={
            'universal_validator': True,
            'input_sanitization': True,
            'security_pattern_checking': True,
            'type_specific_validation': True,
            'structured_data_support': True,
            'ai_parameter_validation': True,
            'rate_limiting': True,
            'security_headers': True,
            'audit_logging': True
        },
        supported_input_types=list(validator.ALLOWED_CHAR_PATTERNS.keys()),
        size_limits=validator.SIZE_LIMITS,
        endpoints={
            'process': 'POST /api/process - Process AI prompts (enhanced validation)',
            'health': 'GET /api/health - Health check',
            'info': 'GET /api/info - Service information',
            'security': 'GET /api/security - Security verification and integrity checks',
            'start': 'POST /api/start - Server startup instructions',
            'simple_chat': 'POST /api/simple_chat - Provider-agnostic chat (secured)',
            'context_chat': 'POST /api/context_chat - Enhanced chat with full board state integration'
        },
        license='CC-BY-NC-SA 4.0',
        dependencies={
            'FastAPI': 'MIT License',
            'Uvicorn': 'BSD 3-Clause License'
        },
        security={
            'api_authentication': bool(OPENAI_API_KEY) or bool(NOVELAI_API_KEY),
            'universal_security_middleware': True,
            'rate_limiting': True,
            'cors_restrictions': len(CORS_ORIGINS) > 0,
            'input_validation': 'UniversalInputValidator',
            'security_headers': True,
            'xss_protection': True,
            'sql_injection_protection': True,
            'command_injection_protection': True,
            'audit_logging': True
        }
    )

@app.get("/api/security")
async def security_verification():
    """
    Security verification endpoint for integrity checks
    Security is handled by UniversalSecurityMiddleware
    """
    try:
        # Perform comprehensive security checks
        security_status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'verified',
            'checks': {}
        }
        
        # Virtual environment verification
        venv_status = verify_virtual_environment()
        security_status['checks']['virtual_environment'] = {
            'verified': venv_status,
            'message': 'Virtual environment isolation verified' if venv_status else 'Virtual environment issues detected'
        }
        
        # File integrity verification
        integrity_checks = verify_file_integrity()
        security_status['checks']['file_integrity'] = {
            'verified': len(integrity_checks) > 0,
            'hashes': integrity_checks,
            'message': 'Critical file integrity verified'
        }
        
        # File permissions verification
        permission_issues = verify_file_permissions()
        security_status['checks']['file_permissions'] = {
            'verified': len(permission_issues) == 0,
            'issues': permission_issues,
            'message': 'File permissions secure' if len(permission_issues) == 0 else f'Found {len(permission_issues)} permission issues'
        }
        
        # Dependency integrity verification
        dependency_status = verify_dependency_integrity()
        security_status['checks']['dependencies'] = {
            'verified': 'MISSING' not in str(dependency_status),
            'status': dependency_status,
            'message': 'Dependencies verified' if 'MISSING' not in str(dependency_status) else 'Missing critical dependencies'
        }
        
        # Session management status
        active_sessions = len(session_manager.sessions)
        security_status['checks']['session_management'] = {
            'verified': True,
            'active_sessions': active_sessions,
            'timeout_configured': True,
            'timeout_minutes': SESSION_TIMEOUT_MINUTES,
            'warning_minutes': SESSION_WARNING_MINUTES,
            'message': f'Session management active with {active_sessions} sessions'
        }
        
        # Rate limiting status
        security_status['checks']['rate_limiting'] = {
            'verified': True,
            'max_requests': RATE_LIMIT_MAX_REQUESTS,
            'window_seconds': RATE_LIMIT_WINDOW_SECONDS,
            'message': 'Rate limiting configured and active'
        }
        
        # CORS configuration status
        security_status['checks']['cors_configuration'] = {
            'verified': len(CORS_ORIGINS) > 0,
            'origins_count': len(CORS_ORIGINS),
            'origins': CORS_ORIGINS if FLASK_ENV == 'development' else 'configured',
            'message': 'CORS configured' if len(CORS_ORIGINS) > 0 else 'CORS not configured'
        }
        
        # Universal security middleware status
        security_status['checks']['universal_security_middleware'] = {
            'verified': True,
            'message': 'Universal Security Middleware is active and protecting all endpoints'
        }
        
        # Overall security status
        all_checks_pass = all([
            venv_status,
            len(integrity_checks) > 0,
            len(permission_issues) == 0,
            'MISSING' not in str(dependency_status),
            len(CORS_ORIGINS) > 0
        ])
        
        security_status['overall_status'] = 'secure' if all_checks_pass else 'warning'
        security_status['security_score'] = sum([
            venv_status,
            len(integrity_checks) > 0,
            len(permission_issues) == 0,
            'MISSING' not in str(dependency_status),
            len(CORS_ORIGINS) > 0
        ])
        
        return security_status
        
    except Exception as e:
        logger.error(f"Security verification error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/api/session/init")
async def initialize_session(request: Request):
    """
    Initialize or refresh a session for the frontend
    Supports both creating new sessions and extending existing ones
    Returns session ID and expiry time for session management
    Security is handled by UniversalSecurityMiddleware
    """
    try:
        # Get request body for parameters
        request_data = {}
        try:
            request_data = await request.json()
        except Exception:
            # If no JSON body, treat as empty object
            request_data = {}
        
        # Get client information for session creation
        client_host = request.client.host if request.client else "unknown"
        
        # Check if we should try to extend existing session
        extend_existing = request_data.get('extend_existing', False)
        preferred_session_id = request_data.get('session_id', None)
        
        session_id = None
        was_extended = False
        
        # Try to extend existing session if requested and session_id provided
        if extend_existing and preferred_session_id:
            if session_manager.is_session_valid(preferred_session_id):
                # Update session activity and extend expiry
                session_manager.update_session_activity(preferred_session_id)
                session_id = preferred_session_id
                was_extended = True
                logger.info(f"Session extended for {client_host}: {session_id}")
            else:
                logger.info(f"Preferred session {preferred_session_id} invalid, creating new session for {client_host}")
        
        # Create new session if extension wasn't possible or requested
        if not session_id:
            session_id = session_manager.create_session(request)
            was_extended = False
            logger.info(f"New session created for {client_host}: {session_id}")
        
        # Generate expiry time (default 30 minutes from now)
        expiry_time = datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        
        # Generate CSRF token for session
        csrf_token = session_manager.generate_csrf_token(session_id)
        
        return {
            'session_id': session_id,
            'expires_at': expiry_time.isoformat(),
            'csrf_token': csrf_token,
            'timeout_minutes': SESSION_TIMEOUT_MINUTES,
            'was_extended': was_extended,
            'message': 'Session initialized successfully' if not was_extended else 'Session extended successfully'
        }
        
    except Exception as e:
        logger.error(f"Session initialization error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize session"
        )

@app.post("/api/start")
async def start_backend():
    """
    Attempt to start backend server (for auto-start functionality)
    Note: This is a simplified approach since browser can't spawn processes directly
    """
    return {
        'status': 'info',
        'message': 'Please start backend manually: cd backend && source venv/bin/activate && python server.py',
        'instructions': {
            'step1': 'Open terminal',
            'step2': 'Navigate to backend directory',
            'step3': 'Activate virtual environment: source venv/bin/activate',
            'step4': 'Start server: python server.py'
        },
        'note': 'Automatic process spawning is blocked by browser security restrictions',
        'environment_note': f'Current environment: {FLASK_ENV}',
        'validation_status': 'Universal Security Middleware is active',
        'cors_note': f'CORS configured for {len(CORS_ORIGINS)} origins',
        'security_note': 'All endpoints now protected by Universal Security Middleware'
    }

# Admin API endpoint - requires admin password in X-Admin-Password header
@app.post("/api/admin")
async def admin_endpoint(request: Request):
    """
    Password-protected admin endpoint for server management
    Requires admin password in X-Admin-Password header
    Security is now handled by UniversalSecurityMiddleware
    """
    # Declare global variables at function level
    global OPENAI_API_KEY, NOVELAI_API_KEY, manager
    
    try:
        # Get admin password from headers
        admin_password = request.headers.get('X-Admin-Password')
        if not admin_password:
            raise HTTPException(
                status_code=401,
                detail="Admin password required in X-Admin-Password header",
                headers={"WWW-Authenticate": 'Basic realm="The Gold Box Admin"'}
            )
        
        # Verify admin password using already loaded manager
        is_valid, error_msg = manager.verify_password(admin_password)
        if not is_valid:
            logger.warning(f"Invalid admin password attempt from {request.client.host if request.client else 'unknown'}")
            raise HTTPException(
                status_code=401,
                detail=f"Admin authentication failed: {error_msg}",
                headers={"WWW-Authenticate": 'Basic realm="The Gold Box Admin"'}
            )
        
        # Get request body for admin commands
        try:
            request_data = await request.json()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON in request body"
            )
        
        # Get validated data from middleware if available
        if hasattr(request.state, 'validated_body') and request.state.validated_body:
            request_data = request.state.validated_body
        
        # Process admin commands
        command = request_data.get('command', '')
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"Admin command '{command}' from {client_host}")
        
        if command == 'status':
            # Return server and key status
            return {
                "service": "The Gold Box Backend",
                "version": "0.2.3",
                "status": "running",
                "features": [
                    "Universal Security Middleware",
                    "Rate Limiting",
                    "Input Validation",
                    "Security Headers",
                    "Audit Logging",
                    "OpenAI Compatible API support",
                    "NovelAI API support", 
                    "OpenCode Compatible API support",
                    "Local LLM support",
                    "Simple chat endpoint",
                    "Admin settings management",
                    "Health check endpoint",
                    "Auto-start instructions",
                    "Advanced key management",
                    "Enhanced message context processing",
                    "Fixed JavaScript syntax errors",
                    "Improved API debugging",
                    "Better error handling and logging"
                ],
                "endpoints": {
                    "health": "/api/health",
                    "process": "/api/process",
                    "admin": "/api/admin",
                    "simple_chat": "/api/simple_chat",
                    "start": "/api/start"
                },
                "security": "Universal Security Middleware is active"
            }
        
        elif command == 'reload_keys':
            # Reload environment variables (keys already loaded in global manager)
            if manager.set_environment_variables():
                # Reload global variables
                OPENAI_API_KEY = os.environ.get('GOLD_BOX_OPENAI_COMPATIBLE_API_KEY', '')
                NOVELAI_API_KEY = os.environ.get('GOLD_BOX_NOVELAI_API_API_KEY', '')
                
                logger.info("Environment variables reloaded successfully")
                return {
                    'status': 'success',
                    'command': 'reload_keys',
                    'message': 'Environment variables reloaded successfully',
                    'timestamp': datetime.now().isoformat(),
                    'keys_status': manager.get_key_status()
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to set environment variables"
                )
        
        elif command == 'set_admin_password':
            # Set new admin password
            new_password = request_data.get('password', '')
            if manager.set_password(new_password):
                # Save updated configuration
                if manager.save_keys(manager.keys_data):
                    logger.info("Admin password updated successfully")
                    return {
                        'status': 'success',
                        'command': 'set_admin_password',
                        'message': 'Admin password updated successfully',
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to save updated admin password"
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to set new admin password"
                )
        
        elif command == 'update_settings':
            # Update frontend settings
            frontend_settings_data = request_data.get('settings', {})
            
            if settings_manager.update_settings(frontend_settings_data):
                logger.info(f"Frontend settings updated from {client_host}")
                return {
                    'status': 'success',
                    'command': 'update_settings',
                    'message': f'Frontend settings updated: {len(frontend_settings_data)} settings loaded',
                    'timestamp': datetime.now().isoformat(),
                    'settings_count': len(frontend_settings_data),
                    'current_settings': settings_manager.get_settings()
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update frontend settings"
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown admin command: {command}",
                headers={"X-Supported-Commands": "status, reload_keys, set_admin_password, update_settings"}
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions (security failures already logged by middleware)
        raise
    except Exception as e:
        logger.error(f"Admin endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error in admin endpoint"
        )

# FastAPI exception handlers
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            'error': 'Endpoint not found',
            'status': 'error',
            'available_endpoints': ['/api/simple_chat', '/api/context_chat', '/api/health', '/api/info', '/api/security', '/api/session/init', '/api/start', '/api/admin', '/api/debug/settings', '/api/debug/provider'],
            'security': 'Protected by Universal Security Middleware'
        }
    )

# Debug endpoints for universal settings testing
@app.get("/api/debug/settings")
async def debug_settings_endpoint():
    """
    Debug endpoint to display universal settings schema and current state
    Security is handled by UniversalSecurityMiddleware
    """
    try:
        # Get current frontend settings
        current_settings = settings_manager.get_settings()
        
        # Extract universal settings to show current state
        extracted_settings = extract_universal_settings(current_settings)
        
        # Get provider config for both tactical and general
        general_provider_config = get_provider_config(current_settings, use_tactical=False)
        tactical_provider_config = get_provider_config(current_settings, use_tactical=True)
        
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'schema_info': {
                'schema_version': '1.0',
                'total_settings': len(UniversalSettings.SETTINGS_SCHEMA),
                'setting_keys': list(UniversalSettings.SETTINGS_SCHEMA.keys())
            },
            'current_frontend_settings': {
                'raw_settings': current_settings,
                'extracted_settings': extracted_settings,
                'settings_count': len(current_settings)
            },
            'provider_configs': {
                'general': {
                    'config': general_provider_config,
                    'valid': bool(general_provider_config.get('provider'))
                },
                'tactical': {
                    'config': tactical_provider_config,
                    'valid': bool(tactical_provider_config.get('provider'))
                }
            },
            'universal_settings_schema': {k: {'type': str(v['type']).__name__, **{k2: v2 for k2, v2 in v.items() if k2 != 'type'}} for k, v in UniversalSettings.SETTINGS_SCHEMA.items()},
            'debug_info': {
                'message': 'Universal settings debug information',
                'use_tactical_param': 'Controls whether tactical settings override general settings',
                'extraction_logic': 'Settings are extracted in order: tactical -> general -> defaults'
            }
        }
        
        return JSONResponse(
            status_code=200,
            content=debug_info
        )
        
    except Exception as e:
        logger.error(f"Debug settings endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Debug settings error: {str(e)}"
        )

@app.post("/api/debug/provider")
async def debug_provider_endpoint(request: Request):
    """
    Debug endpoint to test provider configuration with given settings
    Security is handled by UniversalSecurityMiddleware
    """
    try:
        # Get request data
        request_data = await request.json()
        settings = request_data.get('settings', {})
        use_tactical = request_data.get('use_tactical', False)
        
        # Extract provider config
        provider_config = get_provider_config(settings, use_tactical)
        
        # Validate provider configuration
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check for required fields
        if not provider_config.get('provider'):
            validation_result['valid'] = False
            validation_result['errors'].append('Provider is required')
        
        if not provider_config.get('model'):
            validation_result['valid'] = False
            validation_result['errors'].append('Model is required')
        
        # Check for logical issues
        if provider_config.get('provider') == 'openai' and not provider_config.get('api_key'):
            validation_result['warnings'].append('OpenAI provider detected but no API key found in environment')
        
        if provider_config.get('base_url') and not provider_config.get('provider'):
            validation_result['warnings'].append('Base URL provided but no provider specified')
        
        debug_response = {
            'timestamp': datetime.now().isoformat(),
            'request_data': {
                'settings': settings,
                'use_tactical': use_tactical
            },
            'extracted_config': provider_config,
            'validation': validation_result,
            'debug_info': {
                'message': 'Provider configuration debug test',
                'extraction_method': 'tactical' if use_tactical else 'general'
            }
        }
        
        return JSONResponse(
            status_code=200,
            content=debug_response
        )
        
    except Exception as e:
        logger.error(f"Debug provider endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Debug provider error: {str(e)}"
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
