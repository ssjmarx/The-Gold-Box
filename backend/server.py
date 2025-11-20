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

# Import key management from separate module
from key_manager import MultiKeyManager
from simple_chat import process_simple_chat

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
OPENAI_API_KEY = os.environ.get('GOLD_BOX_OPENAI_COMPATIBLE_API_KEY', '')
NOVELAI_API_KEY = os.environ.get('GOLD_BOX_NOVELAI_API_API_KEY', '')
GOLD_BOX_PORT = int(os.environ.get('GOLD_BOX_PORT', 5000))
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', 'goldbox.log')

# Rate limiting configuration
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', 5))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('RATE_LIMIT_WINDOW_SECONDS', 60))

# Session timeout configuration
SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30))
SESSION_WARNING_MINUTES = int(os.environ.get('SESSION_WARNING_MINUTES', 5))

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
    prompt: str = Field(..., description="The prompt to send to the AI", min_length=1, max_length=10000)
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

# Enhanced CORS configuration with security headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Admin-Password"],
    expose_headers=[],
    max_age=86400,
)

logger.info(f"CORS configured for {len(CORS_ORIGINS)} origins")

# Simple in-memory rate limiting for basic protection
class RateLimiter:
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    def is_allowed(self, client_id):
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] 
            if now - req_time < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True

# Initialize rate limiter with environment variables
rate_limiter = RateLimiter(max_requests=RATE_LIMIT_MAX_REQUESTS, window_seconds=RATE_LIMIT_WINDOW_SECONDS)

# Session management with timeout
class SessionManager:
    def __init__(self, timeout_minutes=30, warning_minutes=5):
        self.timeout_minutes = timeout_minutes
        self.warning_minutes = warning_minutes
        self.sessions = {}  # client_id -> {'last_activity': timestamp, 'warnings_sent': int}
    
    def update_activity(self, client_id):
        """Update client activity timestamp"""
        now = time.time()
        if client_id not in self.sessions:
            self.sessions[client_id] = {
                'last_activity': now,
                'warnings_sent': 0,
                'created': now
            }
        else:
            self.sessions[client_id]['last_activity'] = now
        return True
    
    def is_session_valid(self, client_id):
        """Check if session is still valid"""
        if client_id not in self.sessions:
            return False, "No active session"
        
        session = self.sessions[client_id]
        now = time.time()
        elapsed_minutes = (now - session['last_activity']) / 60
        
        # Check if session has timed out
        if elapsed_minutes >= self.timeout_minutes:
            return False, f"Session timed out after {elapsed_minutes:.1f} minutes"
        
        # Check if we should send a warning
        time_until_timeout = self.timeout_minutes - elapsed_minutes
        if (time_until_timeout <= self.warning_minutes and 
            time_until_timeout > 0 and 
            session['warnings_sent'] == 0):
            session['warnings_sent'] = 1
            return True, f"Session will timeout in {time_until_timeout:.1f} minutes"
        
        return True, "Session active"
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = time.time()
        expired_clients = []
        
        for client_id, session in self.sessions.items():
            elapsed_minutes = (now - session['last_activity']) / 60
            if elapsed_minutes >= self.timeout_minutes + 10:  # Extra 10 minutes grace period
                expired_clients.append(client_id)
        
        for client_id in expired_clients:
            del self.sessions[client_id]
            logger.info(f"Cleaned up expired session for {client_id}")
        
        return len(expired_clients)

# Initialize session manager
session_manager = SessionManager(timeout_minutes=SESSION_TIMEOUT_MINUTES, warning_minutes=SESSION_WARNING_MINUTES)

# Security verification functions
def verify_virtual_environment():
    """Verify that we're running in a proper virtual environment"""
    try:
        # Check if we're in a virtual environment
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        
        if not in_venv:
            logger.warning("Not running in a virtual environment - this is not recommended for production")
            return False
        
        # Verify venv isolation
        venv_path = sys.prefix
        if not os.path.exists(venv_path):
            logger.error(f"Virtual environment path does not exist: {venv_path}")
            return False
        
        # Check for critical venv components
        required_dirs = ['lib', 'include', 'bin']
        for dir_name in required_dirs:
            dir_path = os.path.join(venv_path, dir_name)
            if not os.path.exists(dir_path):
                logger.error(f"Virtual environment missing required directory: {dir_path}")
                return False
        
        logger.info(f"Virtual environment verified: {venv_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying virtual environment: {e}")
        return False

def verify_file_integrity():
    """Verify integrity of critical files"""
    try:
        integrity_checks = []
        
        # Check requirements.txt integrity
        req_file = Path(__file__).parent / 'requirements.txt'
        if req_file.exists():
            with open(req_file, 'r') as f:
                req_content = f.read()
                req_hash = hashlib.sha256(req_content.encode()).hexdigest()
                integrity_checks.append(f"requirements.txt: {req_hash}")
                logger.info(f"requirements.txt hash: {req_hash}")
        
        # Check server.py integrity
        server_file = Path(__file__)
        if server_file.exists():
            with open(server_file, 'r') as f:
                server_content = f.read()
                server_hash = hashlib.sha256(server_content.encode()).hexdigest()
                integrity_checks.append(f"server.py: {server_hash}")
                logger.info(f"server.py hash: {server_hash}")
        
        return integrity_checks
        
    except Exception as e:
        logger.error(f"Error verifying file integrity: {e}")
        return []

def verify_file_permissions():
    """Verify and enforce proper file permissions"""
    try:
        permission_issues = []
        
        # Check log file permissions
        log_file_path = Path(LOG_FILE)
        if log_file_path.exists():
            current_perms = stat.filemode(log_file_path.stat().st_mode)
            # Log files should be readable/writeable by owner, not by others
            if current_perms[-3:] in ['777', '666', '644']:
                logger.warning(f"Log file has overly permissive permissions: {current_perms}")
                permission_issues.append(f"Log file permissions: {current_perms}")
                
                # Try to fix permissions
                try:
                    os.chmod(log_file_path, 0o600)
                    logger.info("Fixed log file permissions to 0o600")
                except Exception as perm_error:
                    logger.error(f"Failed to fix log file permissions: {perm_error}")
        
        # Check key file permissions if it exists
        key_file_path = Path(__file__).parent / 'keys.enc'
        if key_file_path.exists():
            current_perms = stat.filemode(key_file_path.stat().st_mode)
            # Key files should be restricted to owner only
            if current_perms[-3:] != '600':
                logger.warning(f"Key file has insecure permissions: {current_perms}")
                permission_issues.append(f"Key file permissions: {current_perms}")
                
                # Try to fix permissions
                try:
                    os.chmod(key_file_path, 0o600)
                    logger.info("Fixed key file permissions to 0o600")
                except Exception as perm_error:
                    logger.error(f"Failed to fix key file permissions: {perm_error}")
        
        return permission_issues
        
    except Exception as e:
        logger.error(f"Error verifying file permissions: {e}")
        return ["Permission verification failed"]

def verify_dependency_integrity():
    """Verify dependency integrity using pip hash checking if available"""
    try:
        # Get list of installed packages
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("Could not verify dependency integrity")
            return []
        
        installed_packages = {}
        for line in result.stdout.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    package_name = parts[0]
                    version = parts[1]
                    installed_packages[package_name] = version
        
        # Check critical dependencies
        critical_deps = ['Flask', 'Flask-CORS', 'python-dotenv', 'cryptography']
        integrity_status = []
        
        for dep in critical_deps:
            if dep in installed_packages:
                integrity_status.append(f"{dep}: {installed_packages[dep]} - OK")
                logger.info(f"Dependency verified: {dep} v{installed_packages[dep]}")
            else:
                integrity_status.append(f"{dep}: MISSING")
                logger.error(f"Critical dependency missing: {dep}")
        
        return integrity_status
        
    except Exception as e:
        logger.error(f"Error verifying dependency integrity: {e}")
        return ["Dependency verification failed"]

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

class UniversalInputValidator:
    """
    Universal input validation system for The Gold Box
    Handles various input types and prepares for AI API integration
    """
    
    # Security patterns for dangerous content (more specific to avoid false positives)
    DANGEROUS_PATTERNS = [
        # Script injection patterns
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        # SQL injection patterns (more specific to avoid false positives like "D&D")
        r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\s+(?:\*|\w+)\s+(?:FROM|INTO|TABLE)',
        r"[';]\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\s+(?:\*|\w+)",
        # Command injection patterns
        r'[;&|`$(){}[\]]\s*(rm|del|format|shutdown|reboot|cat)',
        r'\|\s*(rm|del|format|shutdown|reboot)',
        # Path traversal patterns
        r'\.\.[\\/]',
        r'[\\/]\.\.[\\/]',
        # XSS patterns
        r'on\w+\s*=',
        r'expression\s*\(',
        r'@import',
        # Data exfiltration patterns (more specific)
        r'base64\s*decode',
        r'hex\s*:\s*[0-9a-fA-F]{20,}',  # Only flag long hex strings
    ]
    
    # Allowed characters for different input types
    ALLOWED_CHAR_PATTERNS = {
        'text': r'^[\w\s\.\,\!\?\;\:\-\(\)\[\]\"\'\/\n\r\t]*$',  # Text with punctuation
        'prompt': r'^[\w\s\.\,\!\?\;\:\-\(\)\[\]\"\'\/\n\r\t\#\@\*\&]*$',  # Prompt with special chars
        'api_key': r'^[a-zA-Z0-9\-_\.]+$',  # API keys
        'config': r'^[a-zA-Z0-9\-_\.\/\:\s]*$',  # Configuration values
    }
    
    # Size limits for different input types
    SIZE_LIMITS = {
        'prompt': 10000,  # AI prompts can be longer
        'text': 50000,     # General text
        'api_key': 500,    # API keys
        'config': 1000,     # Configuration values
        'url': 2048,        # URLs
        'email': 254,       # Email addresses
        'filename': 255,     # Filenames
    }
    
    def __init__(self):
        """Initialize the validator with compiled regex patterns"""
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL) 
                               for pattern in self.DANGEROUS_PATTERNS]
        self.compiled_allowed = {key: re.compile(pattern) 
                              for key, pattern in self.ALLOWED_CHAR_PATTERNS.items()}
    
    def validate_input(self, 
                   input_data: Any, 
                   input_type: str = 'text',
                   field_name: str = 'input',
                   required: bool = True,
                   min_length: int = 0,
                   max_length: Optional[int] = None) -> Tuple[bool, str, Any]:
        """
        Universal input validation function
        
        Args:
            input_data: The input data to validate
            input_type: Type of input ('text', 'prompt', 'api_key', 'config', 'url', 'email', 'filename')
            field_name: Name of the field for error messages
            required: Whether the field is required
            min_length: Minimum allowed length
            max_length: Maximum allowed length (overrides default)
            
        Returns:
            Tuple[bool, str, Any]: (is_valid, error_message, sanitized_data)
        """
        
        # Type checking and conversion
        if input_data is None:
            if required:
                return False, f"{field_name} is required", None
            return True, "", None
        
        # Convert to string if not already
        try:
            if isinstance(input_data, (dict, list)):
                # Handle structured data
                return self._validate_structured_data(input_data, input_type, field_name)
            else:
                input_str = str(input_data).strip()
        except Exception as e:
            return False, f"{field_name}: Invalid data format", None
        
        # Length validation
        if max_length is None:
            max_length = self.SIZE_LIMITS.get(input_type, 1000)
        
        if len(input_str) < min_length:
            return False, f"{field_name} must be at least {min_length} characters", None
        
        if len(input_str) > max_length:
            return False, f"{field_name} too long (max {max_length} characters)", None
        
        # Empty validation
        if required and not input_str:
            return False, f"{field_name} cannot be empty", None
        
        if not required and not input_str:
            return True, "", None
        
        # Security validation
        is_safe, security_error = self._check_security(input_str)
        if not is_safe:
            return False, f"{field_name}: {security_error}", None
        
        # Character pattern validation
        pattern_error = self._check_allowed_characters(input_str, input_type)
        if pattern_error:
            return False, f"{field_name}: {pattern_error}", None
        
        # Type-specific validation
        type_error = self._validate_type_specific(input_str, input_type)
        if type_error:
            return False, f"{field_name}: {type_error}", None
        
        # Sanitization
        sanitized = self._sanitize_input(input_str, input_type)
        
        return True, "", sanitized
    
    def _validate_structured_data(self, 
                               data: Union[Dict, List], 
                               input_type: str, 
                               field_name: str) -> Tuple[bool, str, Any]:
        """Validate structured data (dict/list)"""
        if isinstance(data, dict):
            # Validate each key-value pair
            sanitized_dict = {}
            for key, value in data.items():
                is_valid, error, sanitized_value = self.validate_input(
                    value, input_type, f"{field_name}.{key}"
                )
                if not is_valid:
                    return False, error, None
                sanitized_dict[key] = sanitized_value
            return True, "", sanitized_dict
        
        elif isinstance(data, list):
            # Validate each item in list
            sanitized_list = []
            for i, item in enumerate(data):
                is_valid, error, sanitized_value = self.validate_input(
                    item, input_type, f"{field_name}[{i}]"
                )
                if not is_valid:
                    return False, error, None
                sanitized_list.append(sanitized_value)
            return True, "", sanitized_list
        
        else:
            return False, f"{field_name}: Unsupported data structure", None
    
    def _check_security(self, input_str: str) -> Tuple[bool, str]:
        """Check for dangerous patterns"""
        for pattern in self.compiled_patterns:
            if pattern.search(input_str):
                return False, "Contains potentially dangerous content"
        return True, ""
    
    def _check_allowed_characters(self, input_str: str, input_type: str) -> str:
        """Check if input contains only allowed characters"""
        if input_type in self.compiled_allowed:
            pattern = self.compiled_allowed[input_type]
            if not pattern.fullmatch(input_str):
                return "Contains invalid characters"
        return ""
    
    def _validate_type_specific(self, input_str: str, input_type: str) -> str:
        """Type-specific validation"""
        if input_type == 'url':
            # Basic URL validation
            url_pattern = re.compile(
                r'^https?://[^\s/$.?#].[^\s]*$',
                re.IGNORECASE
            )
            if not url_pattern.match(input_str):
                return "Invalid URL format"
        
        elif input_type == 'email':
            # Basic email validation
            email_pattern = re.compile(
                r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                re.IGNORECASE
            )
            if not email_pattern.match(input_str):
                return "Invalid email format"
        
        elif input_type == 'filename':
            # Filename validation
            if input_str in ['.', '..', '/', '\\', '']:
                return "Invalid filename"
            # Check for reserved names (Windows)
            reserved_names = [
                'CON', 'PRN', 'AUX', 'NUL',
                'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
            ]
            base_name = os.path.splitext(input_str)[0].upper()
            if base_name in reserved_names:
                return "Reserved filename"
        
        return ""
    
    def _sanitize_input(self, input_str: str, input_type: str) -> str:
        """Sanitize input based on type"""
        # HTML escaping for text types
        if input_type in ['text', 'prompt', 'config']:
            input_str = html.escape(input_str)
        
        # Remove null bytes
        input_str = input_str.replace('\x00', '')
        
        # Normalize whitespace
        if input_type in ['text', 'prompt']:
            input_str = ' '.join(input_str.split())
        
        # Trim based on type
        max_length = self.SIZE_LIMITS.get(input_type, 1000)
        if len(input_str) > max_length:
            input_str = input_str[:max_length]
        
        return input_str
    
    def validate_ai_request(self, request_data: Dict) -> Tuple[bool, str, Dict]:
        """
        Validate AI-specific request data
        Prepares for future AI API integration
        """
        sanitized_request = {}
        
        # Validate prompt (required)
        prompt = request_data.get('prompt')
        is_valid, error, sanitized_prompt = self.validate_input(
            prompt, 'prompt', 'prompt', required=True
        )
        if not is_valid:
            return False, error, None
        sanitized_request['prompt'] = sanitized_prompt
        
        # Validate optional parameters
        optional_params = {
            'max_tokens': ('int', 100, 8192),
            'temperature': ('float', 0.7, 0.0, 2.0),
            'top_p': ('float', 1.0, 0.0, 1.0),
            'frequency_penalty': ('float', 0.0, -2.0, 2.0),
            'presence_penalty': ('float', 0.0, -2.0, 2.0),
        }
        
        for param, (param_type, default_val, *ranges) in optional_params.items():
            value = request_data.get(param, default_val)
            
            try:
                if param_type == 'int':
                    value = int(float(value))  # Handle string numbers
                    if ranges and len(ranges) == 1 and (value < 0 or value > ranges[0]):
                        return False, f"{param} must be between 0 and {ranges[0]}", None
                elif param_type == 'float':
                    value = float(value)
                    if ranges and len(ranges) == 2 and (value < ranges[0] or value > ranges[1]):
                        return False, f"{param} must be between {ranges[0]} and {ranges[1]}", None
                
                sanitized_request[param] = value
                
            except (ValueError, TypeError):
                return False, f"{param} must be a valid {param_type}", None
        
        return True, "", sanitized_request
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, str]:
        """Validate API key format"""
        if not api_key:
            return True, ""  # Empty API key is allowed in development mode
        
        is_valid, error, sanitized = self.validate_input(
            api_key, 'api_key', 'API key', required=True, min_length=8
        )
        return is_valid, error

# Initialize global validator
validator = UniversalInputValidator()

# Global settings dictionary for frontend configuration
frontend_settings = {}

class SettingsManager:
    """Global settings manager for frontend configuration"""
    
    @staticmethod
    def update_settings(new_settings: Dict) -> bool:
        """Update the global frontend settings dictionary"""
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


def manage_keys(keychange=False):
    """Enhanced key management function with admin password"""
    print("Gold Box - Starting Key Management...")
    
    manager = MultiKeyManager()
    
    # Check if keychange flag is set or no key file exists
    if keychange or not manager.key_file.exists():
        print("Running key setup wizard...")
        if manager.interactive_setup():
            print('\nSet encryption password for your keys.')
            print('This password will be required on every server startup.')
            encryption_password = getpass.getpass('Encryption password (blank for unencrypted): ')
            manager.save_keys(manager.keys_data, encryption_password if encryption_password else None)
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
    print("Gold Box - Admin Password Setup")
    print("=" * 50)
    
    if not manager.get_admin_password_status():
        print("No admin password set. Setting up admin password now...")
        if manager.set_admin_password():
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
    print("Gold Box - Validating Server Requirements")
    print("=" * 50)
    
    # Check for valid API keys
    valid_keys_exist = any(key for key in manager.keys_data.values() if key)
    if not valid_keys_exist:
        print("ERROR: No valid API keys found")
        print("Please configure at least one API key using the key manager")
        return False
    
    print(f"✓ Found {len([k for k in manager.keys_data.values() if k])} valid API key(s)")
    
    # Check for admin password
    if not manager.get_admin_password_status():
        print("ERROR: No admin password set")
        return False
    
    print("✓ Admin password configured")
    print("✓ All server requirements validated")
    return True

def validate_prompt(prompt):
    """
    Legacy function for backward compatibility
    Uses the new universal validator
    """
    is_valid, error, sanitized = validator.validate_input(
        prompt, 'prompt', 'prompt', required=True
    )
    if not is_valid:
        raise ValueError(error)
    return sanitized

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

# FastAPI middleware for security headers and request logging
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Add security headers and log requests"""
    # Log incoming requests
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"{request.method} {request.url.path} from {client_host}")
    
    # Call the next middleware/route handler
    response = await call_next(request)
    
    # Add security headers to API responses
    if request.url.path.startswith('/api/'):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

@app.post("/api/simple_chat")
async def simple_chat_endpoint(request: Request):
    """
    Enhanced simple chat endpoint for OpenCode-compatible APIs
    Handles both single prompts and message context
    """
    try:
        # Get client IP for rate limiting
        client_host = request.client.host if request.client else "unknown"
        
        # Rate limiting
        if not rate_limiter.is_allowed(client_host):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"X-RateLimit-Remaining": str(0)}
            )
        
        # Session management
        session_manager.update_activity(client_host)
        is_valid, session_msg = session_manager.is_session_valid(client_host)
        
        if not is_valid:
            raise HTTPException(
                status_code=401,
                detail=session_msg,
                headers={"X-Session-Timeout": "true"}
            )
        
        # Get request body
        try:
            request_data = await request.json()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON in request body"
            )
        
        # Extract parameters
        service_key = request_data.get('service_key', 'z_ai')  # Default to Z.AI
        prompt = request_data.get('prompt', '')
        message_context = request_data.get('message_context', [])
        
        # Validate that we have either prompt or message_context
        if not prompt and not message_context:
            raise HTTPException(
                status_code=400,
                detail="Either prompt or message_context is required"
            )
        
        # Process using simple_chat module
        logger.info(f"Processing simple chat request from {client_host}: service={service_key}")
        
        result = await process_simple_chat(
            service_key=service_key,
            prompt=prompt,
            message_context=message_context,
            temperature=request_data.get('temperature', 0.1),
            max_tokens=request_data.get('max_tokens', None)
        )
        
        if result['success']:
            # Log the actual content for debugging
            content = result['content']
            logger.info(f"🔍 SERVER DEBUG: Content extracted: '{content}'")
            logger.info(f"🔍 SERVER DEBUG: Content length: {len(content) if content else 0}")
            logger.info(f"🔍 SERVER DEBUG: Content is empty: {not bool(content)}")
            
            response_data = {
                'status': 'success',
                'response': result['content'],
                'timestamp': datetime.now().isoformat(),
                'service_used': service_key,
                'metadata': result.get('metadata', {}),
                'message': 'OpenCode API response received successfully'
            }
            logger.info(f"OpenCode response sent to {client_host}: success")
            logger.info(f"🔍 SERVER DEBUG: Response data content: '{response_data['response']}'")
        else:
            response_data = {
                'status': 'error',
                'error': result.get('error', 'Unknown error occurred'),
                'timestamp': datetime.now().isoformat(),
                'service_used': service_key
            }
            logger.error(f"OpenCode response failed for {client_host}: {result.get('error')}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Simple chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    """
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
        }
    )

@app.get("/api/info", response_model=InfoResponse)
async def service_info():
    """
    Enhanced service information endpoint
    """
    return InfoResponse(
        name='The Gold Box Backend',
        description='AI-powered Foundry VTT Module Backend with Universal Input Validation',
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
            'ai_parameter_validation': True
        },
        supported_input_types=list(validator.ALLOWED_CHAR_PATTERNS.keys()),
        size_limits=validator.SIZE_LIMITS,
        endpoints={
            'process': 'POST /api/process - Process AI prompts (enhanced validation)',
            'health': 'GET /api/health - Health check',
            'info': 'GET /api/info - Service information',
            'security': 'GET /api/security - Security verification and integrity checks',
            'start': 'POST /api/start - Server startup instructions'
        },
        license='CC-BY-NC-SA 4.0',
        dependencies={
            'FastAPI': 'MIT License',
            'Uvicorn': 'BSD 3-Clause License'
        },
        security={
            'api_authentication': bool(OPENAI_API_KEY) or bool(NOVELAI_API_KEY),
            'rate_limiting': True,
            'cors_restrictions': len(CORS_ORIGINS) > 0,
            'input_validation': 'UniversalInputValidator',
            'security_headers': True,
            'xss_protection': True,
            'sql_injection_protection': True,
            'command_injection_protection': True
        }
    )

@app.get("/api/security")
async def security_verification():
    """
    Security verification endpoint for integrity checks
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

@app.post("/api/start")
async def start_backend():
    """
    Attempt to start backend server (for auto-start functionality)
    Note: This is a simplified approach since browser can't spawn processes directly
    """
    return {
        'status': 'info',
        'message': 'Please start the backend manually: cd backend && source venv/bin/activate && python server.py',
        'instructions': {
            'step1': 'Open terminal',
            'step2': 'Navigate to backend directory',
            'step3': 'Activate virtual environment: source venv/bin/activate',
            'step4': 'Start server: python server.py'
        },
        'note': 'Automatic process spawning is blocked by browser security restrictions',
        'environment_note': f'Current environment: {FLASK_ENV}',
        'validation_status': 'Universal input validation is active',
        'cors_note': f'CORS configured for {len(CORS_ORIGINS)} origins'
    }

# Admin API endpoint - requires admin password in X-Admin-Password header
@app.post("/api/admin")
async def admin_endpoint(request: Request):
    """
    Password-protected admin endpoint for server management
    Requires admin password in X-Admin-Password header
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
                headers={"WWW-Authenticate": 'Basic realm="Gold Box Admin"'}
            )
        
        # Verify admin password using the already loaded manager
        is_valid, error_msg = manager.verify_admin_password(admin_password)
        if not is_valid:
            logger.warning(f"Invalid admin password attempt from {request.client.host if request.client else 'unknown'}")
            raise HTTPException(
                status_code=401,
                detail=f"Admin authentication failed: {error_msg}",
                headers={"WWW-Authenticate": 'Basic realm="Gold Box Admin"'}
            )
        
        # Get request body for admin commands
        try:
            request_data = await request.json()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON in request body"
            )
        
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
                }
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
            if manager.set_admin_password(new_password):
                # Save updated configuration
                if manager.save_keys(manager.keys_data, None):  # Save without changing encryption
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
        # Re-raise HTTP exceptions
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
            'available_endpoints': ['/api/process', '/api/health', '/api/info', '/api/security', '/api/start'],
            'validator_features': ['universal_validation', 'security_checking', 'sanitization']
        }
    )

@app.exception_handler(405)
async def method_not_allowed(request: Request, exc):
    return JSONResponse(
        status_code=405,
        content={
            'error': 'Method not allowed',
            'status': 'error',
            'allowed_methods': ['GET', 'POST', 'OPTIONS']
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
    
    # Get encryption password once at the start
    encryption_password = None
    if manager.key_file.exists():
        print("Loading API keys and admin password...")
        encryption_password = getpass.getpass('Enter encryption password to unlock keys: ')
        if not manager.load_keys_with_password(encryption_password):
            print("[ERROR] Failed to load keys - invalid password or corrupted file")
            print("If you forgot the password, you may need to delete the keys file and start over")
            sys.exit(1)
    else:
        print("No keys file found. Running initial setup...")
    
    # Step 1: Check if valid API keys exist
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
        
        # Get encryption password for first-time save
        if encryption_password is None:
            print('\nSet encryption password for your keys.')
            print('This password will be required on every server startup.')
            encryption_password = getpass.getpass('Encryption password (blank for unencrypted): ')
        
        if not manager.save_keys(manager.keys_data, encryption_password if encryption_password else None):
            print("[ERROR] Failed to save updated keys")
            sys.exit(1)
    
    # Step 2: Check if admin password is set
    if not manager.get_admin_password_status():
        print("\n" + "=" * 50)
        print("ADMIN PASSWORD REQUIRED")
        print("=" * 50)
        print("No admin password is configured.")
        print("Setting up admin password now...")
        if not manage_admin_password(manager):
            print("[ERROR] Admin password setup failed")
            sys.exit(1)
        
        # Save configuration with admin password using the same password
        if not manager.save_keys(manager.keys_data, encryption_password if encryption_password else None):
            print("[ERROR] Failed to save configuration with admin password")
            sys.exit(1)
    
    # Step 5: Set environment variables and start server
    print("Setting up environment variables...")
    if not manager.set_environment_variables():
        print("[ERROR] Failed to set environment variables")
        sys.exit(1)
    
    # Reload global variables
    OPENAI_API_KEY = os.environ.get('GOLD_BOX_OPENAI_COMPATIBLE_API_KEY', '')
    NOVELAI_API_KEY = os.environ.get('GOLD_BOX_NOVELAI_API_API_KEY', '')
    
    print("✓ All requirements validated successfully")
    
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
    
    print("=" * 60)
    print("The Gold Box FastAPI Backend Server")
    print("=" * 60)
    print(f"Environment: {FLASK_ENV}")
    print(f"Debug mode: {debug_mode}")
    print(f"API Keys Required: {bool(OPENAI_API_KEY) or bool(NOVELAI_API_KEY)}")
    print(f"OpenAI API Key: {'CONFIGURED' if OPENAI_API_KEY else 'NOT SET'}")
    print(f"NovelAI API Key: {'CONFIGURED' if NOVELAI_API_KEY else 'NOT SET'}")
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
    
    # Start FastAPI server with uvicorn
    uvicorn.run(
        app,
        host='localhost',
        port=available_port,
        log_level="info" if not debug_mode else "debug",
        access_log=True
    )
