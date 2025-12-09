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

from services.message_services.api_chat_processor import APIChatProcessor
from services.ai_services.ai_chat_processor import AIChatProcessor
from services.ai_services.ai_service import AIService
from shared.core.processor import ChatContextProcessor
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

# Global instances
api_chat_processor = APIChatProcessor()
ai_chat_processor = AIChatProcessor()
# Use ServiceRegistry to get provider manager and avoid duplication
try:
    from services.system_services.registry import ServiceRegistry
    
    # Try to get key manager from registry
    if ServiceRegistry.is_ready() and ServiceRegistry.is_registered('key_manager'):
        key_manager = ServiceRegistry.get('key_manager')
        provider_manager = key_manager.provider_manager
        logger.info("✅ API Chat: Using provider manager from ServiceRegistry")
    else:
        # Fallback - create new instance
        from services.system_services.provider_manager import ProviderManager
        provider_manager = ProviderManager()
        if ServiceRegistry.is_ready():
            logger.warning("⚠️ API Chat: Provider manager not in registry, created new instance")
        else:
            logger.warning("⚠️ API Chat: ServiceRegistry not ready, created new ProviderManager")
            
except Exception as e:
    # Ultimate fallback - create new instance
    logger.error(f"❌ API Chat: Failed to access ServiceRegistry: {e}")
    from services.system_services.provider_manager import ProviderManager
    provider_manager = ProviderManager()
    logger.info("🔄 API Chat: Created new ProviderManager (exception fallback)")

ai_service = AIService(provider_manager)  # Properly initialized with provider manager

async def _send_messages_to_foundry(api_formatted_data, client_id):
    """Send processed messages to Foundry via relay server"""
    try:
        import requests
        
        # Handle both single message and multi-message formats
        if api_formatted_data.get("type") == "multi-message":
            messages = api_formatted_data.get("messages", [])
        else:
            messages = [api_formatted_data]
        
        # Send each message to relay server
        success_count = 0
        for message in messages:
            try:
                # Check if this is a dice roll message
                if message.get("type") == "dice-roll" and "roll" in message:
                    # Send dice roll via /roll endpoint
                    success = await _send_dice_roll_to_foundry(message, client_id)
                else:
                    # Send regular chat message via /chat endpoint
                    success = await _send_chat_message_to_foundry(message, client_id)
                
                if success:
                    success_count += 1
                
            except Exception as e:
                logger.error(f"Error sending individual message to Foundry: {e}")
        
        return success_count, len(messages)
                
    except Exception as e:
        logger.error(f"Error sending messages to Foundry: {e}")
        return 0, len(messages) if 'messages' in locals() else 0

async def _send_dice_roll_to_foundry(message, client_id):
    """Send dice roll to Foundry via /roll endpoint"""
    try:
        import requests
        
        roll_data = message.get("roll", {})
        
        # Prepare roll data for relay server
        post_data = {
            "formula": roll_data.get("formula", ""),
            "flavor": message.get("content", ""),
            "createChatMessage": True,  # Always create chat message for dice rolls
            "speaker": message.get("author", {}).get("name", "The Gold Box AI")
        }
        
        # DEBUG: Show exactly what data is sent to POST /roll endpoint
        logger.info("=== DATA SENT TO POST /ROLL ENDPOINT ===")
        logger.info(f"POST URL: http://localhost:3010/roll?clientId={client_id}")
        logger.info(f"POST Data: {json.dumps(post_data, indent=2)}")
        logger.info("=== END POST /ROLL DATA ===")
        
        # Retry logic for relay server communication
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"http://localhost:3010/roll?clientId={client_id}",
                    json=post_data,
                    headers={"x-api-key": "local-dev"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully sent dice roll to Foundry: {roll_data.get('formula', 'unknown')}")
                    return True  # Success, exit retry loop
                else:
                    logger.warning(f"Roll attempt {attempt + 1} failed: {response.status_code} - {response.text}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for dice roll")
                        return False
                        
            except Exception as e:
                logger.error(f"Roll attempt {attempt + 1} exception: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All {max_retries} attempts failed for dice roll")
                    return False
        
        return False
                
    except Exception as e:
        logger.error(f"Error sending dice roll to Foundry: {e}")
        return False

async def _send_chat_message_to_foundry(message, client_id):
    """Send chat message to Foundry via /chat endpoint"""
    try:
        import requests
        
        # Use correct relay server format - BOTH nested message object AND flat fields
        post_data = {
            "clientId": client_id,
            "message": {
                "message": message.get("content", "Test message"),
                "speaker": message.get("author", {}).get("name", "The Gold Box AI"),
                "type": message.get("type", "ic"),  # ic = in-character
                "timestamp": int(datetime.now().timestamp() * 1000)  # milliseconds as required
            },
            # Also provide flat fields (required by relay server validation)
            "message.message": message.get("content", "Test message"),
            "message.speaker": message.get("author", {}).get("name", "The Gold Box AI"),
            "message.type": message.get("type", "ic"),  # ic = in-character
            "message.timestamp": int(datetime.now().timestamp() * 1000)  # milliseconds as required
        }
        
        # DEBUG: Show exactly what data is sent to POST /chat endpoint
        logger.info("=== DATA SENT TO POST /CHAT ENDPOINT ===")
        logger.info(f"POST URL: http://localhost:3010/chat")
        logger.info(f"POST Data: {json.dumps(post_data, indent=2)}")
        logger.info("=== END POST /CHAT DATA ===")
        
        # Retry logic for relay server communication
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"http://localhost:3010/chat",
                    json=post_data,
                    headers={"x-api-key": "local-dev"},
                    timeout=30  # Increased timeout to 30 seconds as requested
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully sent chat message to Foundry: {message.get('type', 'unknown')}")
                    return True  # Success, exit retry loop
                else:
                    logger.warning(f"Chat attempt {attempt + 1} failed: {response.status_code} - {response.text}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for chat message")
                        return False
                        
            except Exception as e:
                logger.error(f"Chat attempt {attempt + 1} exception: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All {max_retries} attempts failed for chat message")
                    return False
        
        return False
                
    except Exception as e:
        logger.error(f"Error sending chat message to Foundry: {e}")
        return False

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
        
        # PHASE 1 FIX: Load stored settings FIRST before validation
        try:
            from services.system_services.registry import ServiceRegistry
            if ServiceRegistry.is_ready() and ServiceRegistry.is_registered('settings_manager'):
                settings_manager = ServiceRegistry.get('settings_manager')
                stored_settings = settings_manager.get_settings()
                if stored_settings:
                    # logger.info(f"DEBUG: Loaded {len(stored_settings)} stored settings before validation")
                    # Merge request settings with stored settings (request takes priority for client ID)
                    merged_settings = {**stored_settings}  # Start with all stored settings
                    if settings and isinstance(settings, dict):
                        merged_settings.update(settings)  # Override with request settings (client ID)
                    settings = merged_settings  # Use merged settings for all processing
                    # logger.info(f"DEBUG: Merged settings total count: {len(settings)}")
                else:
                    # logger.warning("DEBUG: No stored settings available for merging")
                    pass
            else:
                logger.warning("Settings manager not available in registry")
        except ImportError as e:
            logger.error(f"Failed to import settings_manager for early merge: {e}")
        
        # PHASE 1 TEST: Verify unified settings object structure (AFTER merge)
        if settings and isinstance(settings, dict):
            required_keys = [
                'maximum message context',
                'chat processing mode', 
                'ai role',
                'general llm provider',
                'general llm model',
                'general llm base url',
                'general llm version',
                'general llm timeout',
                'general llm max retries',
                'general llm custom headers',
                'tactical llm provider',
                'tactical llm base url',
                'tactical llm model',
                'tactical llm version',
                'tactical llm timeout',
                'tactical llm max retries',
                'tactical llm custom headers',
                'backend password'
            ]
            
            missing_keys = [key for key in required_keys if key not in settings]
            extra_keys = [key for key in settings if key not in required_keys]
            
            # logger.info(f"PHASE 1 TEST: Settings structure validation (after merge):")
            # logger.info(f"  Required keys present: {len([k for k in required_keys if k in settings])}/{len(required_keys)}")
            # logger.info(f"  Missing keys: {missing_keys}")
            # logger.info(f"  Extra keys: {extra_keys}")
            
            if len(missing_keys) == 0:
                # logger.info("PHASE 1 TEST: ✅ Settings object structure is correct after merge")
                pass
            else:
                logger.warning(f"PHASE 1 TEST: ⚠️ Settings structure issues detected after merge")
        
        # Initialize universal_settings with defaults to avoid scope issues
        universal_settings = extract_universal_settings({}, "api_chat")
        # logger.info(f"DEBUG: Initialized universal_settings with defaults: {universal_settings}")
        
        # Step 1: Collect chat messages via REST API (relay server is started by main server)
        logger.info(f"Collecting {context_count} chat messages via REST API")
        
        # Prepare request data for client ID extraction (PHASE 1 FIX: Always ensure valid dictionary)
        if hasattr(http_request.state, 'validated_body') and http_request.state.validated_body:
            request_data_for_api = http_request.state.validated_body
            # logger.info("DEBUG: Using middleware-validated request data for API calls")
        else:
            # If no middleware validation, use the original request data (PHASE 1 FIX: Ensure valid structure)
            request_data_for_api = {
                'context_count': request.context_count,
                'settings': request.settings if request.settings is not None else {}
            }
            # logger.info("DEBUG: Using original request data for API calls")
        
        # PHASE 1 FIX: Ensure request_data_for_api is never None
        if request_data_for_api is None:
            request_data_for_api = {'context_count': context_count, 'settings': {}}
            # logger.warning("DEBUG: request_data_for_api was None, using fallback structure")
        
        api_messages = await collect_chat_messages_api(context_count, request_data_for_api)
        
        # Step 2: Convert to compact JSON
        compact_messages = api_chat_processor.process_api_messages(api_messages)
        
        # Step 3: Use universal settings extraction for consistent behavior
        # First try to use settings from request, then fall back to stored settings
        if settings and isinstance(settings, dict):
            # MERGE FIX: If settings contains client ID, merge with stored settings for complete config
            if 'relay client id' in settings:
                # Client ID provided - merge with stored settings for complete configuration
                try:
                    from server import settings_manager
                    stored_settings = settings_manager.get_settings()
                    if stored_settings:
                        # Merge request settings with stored settings (request takes priority for client ID)
                        merged_settings = {**stored_settings}  # Start with all stored settings
                        merged_settings.update(settings)  # Override with request settings (client ID)
                        request_data_for_settings = {
                            'settings': merged_settings
                        }
                        universal_settings = extract_universal_settings(request_data_for_settings, "api_chat")
                        # logger.info(f"DEBUG: Merged settings - Stored: {len(stored_settings)}, Request: {len(settings)}, Final: {len(merged_settings)}")
                except ImportError as e:
                    logger.error(f"Failed to import settings_manager for merge: {e}")
                    # Fallback to request settings only
                    request_data_for_settings = {
                        'settings': settings
                    }
                    universal_settings = extract_universal_settings(request_data_for_settings, "api_chat")
                    # logger.info(f"DEBUG: Using request settings only (no stored settings available): {universal_settings}")
            else:
                # No client ID - use request settings as-is
                request_data_for_settings = {
                    'settings': settings
                }
                universal_settings = extract_universal_settings(request_data_for_settings, "api_chat")
                # logger.info(f"DEBUG: Using request settings only (no client ID): {universal_settings}")
        else:
            # Use stored settings from settings manager (fallback)
            try:
                from server import settings_manager
                stored_settings = settings_manager.get_settings()
            except ImportError as e:
                logger.error(f"Failed to import settings_manager: {e}")
                stored_settings = {}
            # logger.info(f"DEBUG: Retrieved stored settings: {stored_settings}")
            if stored_settings:
                request_data_for_settings = {
                    'settings': stored_settings
                }
                universal_settings = extract_universal_settings(request_data_for_settings, "api_chat")
                # logger.info(f"DEBUG: Universal settings extracted from storage: {universal_settings}")
            else:
                # Final fallback to defaults
                # logger.warning("DEBUG: No stored settings found, using defaults")
                universal_settings = extract_universal_settings({}, "api_chat")
                # logger.info(f"DEBUG: Universal settings extracted from defaults: {universal_settings}")
        
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
        
        # DEBUG: Show exactly what we're sending to AI
        # logger.info("=== CHAT CONTEXT DEBUG ===")
        # logger.info(f"Raw messages count from API: {len(api_messages)}")
        # logger.info(f"Compact messages count after processing: {len(compact_messages)}")
        # logger.info(f"Sample compact messages: {compact_messages[:3] if compact_messages else 'None'}")
        # logger.info(f"Full JSON context being sent to AI:\n{compact_json_context}")
        # logger.info("=== END CHAT CONTEXT DEBUG ===")
        
        # Step 5: Prepare enhanced AI messages with role-based prompts (from legacy context chat)
        ai_role = universal_settings.get('ai role', 'gm') if universal_settings else 'gm'
        
        # Generate enhanced system prompt based on AI role (from legacy context chat)
        system_prompt = _generate_enhanced_system_prompt(ai_role, compact_messages)
        
        ai_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\nPlease respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use compact JSON format specified in system prompt."}
        ]
        
        # DEBUG: Show the final AI messages
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
        api_formatted = ai_chat_processor.process_ai_response(ai_response, compact_messages)
        
        # Step 7.5: Send messages to Foundry via WebSocket (new implementation)
        if api_formatted:
            # Get client ID for WebSocket transmission
            client_id = settings.get('relay client id') if settings else None
            if client_id:
                success_count, total_messages = await _send_messages_to_websocket(api_formatted, client_id)
                logger.info(f"WebSocket transmission: {success_count}/{total_messages} messages sent successfully")
                
                # Step 8: Return confirmation response (only log success, don't send to frontend)
                logger.info(f"✅ Successfully sent {success_count} message(s) to Foundry chat")
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
                logger.warning("No client ID available - cannot send messages to Foundry")
                # Return response with API formatted data for frontend display
                return APIChatResponse(
                    success=True,
                    response=ai_response,  # Return raw AI response as fallback
                    metadata={
                        "context_count": len(compact_messages),
                        "tokens_used": tokens_used,
                        "messages_sent": 0,
                        "websocket_error": "No client ID available",
                        "api_formatted": api_formatted,
                        "provider_used": provider_id,
                        "model_used": model
                    }
                )
        else:
            logger.error("Failed to process AI response to API format")
            return APIChatResponse(
                success=False,
                error="Failed to process AI response for relay transmission"
            )
        
    except Exception as e:
        logger.error(f"API chat processing error: {e}")
        return APIChatResponse(
            success=False,
            error=str(e)
        )

def _generate_enhanced_system_prompt(ai_role: str, compact_messages: List[Dict[str, Any]]) -> str:
    """
    Generate enhanced system prompt based on AI role (from legacy context chat)
    
    Args:
        ai_role: AI role ('gm', 'gm assistant', 'player')
        compact_messages: List of compact messages for context
        
    Returns:
        Enhanced system prompt string
    """
    # Build context codes and abbreviations from compact messages
    context_codes = []
    context_abbreviations = []
    context_schemas = []
    
    # Analyze compact messages to determine available context
    has_rolls = any(msg.get('t') == 'dr' for msg in compact_messages)
    has_chat = any(msg.get('t') == 'cm' for msg in compact_messages)
    has_cards = any(msg.get('t') == 'cd' for msg in compact_messages)
    
    # Add context codes based on available data
    if has_chat:
        context_codes.append('cm: chat_message')
        context_abbreviations.append('cm: chat messages')
        context_schemas.append('cm: {"t": "cm", "s": "speaker", "c": "content"}')
    
    if has_rolls:
        context_codes.append('dr: dice_roll')
        context_abbreviations.extend(['dr: dice rolls', 'f: formula', 'r: results', 'tt: total'])
        context_schemas.append('dr: {"t": "dr", "ft": "flavor_text", "f": "formula", "r": "results", "tt": "total"}')
    
    if has_cards:
        context_codes.append('cd: card')
        context_abbreviations.extend(['cd: cards', 'tt: title', 'st: subtitle', 'btn: buttons'])
        context_schemas.append('cd: {"t": "cd", "tt": "title", "st": "subtitle", "btn": "buttons"}')
    
    # Get AI role specific prompt content (from legacy context chat)
    role_prompts = {
        'gm': 'You are assigned as a full gamemaster. Your role is to describe the scene, describe NPC actions, and create dice rolls whenever NPCs do anything that requires one. Keep generating descriptions, actions, and dice rolls until every NPC in the scene has gone, and then turn the action back over to players.',
        'gm assistant': 'You are assigned as a GM\'s assistant. Your role is to aid the GM in whatever task they are currently doing, which they will usually prompt for you in the most recent message.',
        'player': 'You are assigned as a Player. Your role is to participate in the story via in-character chat and actions. Describe what your character is doing and roll dice as appropriate for your actions.'
    }
    
    role_specific_prompt = role_prompts.get(ai_role.lower(), role_prompts['gm'])
    
    # Build enhanced system prompt
    system_prompt = f"""You are an AI assistant for tabletop RPG games, with the role {ai_role}. {role_specific_prompt}

Data from chat and environment is formatted as follows:

Type Codes:
{', '.join(context_codes) if context_codes else 'No specific type codes detected'}

Field Abbreviations:
{', '.join(context_abbreviations) if context_abbreviations else 'No specific abbreviations detected'}

Message Schemas:
{'; '.join(context_schemas) if context_schemas else 'No specific schemas detected'}

Type Codes:
- dr: dice_roll
- cm: chat_message
- cd: chat_card

Field Abbreviations:
- t: message type (dr, cm, cd)
- f: formula (dice roll formula)
- r: results (individual dice results array)
- tt: total (roll total result)
- s: speaker (character name who sent message)
- c: content (message text content)
- ft: flavor_text (roll context like "Intelligence (Investigation) Check")
- n: name (item/spell/condition name)
- d: description (card description text)
- a: actions (button actions array)

Message Schemas:
- Dice Roll: {{"t": "dr", "ft": "flavor_text", "f": "formula", "r": [results], "tt": total}}
- Chat Message: {{"t": "cm", "s": "speaker", "c": "content"}}
- Chat Card: {{"t": "cd", "n": "name", "d": "description", "a": ["actions"]}}"""
    
    return system_prompt

async def _send_messages_to_websocket(api_formatted_data, client_id):
    """Send processed messages to Foundry via WebSocket (new implementation)"""
    try:
        # Use ServiceRegistry to get WebSocket connection manager
        from services.system_services.registry import ServiceRegistry
        
        # Handle both single message and multi-message formats
        if api_formatted_data.get("type") == "multi-message":
            messages = api_formatted_data.get("messages", [])
        else:
            messages = [api_formatted_data]
        
        # Get WebSocket connection manager from ServiceRegistry
        if not ServiceRegistry.is_ready() or not ServiceRegistry.is_registered('websocket_manager'):
            logger.error("WebSocket manager not available in ServiceRegistry")
            return 0, len(messages)
        
        ws_manager = ServiceRegistry.get('websocket_manager')
        
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
                    logger.info(f"Successfully sent {message.get('type', 'unknown')} to WebSocket client {client_id}")
                else:
                    logger.warning(f"Failed to send {message.get('type', 'unknown')} to WebSocket client {client_id}")
                
            except Exception as e:
                logger.error(f"Error sending individual message to WebSocket client: {e}")
        
        return success_count, len(messages)
                
    except Exception as e:
        logger.error(f"Error sending messages to WebSocket client: {e}")
        return 0, len(messages) if 'messages' in locals() else 0

async def collect_chat_messages_api(count: int, request_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Collect recent chat messages and dice rolls via WebSocket message collector"""
    try:
        # Get client ID from unified settings with better fallback handling
        client_id = None
        if request_data:
            # Priority 1: Get from unified settings in request
            settings = request_data.get('settings', {})
            client_id = settings.get('relay client id')
            if client_id:
                logger.info(f"Client ID found in unified settings: {client_id}")
                pass
            else:
                # Priority 2: Try to get from stored settings as fallback
                try:
                    from server import settings_manager
                    stored_settings = settings_manager.get_settings()
                    if stored_settings:
                        client_id = stored_settings.get('relay client id')
                        if client_id:
                            logger.info(f"Client ID found in stored settings (fallback): {client_id}")
                            pass
                except ImportError:
                    pass
                
                if not client_id:
                    # Priority 3: Fallback to separate parameter (backward compatibility)
                    client_id = request_data.get('relayClientId')
                    if client_id:
                        logger.info(f"Client ID found in separate parameter (backward compatibility): {client_id}")
                        pass
        else:
            # Try to get from stored settings when no request data
                try:
                    from services.system_services.registry import ServiceRegistry
                    if ServiceRegistry.is_ready() and ServiceRegistry.is_registered('settings_manager'):
                        settings_manager = ServiceRegistry.get('settings_manager')
                        stored_settings = settings_manager.get_settings()
                        if stored_settings:
                            client_id = stored_settings.get('relay client id')
                            if client_id:
                                logger.info(f"Client ID found in stored settings (no request data): {client_id}")
                                pass
                    else:
                        logger.warning("Settings manager not available in registry")
                except ImportError:
                    pass
        
        # If no client ID, return empty list
        if not client_id:
            logger.warning("No client ID available for message collection")
            return []
        
        logger.info(f"Collecting {count} messages for client {client_id} via WebSocket message collector")
        
        # Import message collector
        from services.message_services.message_collector import get_combined_client_messages
        
        # Small delay to allow any recent messages to be processed
        await asyncio.sleep(0.1)
        
        # Get combined messages and rolls from WebSocket message collector
        merged_messages = get_combined_client_messages(client_id, count)
        
        logger.info(f"Collected {len(merged_messages)} messages via WebSocket for client {client_id}")
        
        # Log message sources for debugging
        if merged_messages:
            sources = [msg.get('_source') for msg in merged_messages[:5]]
            logger.debug(f"Message sources: {sources}")
        
        return merged_messages
            
    except Exception as e:
        logger.error(f"Error collecting messages via WebSocket: {e}")
        return []
