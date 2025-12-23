#!/usr/bin/env python3
"""
Session management endpoint
Handles session initialization, extension, and management
"""

from fastapi import APIRouter, Request, HTTPException
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def create_session_router(global_config):
    """
    Create and configure session management router
    
    Args:
        global_config: Global configuration dictionary
    """
    router = APIRouter()
    
    # Extract configuration
    SESSION_TIMEOUT_MINUTES = global_config['SESSION_TIMEOUT_MINUTES']
    
    @router.post("/session/init")
    async def initialize_session(request: Request):
        """
        Initialize or refresh a session for frontend
        Supports both creating new sessions and extending existing ones
        Returns session ID and expiry time for session management
        Security is handled by UniversalSecurityMiddleware
        """
        try:
            # Import service factory functions for consistent access patterns
            from services.system_services.service_factory import get_session_manager, get_ai_session_manager
            
            session_mgr = get_session_manager()
            ai_session_mgr = get_ai_session_manager()
            
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
                if session_mgr.is_session_valid(preferred_session_id):
                    # Update session activity and extend expiry
                    session_mgr.update_session_activity(preferred_session_id)
                    session_id = preferred_session_id
                    was_extended = True
                    # Session extended
                else:
                    logger.info(f"Preferred session {preferred_session_id} invalid, creating new session for {client_host}")
            
            # Create new session if extension wasn't possible or requested
            if not session_id:
                session_id = session_mgr.create_session(request)
                was_extended = False
                # New session created
            
            # Generate expiry time (default 30 minutes from now)
            expiry_time = datetime.now() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            
            # Generate CSRF token for session
            csrf_token = session_mgr.generate_csrf_token(session_id)
            
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
    
    @router.post("/ai_session/init")
    async def init_ai_session(request: Request):
        """
        Initialize or get AI session for conversation context
        
        Creates new AI session or continues existing one
        Returns session ID for use in AI chat calls
        Security is handled by UniversalSecurityMiddleware
        """
        try:
            # Import service factory functions
            from services.system_services.service_factory import get_ai_session_manager
            
            ai_session_mgr = get_ai_session_manager()
            
            # Get request body for parameters
            request_data = {}
            try:
                request_data = await request.json()
            except Exception:
                request_data = {}
            
            # Get client information for session creation
            client_host = request.client.host if request.client else "unknown"
            client_id = request_data.get('client_id', client_host)
            
            # Get preferred session ID to continue existing conversation
            preferred_session_id = request_data.get('session_id')
            
            # Create or get AI session
            session_id = ai_session_mgr.create_or_get_session(client_id, preferred_session_id)
            
            # Get session information for response
            session_info = ai_session_mgr.get_session_info(session_id)
            
            return {
                'session_id': session_id,
                'session_info': session_info,
                'message': 'AI session initialized successfully'
            }
            
        except Exception as e:
            logger.error(f"AI session initialization error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize AI session"
            )
    
    @router.get("/ai_session/status/{session_id}")
    async def get_ai_session_status(request: Request, session_id: str):
        """
        Get status and information about AI session
        
        Returns session information for debugging/monitoring
        Security is handled by UniversalSecurityMiddleware
        """
        try:
            # Import service factory functions
            from services.system_services.service_factory import get_ai_session_manager
            
            ai_session_mgr = get_ai_session_manager()
            
            # Get session information
            session_info = ai_session_mgr.get_session_info(session_id)
            
            if not session_info:
                raise HTTPException(
                    status_code=404,
                    detail="AI session not found or expired"
                )
            
            return {
                'session_info': session_info,
                'message': 'AI session status retrieved successfully'
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"AI session status error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get AI session status"
            )
    
    @router.post("/ai_session/clear/{session_id}")
    async def clear_ai_session(request: Request, session_id: str):
        """
        Clear AI session timestamp to force full context on next call
        
        Clears the timestamp so next AI call gets full message context
        Security is handled by UniversalSecurityMiddleware
        """
        try:
            # Import service factory functions
            from services.system_services.service_factory import get_ai_session_manager
            
            ai_session_mgr = get_ai_session_manager()
            
            # Clear session timestamp
            success = ai_session_mgr.clear_session_timestamp(session_id)
            
            if not success:
                raise HTTPException(
                    status_code=404,
                    detail="AI session not found or expired"
                )
            
            return {
                'session_id': session_id,
                'success': success,
                'message': 'AI session timestamp cleared successfully' if success else 'Failed to clear AI session timestamp'
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"AI session clear error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to clear AI session"
            )
    
    @router.get("/ai_session/stats")
    async def get_ai_session_stats(request: Request):
        """
        Get statistics about all AI sessions
        
        Returns session statistics for monitoring/debugging
        Security is handled by UniversalSecurityMiddleware
        """
        try:
            # Import service factory functions
            from services.system_services.service_factory import get_ai_session_manager
            
            ai_session_mgr = get_ai_session_manager()
            
            # Get session statistics
            stats = ai_session_mgr.get_stats()
            
            return {
                'stats': stats,
                'message': 'AI session statistics retrieved successfully'
            }
            
        except Exception as e:
            logger.error(f"AI session stats error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get AI session statistics"
            )
    
    return router
