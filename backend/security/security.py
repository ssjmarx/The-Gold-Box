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
import configparser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta, UTC
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .input_validator import UniversalInputValidator

# Get absolute path to backend directory (where server.py is located)
BACKEND_DIR = Path(__file__).parent.parent.absolute()

def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path based on backend directory.
    This ensures consistent file operations regardless of where script is called from.
    """
    return (BACKEND_DIR / relative_path).resolve()

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

# SessionManager replaced by SessionValidator in sessionvalidator.py

class PersistentRateLimiter:
    """File-based rate limiting that survives server restarts"""
    
    def __init__(self, storage_file: str = "server_files/rate_limits.json"):
        self.storage_file = get_absolute_path(storage_file)
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
    
    def __init__(self, log_file: str = "server_files/security_audit.log"):
        self.log_file = get_absolute_path(log_file)
        
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
        # Import SessionValidator here to avoid circular imports
        from .sessionvalidator import session_validator
        self.session_validator = session_validator
    
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
                # Use SessionValidator for proper session validation
                session_id = self.get_session_id(request)
                
                # Extract session ID from header/cookie
                session_id = self.get_session_id(request)
                if session_id.startswith("header:"):
                    actual_session_id = session_id.replace("header:", "")
                elif session_id.startswith("cookie:"):
                    actual_session_id = session_id.replace("cookie:", "")
                else:
                    # IP-based sessions are not valid for protected endpoints
                    logger.warning(f"Session validation failed for {path} - IP-based session not allowed")
                    self.auditor.log_event('session_invalid', {
                        'client_ip': client_host,
                        'endpoint': path,
                        'method': request.method
                    })
                    raise HTTPException(
                        status_code=401,
                        detail="Valid session ID required (from header or cookie)"
                    )
                
                # Validate session with SessionValidator
                session_info = self.session_validator.get_session_info(actual_session_id)
                if not session_info:
                    logger.warning(f"Session validation failed for {path} - session not found: {actual_session_id}")
                    self.auditor.log_event('session_invalid', {
                        'client_ip': client_host,
                        'endpoint': path,
                        'method': request.method,
                        'session_id': actual_session_id
                    })
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Invalid or expired session", "detail": "Session not found - please initialize a session"}
                    )
                
                if not self.session_validator.is_session_valid(actual_session_id):
                    logger.warning(f"Session validation failed for {path} - session expired: {actual_session_id}")
                    self.auditor.log_event('session_expired', {
                        'client_ip': client_host,
                        'endpoint': path,
                        'method': request.method,
                        'session_id': actual_session_id
                    })
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Session expired", "detail": "Your session has expired - please initialize a new session"}
                    )
                
                # Check client IP match for security
                if session_info['client_ip'] != client_host:
                    logger.warning(f"Session validation failed for {path} - IP mismatch: {session_info['client_ip']} vs {client_host}")
                    self.auditor.log_event('session_ip_mismatch', {
                        'client_ip': client_host,
                        'endpoint': path,
                        'method': request.method,
                        'session_id': actual_session_id,
                        'expected_ip': session_info['client_ip']
                    })
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Session IP mismatch", "detail": "Session IP address has changed"}
                    )
                
                logger.info(f"Session validation passed for {path} - session: {actual_session_id}")
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
                    request_body, 'text', 'request_body', required=False, validation_level=validation_level
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
    Used by session validation middleware
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

def load_security_config(config_file: str = "security_config.ini") -> Dict:
    """
    Load security configuration from INI file
    
    Args:
        config_file: Path to INI configuration file
        
    Returns:
        Dict: Security configuration dictionary
    """
    config = configparser.ConfigParser()
    config_path = get_absolute_path(config_file)
    
    if not config_path.exists():
        logger.warning(f"Security config file not found: {config_path}, using defaults")
        return get_default_security_config()
    
    try:
        config.read(config_path)
        logger.info(f"Loaded security configuration from {config_path}")
        
        # Parse configuration
        security_config = {"global": {}, "endpoints": {}}
        
        # Parse global settings
        if 'global' in config:
            global_section = config['global']
            security_config["global"]["enabled"] = global_section.getboolean('enabled', True)
            security_config["global"]["audit_logging"] = global_section.getboolean('audit_logging', True)
        
        # Parse endpoint configurations
        for section_name in config.sections():
            if section_name.startswith('endpoint:'):
                endpoint_path = section_name[9:]  # Remove 'endpoint:' prefix
                section = config[section_name]
                
                endpoint_config = {
                    "rate_limiting": {
                        "requests": section.getint('rate_limit_requests', 10),
                        "window": section.getint('rate_limit_window', 60)
                    },
                    "input_validation": section.get('input_validation', 'basic'),
                    "session_required": section.getboolean('session_required', False),
                    "security_headers": section.getboolean('security_headers', True)
                }
                
                security_config["endpoints"][endpoint_path] = endpoint_config
        
        return security_config
        
    except Exception as e:
        logger.error(f"Error loading security config: {e}, using defaults")
        return get_default_security_config()

def get_default_security_config() -> Dict:
    """
    Get default security configuration
    
    Returns:
        Dict: Default security configuration
    """
    return {
        "global": {
            "enabled": True,
            "audit_logging": True
        },
        "endpoints": {
            "/api/process_chat": {
                "rate_limiting": {"requests": 10, "window": 60},
                "input_validation": "basic",
                "session_required": True,
                "security_headers": True
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
                "input_validation": "none",
                "session_required": False,
                "security_headers": True
            },
            "/api/simple_chat": {
                "rate_limiting": {"requests": 10, "window": 60},
                "input_validation": "strict",
                "session_required": False,
                "security_headers": True
            },
            "/api/admin": {
                "rate_limiting": {"requests": 10, "window": 60},
                "input_validation": "strict",
                "session_required": True,
                "security_headers": True
            },
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
        req_file = get_absolute_path('requirements.txt')
        if req_file.exists():
            with open(req_file, 'r') as f:
                req_content = f.read()
                req_hash = hashlib.sha256(req_content.encode()).hexdigest()
                integrity_checks.append(f"requirements.txt: {req_hash}")
                logger.info(f"requirements.txt hash: {req_hash}")
        
        # Check server.py integrity
        server_file = get_absolute_path('server.py')
        if server_file.exists():
            with open(server_file, 'r') as f:
                server_content = f.read()
                server_hash = hashlib.sha256(server_content.encode()).hexdigest()
                integrity_checks.append(f"server.py: {server_hash}")
                logger.info(f"server.py hash: {server_hash}")
        
        # Check security.py integrity (self-check)
        security_file = get_absolute_path('security/security.py')
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
        log_file_path = get_absolute_path('goldbox.log')
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
        key_file_path = get_absolute_path('server_files/keys.enc')
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

# Security configuration for universal middleware (loaded from INI)
SECURITY_CONFIG = load_security_config()
