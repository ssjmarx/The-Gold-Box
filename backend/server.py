#!/usr/bin/env python3
"""
The Gold Box - Python Backend Server
AI-powered Foundry VTT Module Backend

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
Dependencies: Flask (BSD 3-Clause), Flask-CORS (MIT)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys
import time
import os
import socket
import re
import html
from datetime import datetime
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional, Tuple, Union

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
EXPECTED_API_KEY = os.environ.get('GOLD_BOX_API_KEY', '')
GOLD_BOX_PORT = int(os.environ.get('GOLD_BOX_PORT', 5001))
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', 'goldbox.log')

# Rate limiting configuration
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get('RATE_LIMIT_MAX_REQUESTS', 5))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get('RATE_LIMIT_WINDOW_SECONDS', 60))

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
    
    # Production - no origins by default (must be explicitly configured)
    logger.error("Production environment requires explicit CORS_ORIGINS configuration")
    return []

# Enhanced CORS configuration
CORS_ORIGINS = get_cors_origins()

# Initialize Flask app
app = Flask(__name__)

# Enhanced CORS configuration with security headers
def configure_cors():
    """Configure CORS with security-focused settings"""
    if not CORS_ORIGINS:
        logger.error("No CORS origins configured - API will be inaccessible")
        return False
    
    # Configure CORS with restrictive settings
    CORS(app, 
         origins=CORS_ORIGINS,
         methods=['GET', 'POST', 'OPTIONS'],  # Explicitly allowed methods
         allow_headers=['Content-Type', 'X-API-Key'],  # Only necessary headers
         expose_headers=[],  # Don't expose additional headers
         supports_credentials=False,  # No cookie-based auth
         max_age=86400,  # Cache preflight requests for 24 hours
         vary_header=True)  # Proper Vary header for caching
    
    logger.info(f"CORS configured for {len(CORS_ORIGINS)} origins")
    return True

# Configure CORS
configure_cors()

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
    Enhanced API key verification using universal validator
    Returns (is_valid: bool, error_message: str)
    """
    # If no API key is expected, allow all requests (development mode)
    if not EXPECTED_API_KEY:
        return True, None
    
    # Get API key from headers
    provided_key = request.headers.get('X-API-Key')
    
    # Check if API key is provided
    if not provided_key:
        logger.warning(f"Missing API key from {request.remote_addr}")
        return False, "API key required"
    
    # Validate API key format
    is_valid, error = validator.validate_api_key(provided_key)
    if not is_valid:
        logger.warning(f"Invalid API key format from {request.remote_addr}: {error}")
        return False, "Invalid API key format"
    
    # Check if API key matches
    if provided_key != EXPECTED_API_KEY:
        logger.warning(f"Invalid API key from {request.remote_addr}")
        return False, "Invalid API key"
    
    logger.info(f"Valid API key from {request.remote_addr}")
    return True, None

# Enhanced request middleware for security
@app.before_request
def security_middleware():
    """Add security headers and log requests"""
    # Log incoming requests
    logger.info(f"{request.method} {request.path} from {request.remote_addr}")
    
    # Add security headers to API responses
    if request.path.startswith('/api/'):
        # Note: This will be applied after the request is processed
        pass
    return None

@app.after_request
def add_security_headers(response):
    """Add security headers to API responses"""
    if request.path.startswith('/api/'):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route('/api/process', methods=['POST'])
def process_prompt():
    """
    Enhanced AI processing endpoint with comprehensive input validation
    """
    try:
        # Verify API key
        is_valid, error_msg = verify_api_key(request)
        if not is_valid:
            return jsonify({
                'error': error_msg,
                'status': 'error',
                'validation_step': 'api_key'
            }), 401
        
        # Rate limiting
        client_id = request.remote_addr
        if not rate_limiter.is_allowed(client_id):
            return jsonify({
                'error': 'Rate limit exceeded. Please try again later.',
                'status': 'error',
                'rate_limit_info': {
                    'max_requests': rate_limiter.max_requests,
                    'window_seconds': rate_limiter.window_seconds,
                    'current_requests': len(rate_limiter.requests.get(client_id, []))
                }
            }), 429
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Invalid JSON data',
                'status': 'error',
                'validation_step': 'json_parsing'
            }), 400
        
        # Validate AI request using universal validator
        is_valid, error, sanitized_request = validator.validate_ai_request(data)
        if not is_valid:
            return jsonify({
                'error': error,
                'status': 'error',
                'validation_step': 'ai_request',
                'received_fields': list(data.keys()) if isinstance(data, dict) else []
            }), 400
        
        # Log the validated request (without sensitive content)
        prompt_length = len(sanitized_request.get('prompt', ''))
        logger.info(f"Processing AI request from {client_id}: {prompt_length} characters")
        
        # For now, just echo back the sanitized prompt
        # This will be replaced with actual AI processing later
        response = {
            'status': 'success',
            'response': sanitized_request['prompt'],  # Echo back sanitized prompt
            'original_prompt': sanitized_request['prompt'],
            'timestamp': datetime.now().isoformat(),
            'processing_time': 0.001,  # Simulated processing time
            'message': 'AI functionality: Basic echo server - prompt sanitized and returned unchanged',
            'api_key_verified': True,
            'validation_passed': True,
            'sanitization_applied': True,
            'rate_limit_remaining': rate_limiter.max_requests - len(rate_limiter.requests.get(client_id, [])),
            'ai_parameters': {k: v for k, v in sanitized_request.items() if k != 'prompt'}
        }
        
        logger.info(f"Response sent to {client_id}: Success with validation")
        
        return jsonify(response)
        
    except ValueError as e:
        logger.warning(f"Validation error from {client_id}: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error',
            'validation_step': 'input_validation'
        }), 400
        
    except Exception as e:
        logger.error(f"Unexpected error from {client_id}: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'status': 'error',
            'validation_step': 'server_processing'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '0.1.0',
        'service': 'The Gold Box Backend',
        'api_key_required': bool(EXPECTED_API_KEY),
        'environment': FLASK_ENV,
        'validation_enabled': True,
        'universal_validator': True,
        'rate_limiting': {
            'max_requests': RATE_LIMIT_MAX_REQUESTS,
            'window_seconds': RATE_LIMIT_WINDOW_SECONDS
        },
        'cors': {
            'origins_count': len(CORS_ORIGINS),
            'configured': len(CORS_ORIGINS) > 0,
            'methods': ['GET', 'POST', 'OPTIONS']
        }
    })

@app.route('/api/info', methods=['GET'])
def service_info():
    """
    Enhanced service information endpoint
    """
    return jsonify({
        'name': 'The Gold Box Backend',
        'description': 'AI-powered Foundry VTT Module Backend with Universal Input Validation',
        'version': '0.1.0',
        'status': 'running',
        'environment': FLASK_ENV,
        'api_key_required': bool(EXPECTED_API_KEY),
        'validation_features': {
            'universal_validator': True,
            'input_sanitization': True,
            'security_pattern_checking': True,
            'type_specific_validation': True,
            'structured_data_support': True,
            'ai_parameter_validation': True
        },
        'supported_input_types': list(validator.ALLOWED_CHAR_PATTERNS.keys()),
        'size_limits': validator.SIZE_LIMITS,
        'endpoints': {
            'process': 'POST /api/process - Process AI prompts (enhanced validation)',
            'health': 'GET /api/health - Health check',
            'info': 'GET /api/info - Service information',
            'start': 'POST /api/start - Auto-start instructions'
        },
        'license': 'CC-BY-NC-SA 4.0',
        'dependencies': {
            'Flask': 'BSD 3-Clause License',
            'Flask-CORS': 'MIT License'
        },
        'security': {
            'api_authentication': bool(EXPECTED_API_KEY),
            'rate_limiting': True,
            'cors_restrictions': len(CORS_ORIGINS) > 0,
            'cors_origins': CORS_ORIGINS if FLASK_ENV == 'development' else 'configured',
            'input_validation': 'UniversalInputValidator',
            'security_headers': True,
            'xss_protection': True,
            'sql_injection_protection': True,
            'command_injection_protection': True
        }
    })

@app.route('/api/start', methods=['POST'])
def start_backend():
    """
    Attempt to start backend server (for auto-start functionality)
    Note: This is a simplified approach since browser can't spawn processes directly
    """
    return jsonify({
        'status': 'info',
        'message': 'Please start the backend manually: cd backend && source venv/bin/activate && python server.py',
        'instructions': {
            'step1': 'Open terminal',
            'step2': 'Navigate to backend directory',
            'step3': 'Activate virtual environment: source venv/bin/activate',
            'step4': 'Start server: python server.py'
        },
        'auto_start_note': 'Automatic process spawning is blocked by browser security restrictions',
        'environment_note': f'Current environment: {FLASK_ENV}',
        'validation_status': 'Universal input validation is active',
        'cors_note': f'CORS configured for {len(CORS_ORIGINS)} origins'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error',
        'available_endpoints': ['/api/process', '/api/health', '/api/info', '/api/start'],
        'validator_features': ['universal_validation', 'security_checking', 'sanitization']
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed',
        'status': 'error',
        'allowed_methods': ['GET', 'POST', 'OPTIONS']
    }), 405

if __name__ == '__main__':
    # Check if running in development or production
    debug_mode = FLASK_DEBUG
    
    # Find an available port
    start_port = GOLD_BOX_PORT
    available_port = find_available_port(start_port)
    
    if not available_port:
        print(f"[ERROR] No available ports found starting from {start_port}")
        print("[ERROR] Please check if another application is using these ports")
        sys.exit(1)
    
    print("=" * 60)
    print("The Gold Box Backend Server")
    print("=" * 60)
    print(f"Environment: {FLASK_ENV}")
    print(f"Debug mode: {debug_mode}")
    print(f"API Key Required: {bool(EXPECTED_API_KEY)}")
    if EXPECTED_API_KEY:
        print(f"API Key: {'*' * (len(EXPECTED_API_KEY) - 4)}{EXPECTED_API_KEY[-4:]}")  # Show last 4 chars
    print(f"Rate Limiting: {RATE_LIMIT_MAX_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds")
    
    # CORS Configuration Summary
    print(f"CORS Origins: {len(CORS_ORIGINS)} configured")
    if FLASK_ENV == 'development':
        print("  Development CORS origins (localhost only):")
        for origin in CORS_ORIGINS:
            print(f"    - {origin}")
    else:
        print("  Production CORS origins (explicitly configured)")
        for origin in CORS_ORIGINS:
            print(f"    - {origin}")
    
    print(f"Universal Input Validator: ENABLED")
    print(f"Security Features: XSS, SQL Injection, Command Injection Protection")
    print(f"Security Headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection")
    print(f"Server starting on http://localhost:{available_port}")
    print("Available endpoints:")
    print("  POST /api/process - Process AI prompts (enhanced validation)")
    print("  GET  /api/health  - Health check")
    print("  GET  /api/info    - Service information")
    print("  POST /api/start   - Auto-start instructions")
    print("=" * 60)
    print("Universal Input Validation Features:")
    print("  - Dangerous pattern detection")
    print("  - Character set validation")
    print("  - Type-specific validation (URL, email, filename)")
    print("  - Structured data support (dict/list)")
    print("  - AI parameter validation")
    print("  - Input sanitization and escaping")
    print("=" * 60)
    
    # Start server with auto-reload disabled to prevent duplicate startup messages
    app.run(
        host='localhost',
        port=available_port,
        debug=debug_mode,
        use_reloader=False  # Disable Flask's auto-restart feature
    )
