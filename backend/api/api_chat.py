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

# Create router (prefix added in server.py for consistency)
router = APIRouter(tags=["api_chat"])

# Request models
class APIChatRequest(BaseModel):
    """Request model for API chat endpoint"""
    context_count: Optional[int] = Field(15, description="Number of recent messages to retrieve", ge=1, le=50)
    settings: Optional[Dict[str, Any]] = Field(None, description="Frontend settings including provider info and client ID")
    combat_state: Optional[Dict[str, Any]] = Field(None, description="Combat state from frontend")
    enable_function_calling: Optional[bool] = Field(True, description="Enable AI function calling for this request (default: enabled)")
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

# Import dynamic chat card translation components
try:
    from services.message_services.chat_card_translation_cache import reset_cache, get_current_cache
    from services.message_services.chat_card_translator import get_translator
except ImportError:
    # Fallback for when running outside main application context
    def reset_cache():
        return None
    def get_current_cache():
        return None
    def get_translator():
        return None

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
        else:
            # Fallback to original request data (should not happen with proper middleware)
            context_count = request.context_count
            settings = request.settings
            logger.info("Processing API chat request with original request data")
        
        # Use UniversalSettings as single source of truth - no fallbacks
        # Pass settings dict (not Pydantic model) to extract_universal_settings
        universal_settings = extract_universal_settings(settings, "api_chat")
        logger.info("Using UniversalSettings as single source of truth")
        
        # Extract client ID from validated settings
        client_id = universal_settings.get('relay client id')
        if not client_id:
            logger.error("Client ID is required for message collection")
            return APIChatResponse(
                success=False,
                error="Client ID is required"
            )
        
        # Step 0.5: Reset dynamic cache for new AI turn
        try:
            reset_cache()
        except Exception as e:
            logger.warning(f"Failed to reset dynamic cache: {e}")
        
        # Step 0.5: Handle session management and delta filtering
        from services.system_services.service_factory import get_ai_session_manager, get_message_delta_service
        
        ai_session_manager = get_ai_session_manager()
        message_delta_service = get_message_delta_service()
        
        # Backend manages sessions entirely based on client_id
        force_full_context = universal_settings.get('force_full_context', False)
        
        # Get provider config for session uniqueness
        provider_config = get_provider_config(universal_settings, use_tactical=False)
        provider = provider_config.get('provider')
        model = provider_config.get('model')
        
        # Get or create AI session based on client_id + provider + model
        session_id = ai_session_manager.create_or_get_session(client_id, None, provider, model)
        
        # Force full context if requested
        if force_full_context:
            message_delta_service.force_full_context(session_id)
        
        # Add session ID to universal settings for response delivery
        universal_settings['ai_session_id'] = session_id
        
        # Step1: Collect chat messages via WebSocket
        api_messages = await collect_chat_messages(context_count, client_id)
        
        # Step 1.5: Apply delta filtering to messages
        if not force_full_context:
            # Apply delta filtering to get only new messages since last AI call
            filtered_messages = message_delta_service.apply_message_delta(session_id, api_messages)
            
            # Log delta statistics for debugging
            delta_stats = message_delta_service.get_delta_stats(session_id, api_messages)
            # logger.info(f"Delta filtering: {delta_stats['filtered_count']}/{delta_stats['original_count']} messages ({delta_stats['delta_ratio']:.1%} new)")
            
            # Use filtered messages for processing
            messages_to_process = filtered_messages
        else:
            # Force full context - bypass delta filtering
            message_delta_service.force_full_context(session_id)
            
            # Use all messages for processing
            messages_to_process = api_messages
        
        # Step 2: Convert to compact JSON using unified processor
        compact_messages = unified_processor.process_api_messages(messages_to_process)
        
        # Extract provider config from universal settings
        provider_config = get_provider_config(universal_settings, use_tactical=False)
        
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
        
        # Step 4: Check for combat state from WebSocket message data and add to context
        # Combat state comes from frontend via WebSocket chat_request messages
        combat_state = request.combat_state  # From APIChatRequest model
        
        if combat_state:
            # Update CombatEncounterService with latest combat state
            try:
                from services.system_services.service_factory import get_combat_encounter_service
                combat_service = get_combat_encounter_service()
                update_success = combat_service.update_combat_state(combat_state)
                if update_success:
                    logger.info(f"CombatEncounterService updated with combat state: {combat_state}")
                else:
                    logger.warning(f"Failed to update CombatEncounterService with combat state: {combat_state}")
            except Exception as e:
                logger.error(f"Error updating CombatEncounterService: {e}")
        
        # Step 4.5: Get fresh combat context from CombatEncounterService for AI
        try:
            from services.system_services.service_factory import get_combat_encounter_service
            combat_service = get_combat_encounter_service()
            combat_context = combat_service.get_combat_context()
            
            # Add combat context to messages with fresh data from service
            combat_context_message = {
                'type': 'combat_context',
                'combat_context': combat_context
            }
            
            # Remove any existing combat context messages and add fresh one
            compact_messages = [msg for msg in compact_messages if msg.get('type') != 'combat_context']
            compact_messages.append(combat_context_message)
            
            logger.info(f"Fresh combat context from service: in_combat={combat_context.get('in_combat', False)}")
            
        except Exception as e:
            logger.error(f"Error getting combat context from service: {e}")
        
        # Step 5: Generate enhanced system prompt based on AI role using unified processor
        ai_role = universal_settings.get('ai role', 'gm') if universal_settings else 'gm'
        system_prompt = unified_processor.generate_enhanced_system_prompt(ai_role, compact_messages)
        
        # Step 5.5: For function calling mode, strip chat context from system prompt
        # Function calling mode should only send system prompt + role instructions + combat context
        # AI will use get_message_history tool to retrieve chat context
        disable_function_calling = universal_settings.get('disable function calling', False)
        enable_function_calling = not disable_function_calling
        
        if enable_function_calling:
            # Generate system prompt without chat context messages
            # Only include system prompt + role instructions + combat context
            # AI will use get_message_history tool to retrieve chat messages
            combat_context_messages = [msg for msg in compact_messages if msg.get('type') == 'combat_context']
            system_prompt = unified_processor.generate_enhanced_system_prompt(ai_role, combat_context_messages)
        # Standard mode includes chat context in system prompt (no special handling needed)
        
        # Step 6: Use shared function for AI processing (function calling or standard)
        # This logic is shared with WebSocket handler to avoid duplication
        ai_response_data = await process_with_function_calling_or_standard(
            universal_settings=universal_settings,
            compact_messages=compact_messages,
            system_prompt=system_prompt,
            session_id=session_id,
            client_id=client_id
        )
        
        ai_response = ai_response_data.get("response", "")
        tokens_used = ai_response_data.get("tokens_used", 0)
        thinking = ai_response_data.get("thinking", "")
        
        logger.info(f"AI service returned response of length: {len(ai_response)} characters")
        logger.info(f"Tokens used: {tokens_used}")
        if thinking:
            logger.info(f"AI thinking extracted: {len(thinking)} characters")
        
        # Step 7: Send thinking whisper if available
        if thinking:
            try:
                from services.system_services.service_factory import get_whisper_service, get_websocket_manager
                whisper_service = get_whisper_service()
                ws_manager = get_websocket_manager()
                
                # Create thinking whisper
                whisper = whisper_service.create_thinking_whisper(
                    thinking=thinking,
                    original_prompt=json.dumps(compact_messages, indent=2),
                    metadata={"combat_active": combat_context.get('in_combat', False)}
                )
                
                # Format whisper for Foundry and send via WebSocket
                foundry_whisper = whisper_service.format_whisper_for_foundry(whisper)
                whisper_sent = await ws_manager.send_to_client(client_id, foundry_whisper)
                
                if whisper_sent:
                    logger.info(f"Thinking whisper sent to client {client_id}: {len(thinking)} characters")
                else:
                    logger.warning(f"Failed to send thinking whisper to client {client_id}")
                    
            except Exception as e:
                logger.error(f"Error sending thinking whisper: {e}")
                # Don't fail the entire request if whisper sending fails
        
        # Step 7: Process AI response back to API format and send to Foundry
        api_formatted = unified_processor.process_ai_response(ai_response, compact_messages)
        
        # Step 7.5: Send messages to Foundry via WebSocket (new implementation)
        if api_formatted:
            # Get client ID for WebSocket transmission
            client_id = settings.get('relay client id') if settings else None
            if client_id:
                success_count, total_messages = await _send_messages_to_websocket(api_formatted, client_id)
                
                # Step 8: Return confirmation response (only log success, don't send to frontend)
                metadata = {
                    "context_count": len(compact_messages),
                    "tokens_used": tokens_used,
                    "messages_sent": success_count,
                    "total_messages": total_messages,
                    "api_formatted": api_formatted,
                    "provider_used": provider_id,
                    "model_used": model
                }
                
                # Add thinking to metadata if available
                if thinking:
                    metadata["thinking"] = thinking
                    logger.info(f"AI thinking included in response metadata: {len(thinking)} characters")
                
                return APIChatResponse(
                    success=True,
                    response="",  # Empty response - success message should only be in logs
                    metadata=metadata
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

async def process_with_function_calling_or_standard(
    universal_settings: Dict[str, Any],
    compact_messages: List[Dict],
    system_prompt: str,
    session_id: str,
    client_id: str
) -> Dict[str, Any]:
    """
    Process AI request using either function calling or standard mode based on settings.
    
    This shared function is used by both HTTP API endpoint and WebSocket handler.
    
    Args:
        universal_settings: Settings dictionary containing 'disable function calling' flag
        compact_messages: Compact JSON messages for context
        system_prompt: System prompt for AI
        session_id: AI session ID for conversation history
        client_id: Client ID for WebSocket communication (transient)
        
    Returns:
        Dictionary with AI response data
    """
    # Check if function calling is enabled (disabled only if "disable function calling" setting is true)
    disable_function_calling = universal_settings.get('disable function calling', False)
    enable_function_calling = not disable_function_calling
    
    if enable_function_calling:
        # === FUNCTION CALLING MODE ===
        # logger.info(f"Function calling mode: {len(compact_messages)} compact messages available")
        
        # Get tool definitions
        from services.ai_tools.ai_tool_definitions import get_tool_definitions
        tools = get_tool_definitions()
        
        # Get AI orchestrator from service factory
        from services.system_services.service_factory import get_ai_orchestrator
        ai_orchestrator = get_ai_orchestrator()
        
        # Get provider config from universal settings
        from services.system_services.universal_settings import get_provider_config
        provider_config = get_provider_config(universal_settings, use_tactical=False)
        
        # Build initial messages for function calling loop
        # Function calling mode: Only system prompt (AI will use get_message_history tool)
        # Standard mode: System prompt + chat context
        import json
        
        if enable_function_calling:
            # FUNCTION CALLING MODE: System prompt + simple user instruction
            # AI will use get_message_history tool to retrieve chat messages
            # User message needed to trigger AI response
            
            # Use shared utility for consistent delta injection
            from shared.utils.ai_prompt_builder import build_initial_messages_with_delta
            
            initial_messages = build_initial_messages_with_delta(
                universal_settings=universal_settings,
                system_prompt=system_prompt
            )
            
            # Debug logging: Show complete initial_messages array (everything sent to AI)
            # Decode escape sequences in content strings for better readability
            decoded_messages = _decode_messages_for_display(initial_messages)
            logger.info(f"===== SENDING INITIAL MESSAGES TO AI =====")
            logger.info(f"Complete initial_messages array:\n{json.dumps(decoded_messages, indent=2, ensure_ascii=False)}")
            logger.info(f"===== END SENDING INITIAL MESSAGES =====")
        else:
            # STANDARD MODE: System prompt + chat context
            compact_json_context = json.dumps(compact_messages, indent=2)
            initial_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}"}
            ]
        
        # Execute function calling loop
        # Note: client_id is passed as transient parameter for message collection
        ai_response_data = await ai_orchestrator.execute_function_call_loop(
            initial_messages=initial_messages,
            tools=tools,
            config=provider_config,
            session_id=session_id,
            client_id=client_id,  # Transient parameter from WebSocket
            max_iterations=10  # Safety limit
        )
        
        logger.info(f"AI Orchestrator completed function calling loop: {ai_response_data.get('iterations', 0)} iterations")
        
        # Send ai_turn_complete message to client via WebSocket
        if ai_response_data.get('complete', False):
            try:
                ws_manager = get_websocket_manager()
                completion_message = {
                    "type": "ai_turn_complete",
                    "data": {
                        "success": True,
                        "tokens_used": ai_response_data.get('tokens_used', 0),
                        "iterations": ai_response_data.get('iterations', 0)
                    }
                }
                await ws_manager.send_to_client(client_id, completion_message)
                logger.info(f"Sent ai_turn_complete message to client {client_id}")
            except Exception as e:
                logger.error(f"Error sending ai_turn_complete message: {e}")
        
        return ai_response_data
        
    else:
        # === STANDARD AI SERVICE CALL (LEGACY MODE) ===
        # logger.info(f"Standard mode: {len(compact_messages)} compact messages")
        
        # Get services directly from service factory (no lazy loading needed)
        from services.system_services.service_factory import get_ai_service
        ai_service = get_ai_service()
        
        ai_response_data = await ai_service.process_compact_context(
            processed_messages=compact_messages,
            system_prompt=system_prompt,
            settings=universal_settings,
            session_id=session_id  # Pass session_id for conversation history
        )
        
        return ai_response_data

def _decode_messages_for_display(messages):
    """
    Decode escape sequences in message content strings for better debug readability
    
    Args:
        messages: List of message dictionaries (OpenAI format)
        
    Returns:
        Decoded messages with content strings properly formatted
    """
    decoded_messages = []
    for msg in messages:
        decoded_msg = msg.copy()
        if 'content' in decoded_msg and isinstance(decoded_msg['content'], str):
            # Decode escape sequences
            content = decoded_msg['content']
            content = content.replace('\\n', '\n')
            content = content.replace('\\r', '\r')
            content = content.replace('\\t', '\t')
            content = content.replace('\\"', '"')
            content = content.replace('\\\\', '\\')
            decoded_msg['content'] = content
        decoded_messages.append(decoded_msg)
    return decoded_messages

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
