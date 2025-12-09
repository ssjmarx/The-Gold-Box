"""
The Gold Box - Startup Security Module

Handles all security-related initialization during server startup.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

def initialize_security_middleware(app: FastAPI, cors_origins: list, security_config: Dict[str, Any]) -> bool:
    """
    Initialize security middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        cors_origins: List of allowed CORS origins
        security_config: Security configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Enhanced CORS configuration with security headers (BEFORE security middleware)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-API-Key", "X-Admin-Password", "X-Session-ID"],
            expose_headers=[],
            max_age=86400,
        )
        
        # Add Universal Security Middleware AFTER CORS (so it runs after CORS handles OPTIONS)
        from ..security.security import UniversalSecurityMiddleware
        app.add_middleware(UniversalSecurityMiddleware, security_config=security_config)
        
        logger.info(f"CORS configured for {len(cors_origins)} origins")
        logger.info("Universal Security Middleware integrated")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize security middleware: {e}")
        return False

def setup_rate_limiting(max_requests: int, window_seconds: int):
    """
    Set up rate limiting for the application.
    
    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
        
    Returns:
        RateLimiter instance or None if failed
    """
    try:
        from ..security.security import RateLimiter
        rate_limiter = RateLimiter(max_requests=max_requests, window_seconds=window_seconds)
        logger.info(f"Rate limiting configured: {max_requests} requests per {window_seconds} seconds")
        return rate_limiter
    except Exception as e:
        logger.error(f"Failed to setup rate limiting: {e}")
        return None

def initialize_session_manager():
    """
    Initialize the session manager for the application.
    
    Returns:
        SessionManager instance or None if failed
    """
    try:
        from ..security.sessionvalidator import session_validator
        logger.info("Session manager initialized")
        return session_validator
    except Exception as e:
        logger.error(f"Failed to initialize session manager: {e}")
        return None

def initialize_global_validator():
    """
    Initialize the global input validator.
    
    Returns:
        UniversalInputValidator instance or None if failed
    """
    try:
        from ..security.security import UniversalInputValidator
        validator = UniversalInputValidator()
        logger.info("Global input validator initialized")
        return validator
    except Exception as e:
        logger.error(f"Failed to initialize global validator: {e}")
        return None

def validate_server_security(validator, session_manager, rate_limiter, cors_origins: list) -> bool:
    """
    Validate that all security components are properly initialized.
    
    Args:
        validator: Input validator instance
        session_manager: Session manager instance
        rate_limiter: Rate limiter instance
        cors_origins: List of CORS origins
        
    Returns:
        True if all security components are valid, False otherwise
    """
    try:
        security_status = {
            'input_validator': validator is not None,
            'session_manager': session_manager is not None,
            'rate_limiter': rate_limiter is not None,
            'cors_configured': len(cors_origins) > 0,
            'cors_count': len(cors_origins)
        }
        
        all_valid = all(security_status.values())
        
        if all_valid:
            logger.info("All security components validated successfully")
        else:
            logger.warning(f"Security validation issues: {security_status}")
            
        return all_valid
        
    except Exception as e:
        logger.error(f"Failed to validate server security: {e}")
        return False

def get_security_components(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get and initialize all security components.
    
    Args:
        config: Server configuration dictionary
        
    Returns:
        Dictionary containing all initialized security components
    """
    components = {}
    
    # Setup rate limiting
    components['rate_limiter'] = setup_rate_limiting(
        config['RATE_LIMIT_MAX_REQUESTS'],
        config['RATE_LIMIT_WINDOW_SECONDS']
    )
    
    # Initialize session manager
    components['session_manager'] = initialize_session_manager()
    
    # Initialize global validator
    components['validator'] = initialize_global_validator()
    
    # Validate all components
    security_valid = validate_server_security(
        components['validator'],
        components['session_manager'],
        components['rate_limiter'],
        config['CORS_ORIGINS']
    )
    
    components['security_valid'] = security_valid
    
    return components
