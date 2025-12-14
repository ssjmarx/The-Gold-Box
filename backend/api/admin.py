#!/usr/bin/env python3
"""
Admin endpoint
Password-protected admin endpoint for server management
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime
from typing import Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

def create_admin_router(global_config):
    """
    Create and configure admin router
    
    Args:
        global_config: Global configuration dictionary
    """
    router = APIRouter()
    
    @router.post("/admin")
    async def admin_endpoint(request: Request):
        """
        Password-protected admin endpoint for server management
        Requires admin password in X-Admin-Password header
        Security is now handled by UniversalSecurityMiddleware
        """
        try:
            # Get admin password from headers
            admin_password = request.headers.get('X-Admin-Password')
            if not admin_password:
                raise HTTPException(
                    status_code=401,
                    detail="Admin password required in X-Admin-Password header",
                    headers={"WWW-Authenticate": 'Basic realm="The Gold Box Admin"'}
                )
            
            # Use service factory to get key manager
            from services.system_services.service_factory import get_key_manager, get_settings_manager
            
            key_manager = get_key_manager()
            
            # Verify admin password using service factory
            is_valid, error_msg = key_manager.verify_password(admin_password)
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
                        "start": "/api/start"
                    },
                    "security": "Universal Security Middleware is active"
                }
            
            elif command == 'reload_keys':
                # Reload environment variables using service factory
                if key_manager.set_environment_variables():
                    # Reload global variables
                    OPENAI_API_KEY = os.environ.get('GOLD_BOX_OPENAI_COMPATIBLE_API_KEY', '')
                    NOVELAI_API_KEY = os.environ.get('GOLD_BOX_NOVELAI_API_API_KEY', '')
                    
                    logger.info("Environment variables reloaded successfully")
                    return {
                        'status': 'success',
                        'command': 'reload_keys',
                        'message': 'Environment variables reloaded successfully',
                        'timestamp': datetime.now().isoformat(),
                        'keys_status': key_manager.get_key_status()
                    }
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to set environment variables"
                    )
            
            elif command == 'set_admin_password':
                # Set new admin password using service factory
                new_password = request_data.get('password', '')
                if key_manager.set_password(new_password):
                    # Save updated configuration
                    if key_manager.save_keys(key_manager.keys_data):
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
                # Update frontend settings using service factory
                settings_mgr = get_settings_manager()
                
                frontend_settings_data = request_data.get('settings', {})
                
                if settings_mgr.update_settings(frontend_settings_data):
                    return {
                        'status': 'success',
                        'command': 'update_settings',
                        'message': f'Frontend settings updated: {len(frontend_settings_data)} settings loaded',
                        'timestamp': datetime.now().isoformat(),
                        'settings_count': len(frontend_settings_data),
                        'current_settings': settings_mgr.get_settings()
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
    
    return router
