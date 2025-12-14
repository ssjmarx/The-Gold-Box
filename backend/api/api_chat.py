"""
API Chat Endpoint for The Gold Box v0.3.0
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

from shared.core.unified_message_processor import get_unified_processor
from services.system_services.universal_settings import extract_universal_settings, get_provider_config

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["api_chat"])

# Request models
class APIChatRequest(BaseModel):
    """Request model for API chat endpoint"""
    context_count: Optional[int] = Field(15, description="Number of recent messages to retrieve", ge=1, le=50)
    settings: Optional[Dict[str, Any]] = Field(None, description="Frontend settings including provider info and client ID")
    # Removed: relayClientId - now included in unified settings (Phase 2 fix)

class APIChatResponse(BaseModel):
    """Response model for API chat endpoint"""
    success: bool = Field(..., description="Whether request was successful")
    response: Optional[str] = Field(None, description="AI response as formatted text")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if failed")

# Global instance - unified processor replaces redundant processors
unified_processor = get_unified_processor()

# Import service factory functions for consistent access patterns
from services.system_services.service_factory import (
    get_provider_manager, get_ai_service, get_websocket_manager, get_message_collector
)

# Relay server functions removed - now using WebSocket-only communication

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
            # logger.info(f"DEBUG: Request body from middleware: {validated_request}")
        else:
            # Fallback to original request data (should not happen with proper middleware)
            context_count = request.context_count
            settings = request.settings
            logger.info("Processing API chat request with original request data")
        
        # logger.info(f"DEBUG: Request data received: {request}")
        # logger.info(f"DEBUG: Extracted context_count: {context_count}")
        # logger.info(f"DEBUG: Extracted settings: {settings}")
        # logger.info(f"DEBUG: Settings keys: {list(settings.keys()) if settings else 'None'}")
        
        # Use UniversalSettings as single source of truth - no fallbacks
        universal_settings = extract_universal_settings(request, "api_chat")
        logger.info("Using UniversalSettings as single source of truth")
        
        # Extract client ID from validated settings
        client_id = universal_settings.get('relay client id')
        if not client_id:
            logger.error("Client ID is required for message collection")
            return APIChatResponse(
                success=False,
                error="Client ID is required"
            )
        
        # Step 1: Collect chat messages via WebSocket
        logger.info(f"Collecting {context_count} chat messages via WebSocket for client {client_id}")
        api_messages = await collect_chat_messages(context_count, client_id)
        
        # Step 2: Convert to compact JSON using unified processor
        compact_messages = unified_processor.process_api_messages(api_messages)
        
        # Extract provider config from universal settings
        provider_config = get_provider_config(universal_settings, use_tactical=False)
        # logger.info(f"DEBUG: Provider config extracted: {provider_config}")
        
        # Use provider config values for consistency
        provider_id = provider_config['provider']
        model = provider_config['model']
        base_url = provider_config['base_url']
        api_version = provider_config['api_version']
        timeout = provider_config['timeout']
        max_retries = provider_config['max_retries']
        custom_headers_str = provider_config.get('custom_headers', '{}')
        
        # Parse custom headers if provided - fail fast on invalid JSON
        if custom_headers_str and custom_headers_str.strip():
            try:
                custom_headers = json.loads(custom_headers_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid custom headers JSON: {e}")
        else:
            custom_headers = {}
        
        client_host = http_request.client.host if http_request.client else "unknown"
        logger.info(f"Processing API chat request from {client_host}: provider={provider_id}, model={model}")
        logger.info(f"Settings: base_url={base_url}, api_version={api_version}, timeout={timeout}, max_retries={max_retries}")
        
        # Step 4: Convert compact messages to JSON string for AI
        compact_json_context = json.dumps(compact_messages, indent=2)
        
        # DEBUG: Show exactly what we're sending to AI
        # logger.info("=== CHAT CONTEXT DEBUG ===")
        # logger.info(f"Raw messages count from API: {len(api_messages)}")
        # logger.info(f"Compact messages count after processing: {len(compact_messages)}")
        # logger.info(f"Sample compact messages: {compact_messages[:3] if compact_messages else 'None'}")
        # logger.info(f"Full JSON context being sent to AI:\n{compact_json_context}")
        # logger.info("=== END CHAT CONTEXT DEBUG ===")
        
        # Step 5: Prepare enhanced AI messages with role-based prompts (from legacy context chat)
        ai_role = universal_settings.get('ai role', 'gm') if universal_settings else 'gm'
        
        # Generate enhanced system prompt based on AI role using unified processor
        system_prompt = unified_processor.generate_enhanced_system_prompt(ai_role, compact_messages)
        
        ai_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\nPlease respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use compact JSON format specified in system prompt."}
        ]
        
        # DEBUG: Show final AI messages
        # logger.info("=== AI MESSAGES DEBUG ===")
        # logger.info(f"System prompt length: {len(system_prompt)} characters")
        # logger.info(f"User message length: {len(ai_messages[1]['content'])} characters")
        # logger.info(f"Total AI messages: {len(ai_messages)}")
        # logger.info("=== END AI MESSAGES DEBUG ===")
        
        # Step 6: Call AI service with universal settings
        logger.info("=== AI SERVICE CALL DEBUG ===")
        logger.info(f"Calling AI service with {len(compact_messages)} compact messages")
        logger.info(f"Settings being passed to AI service: {universal_settings}")
        
        # DEBUG: Print entire prompt sent to AI service
        logger.info("=== ENTIRE PROMPT SENT TO AI ===")
        logger.info(f"SYSTEM PROMPT:\n{system_prompt}")
        logger.info(f"USER CONTEXT:\n{compact_json_context}")
        logger.info("=== END ENTIRE PROMPT ===")
        
        # Get services directly from service factory (no lazy loading needed)
        ai_service = get_ai_service()
        
        ai_response_data = await ai_service.process_compact_context(
            processed_messages=compact_messages,
            system_prompt=system_prompt,
            settings=universal_settings
        )
        
        ai_response = ai_response_data.get("response", "")
        tokens_used = ai_response_data.get("tokens_used", 0)
        logger.info(f"AI service returned response of length: {len(ai_response)} characters")
        logger.info(f"Tokens used: {tokens_used}")
        
        # DEBUG: Show exactly what the AI returned before processing
        logger.info("=== RAW AI RESPONSE BEFORE PROCESSING ===")
        logger.info(f"Raw AI Response: {ai_response}")
        logger.info("=== END RAW AI RESPONSE ===")
        # logger.info("=== END AI SERVICE CALL DEBUG ===")
        
        # Step 7: Process AI response back to API format and send to Foundry
        api_formatted = unified_processor.process_ai_response(ai_response, compact_messages)
        
        # Step 7.5: Send messages to Foundry via WebSocket (new implementation)
        if api_formatted:
            # Get client ID for WebSocket transmission
            client_id = settings.get('relay client id') if settings else None
            if client_id:
                success_count, total_messages = await _send_messages_to_websocket(api_formatted, client_id)
                # Step 8: Return confirmation response (only log success, don't send to frontend)
                return APIChatResponse(
                    success=True,
                    response="",  # Empty response - success message should only be in logs
                    metadata={
                        "context_count": len(compact_messages),
                        "tokens_used": tokens_used,
                        "messages_sent": success_count,
                        "total_messages": total_messages,
                        "api_formatted": api_formatted,
                        "provider_used": provider_id,
                        "model_used": model
                    }
                )
            else:
                logger.error("No client ID available - cannot send messages to Foundry")
                raise ValueError("Client ID is required to send messages to Foundry WebSocket")
        else:
            logger.error("Failed to process AI response to API format")
            return APIChatResponse(
                success=False,
                error="Failed to process AI response for relay transmission"
            )
        
    except ValueError as e:
        logger.error(f"API chat validation error: {e}")
        return APIChatResponse(
            success=False,
            error=str(e)
        )
    except json.JSONDecodeError as e:
        logger.error(f"API chat JSON parsing error: {e}")
        return APIChatResponse(
            success=False,
            error=f"Invalid JSON format: {e}"
        )
    except Exception as e:
        logger.error(f"API chat processing error: {e}")
        return APIChatResponse(
            success=False,
            error=f"Internal server error: {str(e)}"
        )

async def _send_messages_to_websocket(api_formatted_data, client_id):
    """Send processed messages to Foundry via WebSocket (new implementation)"""
    # Handle both single message and multi-message formats
    if api_formatted_data.get("type") == "multi-message":
        messages = api_formatted_data.get("messages", [])
    else:
        messages = [api_formatted_data]
    
    # Get WebSocket connection manager from service factory
    ws_manager = get_websocket_manager()
    
    # Send each message to WebSocket client
    success_count = 0
    for message in messages:
        try:
            # Format message for WebSocket client (frontend expects 'chat_response' type)
            ws_message = {
                "type": "chat_response",
                "data": {
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            # Send to WebSocket client using FastAPI connection manager
            success = await ws_manager.send_to_client(client_id, ws_message)
            if success:
                success_count += 1
                # Successfully sent message to WebSocket client
            else:
                logger.warning(f"Failed to send {message.get('type', 'unknown')} to WebSocket client {client_id}")
            
        except Exception as e:
            logger.error(f"Error sending individual message to WebSocket client: {e}")
            # Continue with other messages instead of failing entirely
    
    return success_count, len(messages)

async def collect_chat_messages(count: int, client_id: str) -> List[Dict[str, Any]]:
    """Collect recent chat messages and dice rolls via WebSocket message collector"""
    if not client_id:
        logger.error("Client ID is required for message collection")
        raise ValueError("Client ID is required")
    
    logger.info(f"Collecting {count} messages for client {client_id} via WebSocket message collector")
    
    # Small delay to allow any recent messages to be processed
    await asyncio.sleep(0.1)
    
    # Get combined messages and rolls from WebSocket message collector
    message_collector = get_message_collector()
    merged_messages = message_collector.get_combined_messages(client_id, count)
    
    logger.info(f"Collected {len(merged_messages)} messages via WebSocket for client {client_id}")
    
    # Log message sources for debugging
    if merged_messages:
        sources = [msg.get('_source') for msg in merged_messages[:5]]
        logger.debug(f"Message sources: {sources}")
    
    return merged_messages
