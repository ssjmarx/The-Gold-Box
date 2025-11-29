#!/usr/bin/env python3
"""
The Gold Box - Python Backend Server
AI-powered Foundry VTT Module Backend

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
Dependencies: FastAPI (MIT), Uvicorn (BSD 3-Clause)
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys
import time
import os
import socket
import re
import html
import hashlib
import subprocess
import stat
import getpass
import json
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from pydantic import BaseModel, Field

# Get absolute path to backend directory (where server.py is located)
BACKEND_DIR = Path(__file__).parent.absolute()

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path based on backend directory.
    This ensures consistent file operations regardless of where script is called from.
    """
    return (BACKEND_DIR / relative_path).resolve()

# Get the absolute path to the backend directory (where server.py is located)
from server.key_manager import MultiKeyManager
from endpoints.simple_chat import process_simple_chat
from endpoints.process_chat import router as process_chat_router
from endpoints.api_chat import router as api_chat_router
from endpoints.api_chat import APIChatProcessor
from endpoints.context_chat import ContextChatEndpoint
# Import security module
from security.security import (
    RateLimiter, UniversalInputValidator, 
    UniversalSecurityMiddleware, SECURITY_CONFIG,
    verify_virtual_environment, verify_file_integrity, verify_file_permissions, 
    verify_dependency_integrity, validate_prompt, get_session_id_from_request
)
from security.sessionvalidator import session_validator
# Import universal settings for debug endpoints
from server.universal_settings import extract_universal_settings, get_provider_config, UniversalSettings

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
OPENAI_API_KEY = os.environ.get('GOLD_BOX_OPENAI_COMPATIBLE_API_KEY', '')
NOVELAI_API_KEY = os.environ.get('GOLD_BOX_NOVELAI_API_API_KEY', '')
GOLD_BOX_PORT = int(os.environ.get('GOLD_BOX_PORT', 5000))
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = str(get_absolute_path('server_files/goldbox.log'))

# Rate limiting configuration
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', 5))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('RATE_LIMIT_WINDOW_SECONDS', 60))

# Session timeout configuration
SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 60))  # Increased to 60 minutes
SESSION_WARNING_MINUTES = int(os.environ.get('SESSION_WARNING_MINUTES', 10))  # Increased to 10 minutes

# Configure logging first
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Enhanced CORS configuration with security-focused defaults
def get_cors_origins():
    """
    Get CORS origins based on environment with security-first approach
    In production, this should be explicitly configured via environment variable
    """
    cors_origins_env = os.environ.get('CORS_ORIGINS', '').strip()
    
    if cors_origins_env:
        # Split and clean environment variable origins
        origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
        logger.info(f"Loaded {len(origins)} CORS origins from environment")
        return origins
    
    # Development defaults - only localhost Foundry VTT ports
    if FLASK_ENV == 'development':
        default_origins = [
            'http://localhost:30000', 'http://127.0.0.1:30000',  # Default Foundry VTT
            'http://localhost:30001', 'http://127.0.0.1:30001',  # Common alternative
            'http://localhost:30002', 'http://127.0.0.1:30002',  # Another alternative
        ]
        logger.warning(f"Using development CORS defaults: {default_origins}")
        return default_origins
    
    # Production - provide localhost defaults for direct server testing
    if not cors_origins_env:
        default_origins = [
            'http://localhost:30000', 'http://127.0.0.1:30000',  # Default Foundry VTT
            'http://localhost:30001', 'http://127.0.0.1:30001',  # Common alternative
            'http://localhost:30002', 'http://127.0.0.1:30002',  # Another alternative
        ]
        logger.warning(f"Production mode with no CORS_ORIGINS set, using localhost defaults: {default_origins}")
        return default_origins
    
    logger.error("Production environment requires explicit CORS_ORIGINS configuration")
    return []

# Enhanced CORS configuration
CORS_ORIGINS = get_cors_origins()

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

# Initialize FastAPI app
app = FastAPI(
    title="The Gold Box Backend",
    description="AI-powered Foundry VTT Module Backend",
    version="0.2.3",
    docs_url="/docs" if FLASK_ENV == 'development' else None,
    redoc_url=None
)

# Include process_chat router
app.include_router(process_chat_router)

# Include API chat router
app.include_router(api_chat_router)

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

# Enhanced CORS configuration with security headers (BEFORE security middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Admin-Password", "X-Session-ID"],
    expose_headers=[],
    max_age=86400,
)

# Add Universal Security Middleware AFTER CORS (so it runs after CORS handles OPTIONS)
app.add_middleware(UniversalSecurityMiddleware, security_config=SECURITY_CONFIG)

logger.info(f"CORS configured for {len(CORS_ORIGINS)} origins")
logger.info("Universal Security Middleware integrated")

# Initialize rate limiter with environment variables
rate_limiter = RateLimiter(max_requests=RATE_LIMIT_MAX_REQUESTS, window_seconds=RATE_LIMIT_WINDOW_SECONDS)

# Initialize session manager using global instance
session_manager = session_validator

def find_available_port(start_port=5000, max_attempts=10):
    """
    Find an available port starting from start_port
    Returns first available port or None if none found
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

# Initialize global validator
validator = UniversalInputValidator()

# Global settings dictionary for frontend configuration
frontend_settings = {}

# Global relay server process
relay_server_process = None

async def start_relay_server():
    """Start relay server as a subprocess"""
    global relay_server_process
    
    # Check if Node.js and npm are available
    try:
        # Check for Node.js
        import subprocess
        node_check = subprocess.run(['node', '--version'], 
                                capture_output=True, text=True, timeout=5)
        if node_check.returncode != 0:
            logger.error("Node.js not available - relay server cannot start")
            return False
        
        # Check for npm
        npm_check = subprocess.run(['npm', '--version'], 
                               capture_output=True, text=True, timeout=5)
        if npm_check.returncode != 0:
            logger.error("npm not available - relay server cannot start")
            return False
        
        node_version = node_check.stdout.strip().replace('v', '')
        npm_version = npm_check.stdout.strip()
        logger.info(f"Found Node.js {node_version} and npm {npm_version}")
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Node.js/npm not available: {e}")
        logger.error("Relay server requires Node.js and npm to be installed")
        logger.error("Please run: ./backend.sh (which will auto-install Node.js)")
        return False
    except Exception as e:
        logger.error(f"Error checking Node.js/npm: {e}")
        return False
    
    # Check if relay server is already running
    try:
        import requests
        response = requests.get("http://localhost:3010/api/health", timeout=2)
        if response.status_code == 200:
            logger.info("Relay server already running on port 3010")
            return True
    except:
        logger.info("Relay server not running, starting...")
    
    # Start relay server
    try:
        relay_path = os.path.join(os.path.dirname(__file__), "..", "relay-server")
        if not os.path.exists(relay_path):
            logger.error("Relay server submodule not found. Run: git submodule update --init --recursive")
            return False
        
        logger.info(f"Starting relay server from: {relay_path}")
        
        # Check if package.json exists in relay server
        package_json_path = os.path.join(relay_path, "package.json")
        if not os.path.exists(package_json_path):
            logger.error("relay-server package.json not found")
            return False
        
        # Check if node_modules exists, if not run npm install
        node_modules_path = os.path.join(relay_path, "node_modules")
        if not os.path.exists(node_modules_path):
            logger.info("Installing relay server dependencies...")
            try:
                install_result = subprocess.run(
                    ['npm', 'install'],
                    cwd=relay_path,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                if install_result.returncode != 0:
                    logger.error(f"npm install failed: {install_result.stderr}")
                    return False
                logger.info("Relay server dependencies installed successfully")
            except subprocess.TimeoutExpired:
                logger.error("npm install timed out after 5 minutes")
                return False
            except Exception as e:
                logger.error(f"npm install error: {e}")
                return False
        
        # Set DATABASE_URL environment variable for relay server
        env = os.environ.copy()
        env["DATABASE_URL"] = "sqlite:./relay-server.db"
        env["DB_TYPE"] = "memory"  # Use memory store to bypass authentication for local development
        
        # Start relay server as subprocess
        relay_server_process = subprocess.Popen(
            ["npm", "start"],
            cwd=relay_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        
        # Wait for it to start
        import asyncio
        await asyncio.sleep(5)  # Increased wait time
        
        # Check if it's running
        try:
            response = requests.get("http://localhost:3010/api/health", timeout=2)
            if response.status_code == 200:
                logger.info("Relay server started successfully on port 3010")
                return True
        except:
            pass
        
        # Check if process is still running
        if relay_server_process.poll() is not None:
            stdout, stderr = relay_server_process.communicate()
            logger.error(f"Relay server failed to start:")
            logger.error(f"STDOUT: {stdout.decode() if stdout else 'None'}")
            logger.error(f"STDERR: {stderr.decode() if stderr else 'None'}")
            return False
        
        logger.warning("Relay server may be starting up (health check failed but process is running)")
        return True
        
    except Exception as e:
        logger.error(f"Error starting relay server: {e}")
        return False

def stop_relay_server():
    """Stop relay server process"""
    global relay_server_process
    if relay_server_process:
        try:
            relay_server_process.terminate()
            relay_server_process.wait(timeout=5)
            logger.info("Relay server stopped")
        except subprocess.TimeoutExpired:
            relay_server_process.kill()
            logger.info("Relay server force killed")
        except Exception as e:
            logger.error(f"Error stopping relay server: {e}")
        finally:
            relay_server_process = None

class SettingsManager:
    """Global settings manager for frontend configuration"""
    
    @staticmethod
    def update_settings(new_settings: Dict) -> bool:
        """Update global frontend settings dictionary"""
        try:
            global frontend_settings
            frontend_settings.clear()
            frontend_settings.update(new_settings)
            logger.info(f"Frontend settings updated: {len(frontend_settings)} settings loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to update frontend settings: {e}")
            return False
    
    @staticmethod
    def get_settings() -> Dict:
        """Get current frontend settings"""
        global frontend_settings
        return frontend_settings.copy()
    
    @staticmethod
    def get_setting(key: str, default=None):
        """Get a specific frontend setting"""
        global frontend_settings
        return frontend_settings.get(key, default)
    
    @staticmethod
    def clear_settings():
        """Clear all frontend settings"""
        global frontend_settings
        frontend_settings.clear()
        logger.info("Frontend settings cleared")

# Initialize settings manager
settings_manager = SettingsManager()

# Export settings_manager to server module for other files to import
try:
    import server
    server.settings_manager = settings_manager
    server.get_settings_manager = lambda: settings_manager
except ImportError:
    # This can happen during initial imports, but that's OK
    pass

def manage_keys(keychange=False):
    """Enhanced key management function with admin password"""
    print("The Gold Box - Starting Key Management...")
    
    manager = MultiKeyManager()
    
    # Check if keychange flag is set or no key file exists
    if keychange or not manager.key_file.exists():
        print("Running key setup wizard...")
        if manager.interactive_setup():
            # Save configuration (password is already set in manager)
            if not manager.save_keys(manager.keys_data):
                print("[ERROR] Failed to save updated keys")
                return False
        else:
            print("Key setup cancelled or failed")
            return False
    else:
        print("Loading API keys and admin password...")
        if not manager.load_keys():
            print("Failed to load keys")
            return False
    
    # Load keys into environment variables
    if not manager.set_environment_variables():
        print("Failed to load API keys")
        return False
    
    print("API keys loaded successfully")
    return True

def manage_admin_password(manager):
    """Admin password management function"""
    print("The Gold Box - Admin Password Setup")
    print("=" * 50)
    
    if not manager.get_password_status():
        print("No admin password set. Setting up admin password now...")
        if manager.set_password():
            print("Admin password set successfully")
            return True
        else:
            print("Failed to set admin password")
            return False
    else:
        print("Admin password already configured")
        return True

def validate_server_requirements(manager):
    """Validate that server has required configurations"""
    print("The Gold Box - Validating Server Requirements")
    print("=" * 50)
    
    # Check for valid API keys
    valid_keys_exist = any(key for key in manager.keys_data.values() if key)
    if not valid_keys_exist:
        print("ERROR: No valid API keys found")
        print("Please configure at least one API key using key manager")
        return False
    
    print(f"Found {len([k for k in manager.keys_data.values() if k])} valid API key(s)")
    
    # Check for admin password
    if not manager.get_password_status():
        print("ERROR: No admin password set")
        return False
    
    print("Admin password configured")
    print("All server requirements validated")
    return True

def verify_api_key(request):
    """
    Enhanced API key verification for multiple services
    Returns (is_valid: bool, error_message: str)
    """
    # Get API key from headers
    provided_key = request.headers.get('X-API-Key')
    
    # Check if API key is provided
    if not provided_key:
        logger.warning(f"Missing API key from {request.remote_addr}")
        return False, "API key required"
    
    # Check against all configured keys
    valid_keys = [key for key in [OPENAI_API_KEY, NOVELAI_API_KEY] if key]
    
    if not valid_keys:
        return False, "No API keys configured on server"
    
    # Check if provided key matches any configured key
    if provided_key not in valid_keys:
        logger.warning(f"Invalid API key from {request.remote_addr}")
        return False, "Invalid API key"
    
    # Determine which service this key belongs to
    service_name = "Unknown"
    if provided_key == OPENAI_API_KEY:
        service_name = "OpenAI Compatible"
    elif provided_key == NOVELAI_API_KEY:
        service_name = "NovelAI API"
    
    logger.info(f"Valid {service_name} API key from {request.remote_addr}")
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
        # logger.info("DEBUG: Starting simple_chat_endpoint")
        
        # Get validated data from universal security middleware if available
        if hasattr(request.state, 'validated_body') and request.state.validated_body:
            # Use middleware-validated data for enhanced security
            request_data = request.state.validated_body
            logger.info("Processing simple chat request with middleware-validated data")
            # logger.info(f"DEBUG: Request data keys: {list(request_data.keys())}")
        else:
            # Fallback to original request data (should not happen with proper middleware)
            try:
                request_data = await request.json()
                # logger.info("DEBUG: Using original request data")
            except Exception as e:
                # logger.error(f"DEBUG: JSON parsing failed: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in request body"
                )
            logger.info("Processing simple chat request with original request data")
        
        # logger.info(f"DEBUG: Request data received: {request}")
        # logger.info(f"DEBUG: Extracted context_count: {context_count}")
        # logger.info(f"DEBUG: Extracted settings: {settings}")
        # logger.info(f"DEBUG: Settings keys: {list(settings.keys()) if settings else 'None'}")
        
        # PHASE 1 FIX: Load stored settings FIRST before validation
        try:
            from server import settings_manager
            stored_settings = settings_manager.get_settings()
            if stored_settings:
                # logger.info(f"DEBUG: Loaded {len(stored_settings)} stored settings before validation")
                # Merge request settings with stored settings (request takes priority for client ID)
                merged_settings = {**stored_settings}  # Start with all stored settings
                if settings and isinstance(settings, dict):
                    merged_settings.update(settings)  # Override with request settings (client ID)
                settings = merged_settings  # Use merged settings for all processing
                # logger.info(f"DEBUG: Merged settings total count: {len(settings)}")
            else:
                # logger.warning("DEBUG: No stored settings available for merging")
                pass
        except ImportError as e:
            logger.error(f"Failed to import settings_manager for early merge: {e}")
        
        # PHASE 1 TEST: Verify unified settings object structure (AFTER merge)
        if settings and isinstance(settings, dict):
            required_keys = [
                'maximum message context',
                'chat processing mode', 
                'ai role',
                'general llm provider',
                'general llm model',
                'general llm base url',
                'general llm version',
                'general llm timeout',
                'general llm max retries',
                'general llm custom headers',
                'tactical llm provider',
                'tactical llm base url',
                'tactical llm model',
                'tactical llm version',
                'tactical llm timeout',
                'tactical llm max retries',
                'tactical llm custom headers',
                'backend password'
            ]
            
            missing_keys = [key for key in required_keys if key not in settings]
            extra_keys = [key for key in settings if key not in required_keys]
            
            # logger.info(f"PHASE 1 TEST: Settings structure validation (after merge):")
            # logger.info(f"  Required keys present: {len([k for k in required_keys if k in settings])}/{len(required_keys)}")
            # logger.info(f"  Missing keys: {missing_keys}")
            # logger.info(f"  Extra keys: {extra_keys}")
            
            if len(missing_keys) == 0:
                # logger.info("PHASE 1 TEST: ✅ Settings object structure is correct after merge")
                pass
            else:
                logger.warning(f"PHASE 1 TEST: ⚠️ Settings structure issues detected after merge")
        
        # Initialize universal_settings with defaults to avoid scope issues
        universal_settings = extract_universal_settings({}, "simple_chat")
        # logger.info(f"DEBUG: Initialized universal_settings with defaults: {universal_settings}")
        
        # Step 1: Collect chat messages via REST API (relay server is started by main server)
        context_count = request_data.get('context_count', 15)
        logger.info(f"Collecting {context_count} chat messages via REST API")
        
        # Prepare request data for client ID extraction (PHASE 1 FIX: Always ensure valid dictionary)
        if hasattr(request.state, 'validated_body') and request.state.validated_body:
            request_data_for_api = request.state.validated_body
            # logger.info("DEBUG: Using middleware-validated request data for API calls")
        else:
            # If no middleware validation, use original request data (PHASE 1 FIX: Ensure valid structure)
            request_data_for_api = {
                'context_count': request_data.get('context_count', 15),
                'settings': request_data.get('settings') if request_data.get('settings') is not None else {}
            }
            # logger.info("DEBUG: Using original request data for API calls")
        
        # PHASE 1 FIX: Ensure request_data_for_api is never None
        if request_data_for_api is None:
            request_data_for_api = {'context_count': context_count, 'settings': {}}
            # logger.warning("DEBUG: request_data_for_api was None, using fallback structure")
        
        api_messages = await collect_chat_messages_api(context_count, request_data_for_api)
        
        # Step 2: Convert to compact JSON
        api_chat_processor = APIChatProcessor()
        compact_messages = api_chat_processor.process_api_messages(api_messages)
        
        # Step 3: Use universal settings extraction for consistent behavior
        # First try to use settings from request, then fall back to stored settings
        if settings and isinstance(settings, dict):
            # MERGE FIX: If settings contains client ID, merge with stored settings for complete config
            if 'relay client id' in settings:
                # Client ID provided - merge with stored settings for complete configuration
                try:
                    from server import settings_manager
                    stored_settings = settings_manager.get_settings()
                    if stored_settings:
                        # Merge request settings with stored settings (request takes priority for client ID)
                        merged_settings = {**stored_settings}  # Start with all stored settings
                        merged_settings.update(settings)  # Override with request settings (client ID)
                        request_data_for_settings = {
                            'settings': merged_settings
                        }
                        universal_settings = extract_universal_settings(request_data_for_settings, "simple_chat")
                        # logger.info(f"DEBUG: Merged settings - Stored: {len(stored_settings)}, Request: {len(settings)}, Final: {len(merged_settings)}")
                except ImportError as e:
                    logger.error(f"Failed to import settings_manager for merge: {e}")
                    # Fallback to request settings only
                    request_data_for_settings = {
                        'settings': settings
                    }
                    universal_settings = extract_universal_settings(request_data_for_settings, "simple_chat")
                    # logger.info(f"DEBUG: Using request settings only (no stored settings available): {universal_settings}")
            else:
                # No client ID - use request settings as-is
                request_data_for_settings = {
                    'settings': settings
                }
                universal_settings = extract_universal_settings(request_data_for_settings, "simple_chat")
                # logger.info(f"DEBUG: Using request settings only (no client ID): {universal_settings}")
        else:
            # Use stored settings from settings manager (fallback)
            try:
                from server import settings_manager
                stored_settings = settings_manager.get_settings()
            except ImportError as e:
                logger.error(f"Failed to import settings_manager: {e}")
                stored_settings = {}
            # logger.info(f"DEBUG: Retrieved stored settings: {stored_settings}")
            if stored_settings:
                request_data_for_settings = {
                    'settings': stored_settings
                }
                universal_settings = extract_universal_settings(request_data_for_settings, "simple_chat")
                # logger.info(f"DEBUG: Universal settings extracted from storage: {universal_settings}")
            else:
                # Final fallback to defaults
                # logger.warning("DEBUG: No stored settings found, using defaults")
                universal_settings = extract_universal_settings({}, "simple_chat")
                # logger.info(f"DEBUG: Universal settings extracted from defaults: {universal_settings}")
        
        # Extract provider config from universal settings
        provider_config = get_provider_config(universal_settings, use_tactical=False)
        # logger.info(f"DEBUG: Provider config extracted: {provider_config}")
        
        # Extract messages from request data
        messages = request_data.get('messages', [])
        
        # logger.info(f"DEBUG: frontend_settings type: {type(request_data.get('settings', {}))}")
        # logger.info(f"DEBUG: messages type: {type(messages)}")
        # logger.info(f"DEBUG: messages: {messages}")
        
        # Validate that we have messages (be more lenient for frontend issues)
        if not messages or not isinstance(messages, list):
            # logger.error(f"DEBUG: Messages invalid: {type(messages)}, raising 400")
            raise HTTPException(
                status_code=400,
                detail=f"Messages array is required and must be a list, got {type(messages).__name__}"
            )
        
        # Use provider config values for consistency
        provider_id = provider_config['provider']
        model = provider_config['model']
        base_url = provider_config['base_url']
        api_version = provider_config['api_version']
        timeout = provider_config['timeout']
        max_retries = provider_config['max_retries']
        custom_headers_str = provider_config.get('custom_headers', '{}')
        
        client_host = request.client.host if request.client else "unknown"
        logger.info(f"Processing provider-agnostic request from {client_host}: provider={provider_id}, model={model}")
        logger.info(f"Settings: base_url={base_url}, api_version={api_version}, timeout={timeout}, max_retries={max_retries}")
        
        # logger.info(f"DEBUG: Calling process_simple_chat with unified settings")
        # logger.info(f"  provider_id: {provider_id}")
        # logger.info(f"  model: {model}")
        # logger.info(f"  message_context: {len(messages)} messages")
        # logger.info(f"  base_url: {base_url}")
        # logger.info(f"  api_version: {api_version}")
        # logger.info(f"  timeout: {timeout}")
        # logger.info(f"  max_retries: {max_retries}")
        # logger.info(f"  custom_headers_str: {custom_headers_str}")
        
        result = await process_simple_chat(
            request_data=request_data,  # Pass full request data with unified settings
            provider_id=provider_id,
            model=model,
            prompt=None,  # Will be set from message context
            message_context=messages,
            temperature=0.1,  # Default temperature
            max_tokens=None,  # No token limit by default
            base_url=base_url,  # Pass base URL if provided
            api_version=api_version,  # Pass API version
            timeout=timeout,  # Pass timeout
            max_retries=max_retries,  # Pass max retries
            custom_headers=custom_headers_str  # Pass custom headers as JSON string
        )
        
        # logger.info(f"DEBUG: process_simple_chat returned: {result}")
        
        if result['success']:
            # Log actual content for debugging
            content = result.get('response', '')  # AI service returns 'response' not 'content'
            response_data = {
                'status': 'success',
                'response': content,
                'timestamp': datetime.now().isoformat(),
                'provider_used': provider_id,
                'model_used': model,
                'metadata': result.get('metadata', {})
            }
            logger.info(f"Provider-agnostic response sent to {client_host}: success")
        else:
            response_data = {
                'status': 'error',
                'error': result.get('error', 'Unknown error occurred'),
                'timestamp': datetime.now().isoformat(),
                'provider_used': provider_id,
                'model_used': model
            }
            logger.error(f"Provider-agnostic response failed for {client_host}: {result.get('error')}")
        
        return response_data
        
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
        
        # Get client ID from unified settings with better fallback handling (Phase 2 fix)
        client_id = None
        if request_data:
            # Priority 1: Get from unified settings in request
            settings = request_data.get('settings', {})
            client_id = settings.get('relay client id')
            if client_id:
                # logger.info("DEBUG: Client ID found in unified settings")
                pass
            else:
                # Priority 2: Try to get from stored settings as fallback
                try:
                    from server import settings_manager
                    stored_settings = settings_manager.get_settings()
                    if stored_settings:
                        client_id = stored_settings.get('relay client id')
                        if client_id:
                            # logger.info("DEBUG: Client ID found in stored settings (fallback)")
                            pass
                except ImportError:
                    pass
                
                if not client_id:
                    # Priority 3: Fallback to separate parameter (backward compatibility)
                    client_id = request_data.get('relayClientId')
                    if client_id:
                        # logger.info("DEBUG: Client ID found in separate parameter (backward compatibility)")
                        pass
        else:
            # Try to get from stored settings when no request data
            try:
                from server import settings_manager
                stored_settings = settings_manager.get_settings()
                if stored_settings:
                    client_id = stored_settings.get('relay client id')
                    if client_id:
                        # logger.info("DEBUG: Client ID found in stored settings (no request data)")
                        pass
            except ImportError:
                pass
        
        # If no client ID provided, try to get one from relay server
        if not client_id:
            # logger.info("DEBUG: No client ID provided, attempting to get available clients from relay server")
            try:
                # Try to get list of available clients from relay server (PHASE 2 FIX: Correct endpoint)
                clients_response = requests.get(
                    f"http://localhost:3010/clients",
                    timeout=5
                )
                if clients_response.status_code == 200:
                    clients = clients_response.json()
                    if clients and len(clients) > 0:
                        # Use the first available client
                        client_id = clients[0].get('id')
                        # logger.info(f"DEBUG: Using first available client: {client_id}")
                    else:
                        # logger.warning("DEBUG: No clients available on relay server")
                        pass
                else:
                    # logger.warning(f"DEBUG: Failed to get clients list: {clients_response.status_code}")
                    pass
            except Exception as e:
                # logger.warning(f"DEBUG: Error getting clients list: {e}")
                pass
        
        # If still no client ID, try some common defaults or generate a test one
        if not client_id:
            # logger.warning("DEBUG: Still no client ID, trying fallback approaches")
            # Try some common client IDs that might be registered
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
                        # logger.info(f"DEBUG: Found working fallback client ID: {client_id}")
                        break
                except:
                    continue
            
            # If all fallbacks fail, use a generated ID but expect it to fail
            if not client_id:
                client_id = "generated-test-client"
                # logger.warning(f"DEBUG: Using generated client ID (may fail): {client_id}")
        
        # logger.info(f"DEBUG: Using client ID for relay server request: {client_id}")
        
        # Get chat messages from relay server with proper authentication
        headers = {}
        # In development mode, we can use a local dev key or bypass auth
        # The relay server uses memory store in local dev which bypasses auth
        headers["x-api-key"] = "local-dev"  # This works for local memory store mode
        
        # TIMING FIX: Enhanced delay to allow Foundry module to process changes and store them
        # The createChatMessage hook in Foundry module runs AFTER message creation
        # We need to allow time for:
        # 1. Message creation in Foundry
        # 2. Hook processing in Foundry module  
        # 3. Relay server processing and storage
        await asyncio.sleep(1.0)  # Increased to 1 second delay for complete processing
        
        # Collect both chat messages AND rolls for complete context
        chat_messages = []
        roll_messages = []
        
        # Step1: Get chat messages (always force fresh data)
        chat_response = requests.get(
            f"http://localhost:3010/messages",  # PHASE 3 FIX: Use correct Gold API endpoint
            params={"clientId": client_id, "limit": count, "sort": "timestamp", "order": "desc", "refresh": True},
            headers=headers,
            timeout=5  # Increased timeout to give more time for processing
        )
        
        # logger.info(f"DEBUG: Chat messages response status: {chat_response.status_code}")
        # logger.info(f"DEBUG: Chat messages response text: {chat_response.text}")
        
        if chat_response.status_code == 200:
            try:
                response_data = chat_response.json()
                # logger.info(f"DEBUG: Parsed chat response data: {response_data}")
                
                # Extract messages from response structure
                if isinstance(response_data, dict):
                    if 'messages' in response_data:
                        chat_messages = response_data['messages']
                        # logger.info(f"DEBUG: Extracted messages from 'messages' field: {len(chat_messages) if chat_messages else 0}")
                    else:
                        # logger.warning(f"DEBUG: No 'messages' field found in chat response. Available keys: {list(response_data.keys())}")
                        pass
                elif isinstance(response_data, list):
                    # Direct list response (fallback)
                    chat_messages = response_data
                    # logger.info(f"DEBUG: Chat response is direct list: {len(chat_messages)} messages")
                else:
                    # logger.warning(f"DEBUG: Unexpected chat response format: {type(response_data)}")
                    pass
                
                # logger.info(f"DEBUG: Final chat messages count: {len(chat_messages) if chat_messages else 0}")
            except json.JSONDecodeError as e:
                # logger.error(f"DEBUG: Failed to parse chat JSON: {e}")
                # logger.error(f"DEBUG: Raw chat response: {chat_response.text}")
                pass
        else:
            logger.error(f"Failed to collect chat messages: {chat_response.status_code}")
            # logger.error(f"DEBUG: Raw chat response: {chat_response.text}")
        
        # Step 2: Get roll messages for same time period (with additional delay for processing)
        await asyncio.sleep(0.5)  # Additional delay before roll request
        
        rolls_response = requests.get(
            f"http://localhost:3010/rolls",
            params={"clientId": client_id, "limit": count, "sort": "timestamp", "order": "desc", "refresh": True},
            headers=headers,
            timeout=5  # Increased timeout for consistency
        )
        
        # logger.info(f"DEBUG: Rolls response status: {rolls_response.status_code}")
        # logger.info(f"DEBUG: Rolls response text: {rolls_response.text}")
        
        if rolls_response.status_code == 200:
            try:
                rolls_data = rolls_response.json()
                # logger.info(f"DEBUG: Parsed rolls response data: {rolls_data}")
                
                # Extract rolls from response structure
                if isinstance(rolls_data, dict):
                    # Check for 'data' field first (relay server puts rolls here)
                    if 'data' in rolls_data:
                        roll_messages = rolls_data['data']
                        # logger.info(f"DEBUG: Extracted rolls from 'data' field: {len(roll_messages) if roll_messages else 0}")
                    # Fallback to 'rolls' field for backward compatibility
                    elif 'rolls' in rolls_data:
                        roll_messages = rolls_data['rolls']
                        # logger.info(f"DEBUG: Extracted rolls from 'rolls' field: {len(roll_messages) if roll_messages else 0}")
                    else:
                        # logger.warning(f"DEBUG: No 'data' or 'rolls' field found in rolls response. Available keys: {list(rolls_data.keys())}")
                        pass
                elif isinstance(rolls_data, list):
                    # Direct list response (fallback)
                    roll_messages = rolls_data
                    # logger.info(f"DEBUG: Rolls response is direct list: {len(roll_messages)} rolls")
                else:
                    # logger.warning(f"DEBUG: Unexpected rolls response format: {type(rolls_data)}")
                    pass
                
                # logger.info(f"DEBUG: Final roll messages count: {len(roll_messages) if roll_messages else 0}")
            except json.JSONDecodeError as e:
                # logger.error(f"DEBUG: Failed to parse rolls JSON: {e}")
                # logger.error(f"DEBUG: Raw rolls response: {rolls_response.text}")
                pass
        else:
            logger.error(f"Failed to collect rolls: {rolls_response.status_code}")
            # logger.error(f"DEBUG: Raw rolls response: {rolls_response.text}")
        
        # Step 3: Merge and sort all messages chronologically
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
        
        # logger.info(f"DEBUG: Merged {len(chat_messages)} chat messages and {len(roll_messages)} roll messages")
        # logger.info(f"DEBUG: Final merged count: {len(merged_messages)}")
        # logger.info(f"DEBUG: Message sources: {[msg.get('_source') for msg in merged_messages[:5]]}")
        
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
            
            # Debug logging to track what settings are received
            # logger.info(f"DEBUG: Admin endpoint received settings data:")
            # logger.info(f"  - Type: {type(frontend_settings_data)}")
            # logger.info(f"  - Keys count: {len(frontend_settings_data) if isinstance(frontend_settings_data, dict) else 'N/A (not dict)'}")
            # logger.info(f"  - Keys: {list(frontend_settings_data.keys()) if isinstance(frontend_settings_data, dict) else 'N/A (not dict)'}")
            # logger.info(f"  - Non-empty values: {len([v for v in frontend_settings_data.values() if v and str(v).strip()]) if isinstance(frontend_settings_data, dict) else 'N/A (not dict)'}")
            
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
    import uvicorn
    
    # Key Management - Check for keys and prompt for setup if needed
    print("=" * 60)
    print("The Gold Box Backend - Key Management")
    print("=" * 60)
    
    manager = MultiKeyManager()
    
    # Check for keychange environment variable
    keychange = os.environ.get('GOLD_BOX_KEYCHANGE', '').lower() in ['true', '1', 'yes']
    
    # Check if keys file exists and load it
    if manager.key_file.exists():
        print("Loading API keys and admin password...")
        if not manager.load_keys():
            # load_keys() will prompt for password if needed
            print("[ERROR] Failed to load keys - invalid password or corrupted file")
            print("If you forgot the password, you may need to delete the keys file and start over")
            sys.exit(1)
    else:
        print("No keys file found. Running initial setup...")
    
    # Force key manager if keychange is set
    if keychange:
        print("\n" + "=" * 50)
        print("KEYCHANGE FLAG DETECTED")
        print("=" * 50)
        print("Forcing key manager to run due to GOLD_BOX_KEYCHANGE=true")
        print("This allows you to modify API keys and settings.")
        if not manager.interactive_setup():
            print("[ERROR] Key setup cancelled or failed")
            sys.exit(1)
        
        # Save configuration (password is already set in manager)
        if not manager.save_keys(manager.keys_data):
            print("[ERROR] Failed to save updated keys")
            sys.exit(1)
    
    # Step 1: Check if valid API keys exist (only if NOT keychange)
    if not keychange:
        valid_keys_exist = any(key for key in manager.keys_data.values() if key)
        if not valid_keys_exist:
            print("\n" + "=" * 50)
            print("NO VALID API KEYS FOUND")
            print("=" * 50)
            print("No valid API keys are configured.")
            print("Running key manager to add API keys...")
            if not manager.interactive_setup():
                print("[ERROR] Key setup failed")
                sys.exit(1)
            
            # Save configuration (password is already set in manager)
            if not manager.save_keys(manager.keys_data):
                print("[ERROR] Failed to save updated keys")
                sys.exit(1)
        
        # Step 2: Check if admin password is set (only if NOT keychange)
        if not manager.get_password_status():
            print("\n" + "=" * 50)
            print("ADMIN PASSWORD REQUIRED")
            print("=" * 50)
            print("No admin password is configured.")
            print("Setting up admin password now...")
            if not manage_admin_password(manager):
                print("[ERROR] Admin password setup failed")
                sys.exit(1)
            
            # Save configuration with admin password using same password
            if not manager.save_keys(manager.keys_data):
                print("[ERROR] Failed to save configuration with admin password")
                sys.exit(1)
    
    # Step3: Set environment variables and start server
    print("Setting up environment variables...")
    if not manager.set_environment_variables():
        print("[ERROR] Failed to set environment variables")
        sys.exit(1)
    
    # Reload global variables
    OPENAI_API_KEY = os.environ.get('GOLD_BOX_OPENAI_COMPATIBLE_API_KEY', '')
    NOVELAI_API_KEY = os.environ.get('GOLD_BOX_NOVELAI_API_API_KEY', '')
    
    print("All requirements validated successfully")
    
    # Check if running in development or production
    debug_mode = FLASK_DEBUG
    is_development = FLASK_ENV == 'development'
    
    # Find an available port
    start_port = GOLD_BOX_PORT
    available_port = find_available_port(start_port)
    
    if not available_port:
        print(f"[ERROR] No available ports found starting from {start_port}")
        print("[ERROR] Please check if another application is using these ports")
        sys.exit(1)
    
    # Clear terminal for clean startup display
    import os
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("=" * 60)
    print("The Gold Box FastAPI Backend Server")
    print("=" * 60)
    print(f"Environment: {FLASK_ENV}")
    
    # List all loaded API keys from provider manager
    loaded_keys = []
    if hasattr(manager, 'keys_data') and manager.keys_data:
        for provider_id, key_value in manager.keys_data.items():
            if key_value:  # Check if key has a value (any length)
                # Get provider name from provider manager for better display
                provider_info = manager.provider_manager.get_provider(provider_id)
                if provider_info:
                    provider_name = provider_info.get('name', provider_id.upper())
                else:
                    provider_name = provider_id.upper().replace('_API_KEY', '')
                loaded_keys.append(provider_name)
    
    print(f"Loaded API Keys: {', '.join(loaded_keys) if loaded_keys else 'None'}")
    print(f"Rate Limiting: {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds")
    
    # CORS Configuration Summary
    print(f"CORS Origins: {len(CORS_ORIGINS)} configured")
    if is_development:
        print("  Development CORS origins (localhost only):")
        for origin in CORS_ORIGINS:
            print(f"    - {origin}")
    else:
        print("  Production CORS origins (explicitly configured)")
        for origin in CORS_ORIGINS:
            print(f"    - {origin}")
    
    # Server startup information
    print(f"FastAPI Server starting on http://localhost:{available_port}")
    print("=" * 60)
    print("🔒 Universal Security Middleware is now active and protecting all endpoints")
    print("=" * 60)
    
    # Start relay server
    print("Starting relay server...")
    import asyncio
    relay_started = asyncio.run(start_relay_server())
    if not relay_started:
        print("⚠️  Warning: Failed to start relay server. API chat functionality may not work.")
    
    # Start FastAPI server with uvicorn
    uvicorn.run(
        app,
        host='localhost',
        port=available_port,
        log_level="info" if not debug_mode else "debug",
        access_log=True
    )
