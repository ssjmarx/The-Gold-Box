"""
API Chat Endpoint for Gold Box v0.3.0
Handles chat processing via Foundry REST API instead of HTML scraping
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import json
import asyncio
import subprocess
import os
from datetime import datetime

from server.api_chat_processor import APIChatProcessor
from server.ai_chat_processor import AIChatProcessor
from server.ai_service import AIService
from server.processor import ChatContextProcessor

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["api_chat"])

# Request models
class APIChatRequest(BaseModel):
    """Request model for API chat endpoint"""
    context_count: Optional[int] = Field(15, description="Number of recent messages to retrieve", ge=1, le=50)
    settings: Optional[Dict[str, Any]] = Field(None, description="Frontend settings including provider info")

class APIChatResponse(BaseModel):
    """Response model for API chat endpoint"""
    success: bool = Field(..., description="Whether request was successful")
    response: Optional[str] = Field(None, description="AI response as formatted text")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if failed")

# Global instances
api_chat_processor = APIChatProcessor()
ai_chat_processor = AIChatProcessor()
from server.provider_manager import ProviderManager
provider_manager = ProviderManager()
ai_service = AIService(provider_manager)  # Properly initialized with provider manager

@router.post("/api_chat", response_model=APIChatResponse)
async def api_chat(http_request: Request, request: APIChatRequest):
    """
    Process chat using Foundry REST API instead of HTML scraping
    
    This endpoint:
    1. Gets validated data from universal security middleware
    2. Ensures relay server is running
    3. Collects chat messages via REST API
    4. Converts to compact JSON for AI processing
    5. Processes through AI services
    6. Returns formatted response
    """
    try:
        # Get validated data from universal security middleware if available
        if hasattr(http_request.state, 'validated_body') and http_request.state.validated_body:
            # Use middleware-validated data for enhanced security
            validated_request = http_request.state.validated_body
            context_count = validated_request.get('context_count', request.context_count)
            settings = validated_request.get('settings', request.settings)
            logger.info("Processing API chat request with middleware-validated data")
            logger.info(f"DEBUG: Request body from middleware: {validated_request}")
        else:
            # Fallback to original request data (should not happen with proper middleware)
            context_count = request.context_count
            settings = request.settings
            logger.info("Processing API chat request with original request data")
        
        logger.info(f"DEBUG: Final context_count: {context_count}, settings: {settings}")
        
        # Step 1: Collect chat messages via REST API (relay server is started by main server)
        logger.info(f"Collecting {context_count} chat messages via REST API")
        api_messages = await collect_chat_messages_api(context_count)
        
        # Step 2: Convert to compact JSON
        compact_messages = api_chat_processor.process_api_messages(api_messages)
        
        # Step 3: Process through AI (use unified settings handling like other endpoints)
        if not settings:
            # Use default settings for backward compatibility
            settings = {
                'general llm provider': 'openai',
                'general llm model': 'gpt-3.5-turbo',
                'general llm base url': None,
                'general llm timeout': 30,
                'general llm max retries': 3,
                'general llm custom headers': None
            }
        
        # Extract provider configuration from settings (same as simple_chat endpoint)
        provider_id = settings.get('general llm provider', 'openai')
        model = settings.get('general llm model', 'gpt-3.5-turbo')
        base_url = settings.get('general llm base url', '')
        api_version = settings.get('general llm version', 'v1')
        timeout = settings.get('general llm timeout', 30)
        max_retries = settings.get('general llm max retries', 3)
        custom_headers_str = settings.get('general llm custom headers', '{}')
        
        # Parse custom headers if provided
        custom_headers = {}
        try:
            if custom_headers_str and custom_headers_str.strip():
                custom_headers = json.loads(custom_headers_str)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Invalid custom headers JSON: {e}")
            custom_headers = {}
        
        client_host = http_request.client.host if http_request.client else "unknown"
        logger.info(f"Processing API chat request from {client_host}: provider={provider_id}, model={model}")
        logger.info(f"Settings: base_url={base_url}, api_version={api_version}, timeout={timeout}, max_retries={max_retries}")
        
        # Step 4: Convert compact messages to JSON string for AI
        compact_json_context = json.dumps(compact_messages, indent=2)
        
        # Step 5: Prepare AI messages
        processor = ChatContextProcessor()
        system_prompt = processor.generate_system_prompt()
        
        ai_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\nPlease respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use the compact JSON format specified in the system prompt."}
        ]
        
        # Step 6: Call AI service with proper settings
        ai_response_data = await ai_service.process_compact_context(
            processed_messages=compact_messages,
            system_prompt=system_prompt,
            settings=settings
        )
        
        ai_response = ai_response_data.get("response", "")
        tokens_used = ai_response_data.get("tokens_used", 0)
        
        # Step 7: Process AI response back to API format (for future use)
        api_formatted = ai_chat_processor.process_ai_response(ai_response, compact_messages)
        
        # Step 8: Return response
        return APIChatResponse(
            success=True,
            response=ai_response,
            metadata={
                "context_count": len(compact_messages),
                "tokens_used": tokens_used,
                "api_formatted": api_formatted,
                "provider_used": provider_id,
                "model_used": model
            }
        )
        
    except Exception as e:
        logger.error(f"API chat processing error: {e}")
        return APIChatResponse(
            success=False,
            error=str(e)
        )

async def collect_chat_messages_api(count: int) -> List[Dict[str, Any]]:
    """Collect recent chat messages via Foundry REST API"""
    try:
        import requests
        
        # Get chat messages from relay server
        # Use a default clientId since we're in memory store mode
        response = requests.get(
            f"http://localhost:3010/chat/messages",
            params={"clientId": "default", "limit": count, "sort": "timestamp", "order": "desc"},
            timeout=10
        )
        
        logger.info(f"DEBUG: Relay server response status: {response.status_code}")
        logger.info(f"DEBUG: Relay server response text: {response.text}")
        
        if response.status_code == 200:
            try:
                messages = response.json()
                logger.info(f"DEBUG: Parsed messages: {messages}")
                # Reverse to get chronological order (oldest first)
                return list(reversed(messages))
            except json.JSONDecodeError as e:
                logger.error(f"DEBUG: Failed to parse JSON: {e}")
                logger.error(f"DEBUG: Raw response: {response.text}")
                return []
        else:
            logger.error(f"Failed to collect chat messages: {response.status_code}")
            logger.error(f"DEBUG: Raw response: {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error collecting chat messages via API: {e}")
        return []
