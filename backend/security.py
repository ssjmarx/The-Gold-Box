#!/usr/bin/env python3
"""
The Gold Box - Security Module
Centralized security validation and input sanitization

License: CC-BY-NC-SA 4.0
"""

import re
import html
import stat
import subprocess
import sys
import os
import time
import hashlib
import secrets
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta, UTC
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiting for basic protection"""
    
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

class SessionManager:
    """Session management with timeout"""
    
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
        'prompt': r'^[\s\S]*$',  # Prompts allow ANY characters (including newlines, Unicode, etc.)
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
        """Initialize validator with compiled regex patterns"""
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
        
        # FIX: Allow empty strings for non-required fields (like custom headers)
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
                # FIX: ALL settings fields should be optional
                is_optional_field = key.startswith('general llm') or key.startswith('tactical llm')
                field_required = not is_optional_field
                
                is_valid, error, sanitized_value = self.validate_input(
                    value, input_type, f"{field_name}.{key}", required=field_required
                )
                if not is_valid:
                    return False, error, None
                sanitized_dict[key] = sanitized_value
            return True, "", sanitized_dict
        
        elif isinstance(data, list):
            # Validate each item in list
            sanitized_list = []
            for i, item in enumerate(data):
                # FIX: Chat messages should use 'prompt' type for longer content (10,000 chars vs 1,000)
                validation_type = 'prompt' if isinstance(item, dict) and 'content' in item else input_type
                is_valid, error, sanitized_value = self.validate_input(
                    item, validation_type, f"{field_name}[{i}]"
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


class PersistentRateLimiter:
    """File-based rate limiting that survives server restarts"""
    
    def __init__(self, storage_file: str = "rate_limits.json"):
        self.storage_file = Path(storage_file)
        self.data = {}
        self.load_limits()
        
    def load_limits(self):
        """Load existing rate limit data from file"""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.data = {}
        else:
            self.data = {}
    
    def save_limits(self):
        """Save rate limit data to file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError:
            pass  # Log error in production
    
    def is_allowed(self, client_id: str, config: Dict) -> bool:
        """Check if client is allowed based on persistent storage"""
        now = time.time()
        window_start = now - config['window']
        
        # Clean old entries
        self.cleanup_old_entries(window_start)
        
        # Check current requests
        client_requests = self.data.get(client_id, [])
        recent_requests = [r for r in client_requests if r > window_start]
        
        if len(recent_requests) >= config['requests']:
            return False
            
        # Add current request
        recent_requests.append(now)
        self.data[client_id] = recent_requests
        self.save_limits()
        return True
    
    def cleanup_old_entries(self, cutoff_time: float):
        """Remove old rate limit entries"""
        for client_id in list(self.data.keys()):
            requests = self.data[client_id]
            self.data[client_id] = [r for r in requests if r > cutoff_time]
        
        # Remove empty client entries
        self.data = {k: v for k, v in self.data.items() if v}

class SecurityAuditor:
    """Structured security event logging for comprehensive audit trails"""
    
    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = Path(log_file)
        
    def log_event(self, event_type: str, details: Dict):
        """Log structured security event"""
        event = {
            'timestamp': datetime.now(UTC).isoformat(),
            'event_type': event_type,
            'client_ip': details.get('client_ip'),
            'endpoint': details.get('endpoint'),
            'method': details.get('method'),
            'user_agent': details.get('user_agent'),
            'details': details
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except IOError:
            # Handle logging errors gracefully
            pass

class UniversalSecurityMiddleware(BaseHTTPMiddleware):
    """Universal security middleware for all endpoints"""
    
    def __init__(self, app, security_config: Dict):
        super().__init__(app)
        self.security_config = security_config
        self.rate_limiter = PersistentRateLimiter()
        self.auditor = SecurityAuditor()
        self.input_validator = UniversalInputValidator()
    
    def get_endpoint_config(self, path: str) -> Dict:
        """Get security configuration for endpoint"""
        return self.security_config.get('endpoints', {}).get(path, {})
    
    def get_session_id(self, request: Request) -> str:
        """Extract session ID from request using shared function"""
        return get_session_id_from_request(request)
    
    async def dispatch(self, request: Request, call_next):
        """Process all requests through universal security pipeline"""
        path = request.url.path
        endpoint_config = self.get_endpoint_config(path)
        client_host = request.client.host if request.client else "unknown"
        
        # COMPREHENSIVE DEBUG: Log ALL incoming requests
        logger.info(f"=== SECURITY MIDDLEWARE DEBUG ===")
        logger.info(f"Request: {request.method} {path}")
        logger.info(f"Client: {client_host}")
        logger.info(f"User-Agent: {request.headers.get('user-agent', 'None')}")
        logger.info(f"Endpoint Config: {endpoint_config}")
        
        # Skip security if globally disabled
        if not self.security_config.get('global', {}).get('enabled', True):
            logger.info("Security globally disabled, skipping all checks")
            return await call_next(request)
        
        # 1. Rate Limiting Check
        rate_limit_config = endpoint_config.get('rate_limiting')
        if rate_limit_config:
            logger.info(f"Rate limiting config found: {rate_limit_config}")
            session_id = self.get_session_id(request)
            if not self.rate_limiter.is_allowed(session_id, rate_limit_config):
                logger.warning(f"Rate limit exceeded for {session_id}")
                self.auditor.log_event('rate_limit_exceeded', {
                    'client_ip': client_host,
                    'endpoint': path,
                    'method': request.method,
                    'limit_config': rate_limit_config
                })
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": str(rate_limit_config.get('window', 60))}
                )
            logger.info(f"Rate limiting check passed")
        
        # 2. Session Validation Check
        if endpoint_config.get('session_required', False):
            logger.info(f"Session validation required for {path}")
            # Skip session validation for OPTIONS requests (CORS preflight)
            if request.method.upper() == 'OPTIONS':
                logger.info(f"Skipping session validation for OPTIONS request to {path}")
            else:
                # For now, basic session validation
                # In production, implement proper session management
                session_id = self.get_session_id(request)
                if session_id == "unknown":
                    logger.warning(f"Session validation failed for {path} - unknown session ID")
                    self.auditor.log_event('session_invalid', {
                        'client_ip': client_host,
                        'endpoint': path,
                        'method': request.method
                    })
                    raise HTTPException(
                        status_code=401,
                        detail="Valid session required"
                    )
                logger.info(f"Session validation passed for {path}")
        else:
            logger.info(f"Session validation NOT required for {path}")
        
        # 4. Input Validation Check - ONLY for requests with bodies
        validation_level = endpoint_config.get('input_validation', 'none')
        logger.info(f"Input validation level: {validation_level}")
        
        # FIX: Skip input validation entirely for OPTIONS requests
        if request.method.upper() == 'OPTIONS':
            logger.info(f"Skipping all security checks for OPTIONS request to {path} (CORS preflight)")
        elif validation_level != 'none' and request.method.upper() not in ['GET', 'HEAD', 'OPTIONS']:
            logger.info(f"Input validation required for {path}")
            try:
                request_body = await request.json()
                is_valid, error, sanitized = self.input_validator.validate_input(
                    request_body, validation_level, 'request_body', required=False
                )
                if not is_valid:
                    logger.error(f"Input validation failed for {path}: {error}")
                    self.auditor.log_event('input_validation_failed', {
                        'client_ip': client_host,
                        'endpoint': path,
                        'method': request.method,
                        'error': error,
                        'validation_level': validation_level
                    })
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid input: {error}",
                        headers={"X-Validation-Error": error}
                    )
                
                # Store validated data for endpoints to use
                request.state.validated_body = sanitized
                logger.info(f"Input validation passed for {path}")
            except Exception as e:
                # Only log as error if it's not a JSON parsing error for GET/HEAD/OPTIONS
                if request.method.upper() not in ['GET', 'HEAD', 'OPTIONS']:
                    logger.error(f"Request body parsing error for {request.method} {path}: {str(e)}")
                    self.auditor.log_event('request_format_invalid', {
                        'client_ip': client_host,
                        'endpoint': path,
                        'method': request.method,
                        'error': str(e)
                    })
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid request format"
                    )
                else:
                    # For GET/HEAD/OPTIONS, just continue without body validation
                    logger.info(f"No request body to validate for {request.method} {path}")
        else:
            # Skip validation for GET/HEAD/OPTIONS requests without bodies, but log for debugging
            logger.info(f"Skipping input validation for {request.method} {path} (no request body)")
        
        # 5. Log Successful Access
        logger.info(f"All security checks passed for {request.method} {path}")
        self.auditor.log_event('access_granted', {
            'client_ip': client_host,
            'endpoint': path,
            'method': request.method,
            'user_agent': request.headers.get('user-agent'),
            'security_config': endpoint_config
        })
        
        # 6. Process Request
        logger.info(f"Calling next middleware for {path}")
        response = await call_next(request)
        logger.info(f"Next middleware returned {response.status_code} for {path}")
        
        # 7. Add Security Headers
        if endpoint_config.get('security_headers', True):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
        
        # 8. Log Response
        self.auditor.log_event('response_sent', {
            'client_ip': client_host,
            'endpoint': path,
            'method': request.method,
            'status_code': response.status_code
        })
        
        return response

def get_session_id_from_request(request: Request) -> str:
    """
    Shared session ID extraction function for consistent session identification
    Used by both CSRF token endpoint and middleware
    """
    # Try to get session ID from various sources in order of preference
    # 1. Check for session cookie
    session_cookie = request.cookies.get('goldbox_session')
    if session_cookie:
        return f"cookie:{session_cookie}"
    
    # 2. Check for session header
    session_header = request.headers.get('X-Session-ID')
    if session_header:
        return f"header:{session_header}"
    
    # 3. Fall back to client IP + User-Agent hash
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get('user-agent', '')[:50]  # Truncate for consistency
    # Create a more stable session identifier using IP + User-Agent hash
    ip_ua_hash = hashlib.sha256(f"{client_ip}:{user_agent}".encode()).hexdigest()[:16]
    return f"ip_ua:{ip_ua_hash}"

# Initialize global instances
rate_limiter = RateLimiter()
auditor = SecurityAuditor()
validator = UniversalInputValidator()

# Security configuration for universal middleware
SECURITY_CONFIG = {
    "global": {
        "enabled": True,
        "audit_logging": True
    },
    "endpoints": {
        # Critical: Process chat endpoints (currently NO security)
        "/api/process_chat": {
            "rate_limiting": None,
            "input_validation": "none",
            "session_required": False,
            "security_headers": False
        },
        "/api/process_chat/validate": {
            "rate_limiting": {"requests": 20, "window": 60},
            "input_validation": "strict",
            "session_required": True,
            "security_headers": True
        },
        "/api/process_chat/status": {
            "rate_limiting": {"requests": 30, "window": 60},
            "input_validation": "basic",
            "session_required": True,
            "security_headers": True
        },
        "/api/process_chat/schemas": {
            "rate_limiting": {"requests": 50, "window": 60},
            "input_validation": "none",  # Public endpoint
            "session_required": False,
            "security_headers": True
        },
        
        # Existing: Simple chat endpoint (ALL SECURITY DISABLED FOR TESTING)
        "/api/simple_chat": {
            "rate_limiting": None,
            "input_validation": "none",
            "session_required": False,
            "security_headers": False
        },
        
        # Admin endpoints
        "/api/admin": {
            "rate_limiting": {"requests": 3, "window": 60},
            "input_validation": "strict",
            "session_required": True,
            "security_headers": True
        },
        
        # Public endpoints (basic security)
        "/api/health": {
            "rate_limiting": {"requests": 100, "window": 60},
            "input_validation": "none",
            "session_required": False,
            "security_headers": True
        },
        "/api/info": {
            "rate_limiting": {"requests": 50, "window": 60},
            "input_validation": "none",
            "session_required": False,
            "security_headers": True
        },
        "/api/start": {
            "rate_limiting": {"requests": 10, "window": 60},
            "input_validation": "none",
            "session_required": False,
            "security_headers": True
        },
        
        # Session initialization endpoint
        "/api/session/init": {
            "rate_limiting": {"requests": 20, "window": 60},
            "input_validation": "none",
            "session_required": False,
            "security_headers": True
        }
    }
}

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
                logger.error(f"Virtual environment missing required directory: {dir_name}")
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
        server_file = Path(__file__).parent / 'server.py'
        if server_file.exists():
            with open(server_file, 'r') as f:
                server_content = f.read()
                server_hash = hashlib.sha256(server_content.encode()).hexdigest()
                integrity_checks.append(f"server.py: {server_hash}")
                logger.info(f"server.py hash: {server_hash}")
        
        # Check security.py integrity (self-check)
        security_file = Path(__file__)
        if security_file.exists():
            with open(security_file, 'r') as f:
                security_content = f.read()
                security_hash = hashlib.sha256(security_content.encode()).hexdigest()
                integrity_checks.append(f"security.py: {security_hash}")
                logger.info(f"security.py hash: {security_hash}")
        
        return integrity_checks
        
    except Exception as e:
        logger.error(f"Error verifying file integrity: {e}")
        return []

def verify_file_permissions():
    """Verify and enforce proper file permissions"""
    try:
        permission_issues = []
        
        # Check log file permissions
        log_file_path = Path('goldbox.log')
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
        critical_deps = ['fastapi', 'uvicorn', 'python-dotenv', 'cryptography']
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

def validate_prompt(prompt, validator=None):
    """
    Legacy function for backward compatibility
    Uses universal validator if provided, otherwise basic validation
    """
    if validator is None:
        validator = UniversalInputValidator()
    
    is_valid, error, sanitized = validator.validate_input(
        prompt, 'prompt', 'prompt', required=True
    )
    if not is_valid:
        raise ValueError(error)
    return sanitized
