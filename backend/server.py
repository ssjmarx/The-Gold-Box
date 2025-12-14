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
from shared.startup import run_server_startup

# Get startup components
startup = run_server_startup()
components = startup.get_startup_components()

# Extract components for easier access
config = components['config']
security_components = components['security_components']
global_services = components['global_services']
app = components['app']
manager = components['manager']

# Use config directly - no redundant global variables
logger = logging.getLogger(__name__)

# Import service factory functions for consistent access patterns
from services.system_services.service_factory import (
    get_session_manager, get_websocket_manager, get_settings_manager,
    get_rate_limiter, get_validator
)

# Get absolute path to backend directory (where server.py is located)
BACKEND_DIR = Path(__file__).parent.absolute()

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path based on backend directory.
    This ensures consistent file operations regardless of where script is called from.
    """
    return (BACKEND_DIR / relative_path).resolve()

# Import remaining modules that depend on startup components
from api.api_chat import router as api_chat_router
from api.health import create_health_router
from api.system import create_system_router
from api.session import create_session_router
from api.admin import create_admin_router
from services.system_services.service_factory import get_client_manager
from shared.core.message_protocol import MessageProtocol
from services.system_services.websocket_handler import WebSocketHandler
from shared.security.security import (
    verify_virtual_environment, verify_file_integrity, verify_file_permissions, 
    verify_dependency_integrity, validate_prompt, get_session_id_from_request
)
from services.system_services.universal_settings import extract_universal_settings, get_provider_config, UniversalSettings
from services.message_services.message_collector import add_client_message, add_client_roll

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
health_router = create_health_router(config)
system_router = create_system_router(config)
session_router = create_session_router(config)
admin_router = create_admin_router(config)

# Include routers in app
app.include_router(health_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    FastAPI WebSocket endpoint for The Gold Box
    Handles real-time communication with Foundry VTT frontend
    Now uses WebSocketHandler module
    """
    # Get websocket manager from service factory
    ws_manager = get_websocket_manager()
    
    # Create WebSocket handler instance
    ws_handler = WebSocketHandler(ws_manager)
    
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

# Relay server functionality removed - using native WebSocket server instead
# All relay server dependencies have been eliminated in favor of direct WebSocket communication

# API key verification moved to api/utils.py to eliminate duplication

# get_configured_providers moved to api/utils.py to eliminate duplication

# Simple chat endpoint removed - deprecated in favor of API chat endpoint

# Duplicate collect_chat_messages_api function removed - now using WebSocket-only message collection

# Old endpoint implementations removed - now handled by routers

# FastAPI exception handlers
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            'error': 'Endpoint not found',
            'status': 'error',
            'available_endpoints': ['/api/health', '/api/session/init', '/api/start', '/api/admin'],
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
