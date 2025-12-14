#!/usr/bin/env python3
"""
Health check endpoint
Provides service health status and basic information
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Union, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Pydantic models for response validation
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

def create_health_router(global_config):
    """
    Create and configure health check router
    
    Args:
        global_config: Global configuration dictionary
    """
    router = APIRouter()
    
    # Extract configuration
    OPENAI_API_KEY = global_config['OPENAI_API_KEY']
    NOVELAI_API_KEY = global_config['NOVELAI_API_KEY']
    FLASK_ENV = global_config['FLASK_ENV']
    RATE_LIMIT_MAX_REQUESTS = global_config['RATE_LIMIT_MAX_REQUESTS']
    RATE_LIMIT_WINDOW_SECONDS = global_config['RATE_LIMIT_WINDOW_SECONDS']
    CORS_ORIGINS = global_config['CORS_ORIGINS']
    
    # Import utils
    from .utils import get_configured_providers
    
    @router.get("/health", response_model=HealthResponse)
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
    
    return router
