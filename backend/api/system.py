#!/usr/bin/env python3
"""
System endpoint
Provides backend startup instructions and system information
"""

from fastapi import APIRouter
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def create_system_router(global_config):
    """
    Create and configure system router
    
    Args:
        global_config: Global configuration dictionary
    """
    router = APIRouter()
    
    # Extract configuration
    FLASK_ENV = global_config['FLASK_ENV']
    CORS_ORIGINS = global_config['CORS_ORIGINS']
    
    @router.post("/start")
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
    
    return router
