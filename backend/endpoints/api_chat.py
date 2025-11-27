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
from server.universal_settings import extract_universal_settings, get_provider_config

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
from server.provider_manager import ProviderManager
provider_manager = ProviderManager()
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
                # Use the correct relay server format - BOTH nested message object AND flat fields
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
                            success_count += 1
                            logger.info(f"Successfully sent message to Foundry: {message.get('type', 'unknown')}")
                            break  # Success, exit retry loop
                        else:
                            logger.warning(f"Attempt {attempt + 1} failed: {response.status_code} - {response.text}")
                            if attempt < max_retries - 1:
                                logger.info(f"Retrying in {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                logger.error(f"All {max_retries} attempts failed for message")
                                break
                                
                    except Exception as e:
                        logger.error(f"Attempt {attempt + 1} exception: {e}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"All {max_retries} attempts failed for message")
                            break
                
            except Exception as e:
                logger.error(f"Error sending individual message to Foundry: {e}")
        
        return success_count, len(messages)
                
    except Exception as e:
        logger.error(f"Error sending messages to Foundry: {e}")
        return 0, len(messages) if 'messages' in locals() else 0

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
        
        logger.info(f"DEBUG: Request data received: {request}")
        logger.info(f"DEBUG: Extracted context_count: {context_count}")
        logger.info(f"DEBUG: Extracted settings: {settings}")
        logger.info(f"DEBUG: Settings keys: {list(settings.keys()) if settings else 'None'}")
        
        # PHASE 1 FIX: Load stored settings FIRST before validation
        try:
            from server import settings_manager
            stored_settings = settings_manager.get_settings()
            if stored_settings:
                logger.info(f"DEBUG: Loaded {len(stored_settings)} stored settings before validation")
                # Merge request settings with stored settings (request takes priority for client ID)
                merged_settings = {**stored_settings}  # Start with all stored settings
                if settings and isinstance(settings, dict):
                    merged_settings.update(settings)  # Override with request settings (client ID)
                settings = merged_settings  # Use merged settings for all processing
                logger.info(f"DEBUG: Merged settings total count: {len(settings)}")
            else:
                logger.warning("DEBUG: No stored settings available for merging")
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
            
            logger.info(f"PHASE 1 TEST: Settings structure validation (after merge):")
            logger.info(f"  Required keys present: {len([k for k in required_keys if k in settings])}/{len(required_keys)}")
            logger.info(f"  Missing keys: {missing_keys}")
            logger.info(f"  Extra keys: {extra_keys}")
            
            if len(missing_keys) == 0:
                logger.info("PHASE 1 TEST: ✅ Settings object structure is correct after merge")
            else:
                logger.warning(f"PHASE 1 TEST: ⚠️ Settings structure issues detected after merge")
        
        # Initialize universal_settings with defaults to avoid scope issues
        universal_settings = extract_universal_settings({}, "api_chat")
        logger.info(f"DEBUG: Initialized universal_settings with defaults: {universal_settings}")
        
        # Step 1: Collect chat messages via REST API (relay server is started by main server)
        logger.info(f"Collecting {context_count} chat messages via REST API")
        
        # Prepare request data for client ID extraction (PHASE 1 FIX: Always ensure valid dictionary)
        if hasattr(http_request.state, 'validated_body') and http_request.state.validated_body:
            request_data_for_api = http_request.state.validated_body
            logger.info("DEBUG: Using middleware-validated request data for API calls")
        else:
            # If no middleware validation, use the original request data (PHASE 1 FIX: Ensure valid structure)
            request_data_for_api = {
                'context_count': request.context_count,
                'settings': request.settings if request.settings is not None else {}
            }
            logger.info("DEBUG: Using original request data for API calls")
        
        # PHASE 1 FIX: Ensure request_data_for_api is never None
        if request_data_for_api is None:
            request_data_for_api = {'context_count': context_count, 'settings': {}}
            logger.warning("DEBUG: request_data_for_api was None, using fallback structure")
        
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
                        logger.info(f"DEBUG: Merged settings - Stored: {len(stored_settings)}, Request: {len(settings)}, Final: {len(merged_settings)}")
                except ImportError as e:
                    logger.error(f"Failed to import settings_manager for merge: {e}")
                    # Fallback to request settings only
                    request_data_for_settings = {
                        'settings': settings
                    }
                    universal_settings = extract_universal_settings(request_data_for_settings, "api_chat")
                    logger.info(f"DEBUG: Using request settings only (no stored settings available): {universal_settings}")
            else:
                # No client ID - use request settings as-is
                request_data_for_settings = {
                    'settings': settings
                }
                universal_settings = extract_universal_settings(request_data_for_settings, "api_chat")
                logger.info(f"DEBUG: Using request settings only (no client ID): {universal_settings}")
        else:
            # Use stored settings from settings manager (fallback)
            try:
                from server import settings_manager
                stored_settings = settings_manager.get_settings()
            except ImportError as e:
                logger.error(f"Failed to import settings_manager: {e}")
                stored_settings = {}
            logger.info(f"DEBUG: Retrieved stored settings: {stored_settings}")
            if stored_settings:
                request_data_for_settings = {
                    'settings': stored_settings
                }
                universal_settings = extract_universal_settings(request_data_for_settings, "api_chat")
                logger.info(f"DEBUG: Universal settings extracted from storage: {universal_settings}")
            else:
                # Final fallback to defaults
                logger.warning("DEBUG: No stored settings found, using defaults")
                universal_settings = extract_universal_settings({}, "api_chat")
                logger.info(f"DEBUG: Universal settings extracted from defaults: {universal_settings}")
        
        # Extract provider config from universal settings
        provider_config = get_provider_config(universal_settings, use_tactical=False)
        logger.info(f"DEBUG: Provider config extracted: {provider_config}")
        
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
        
        # DEBUG: Show exactly what we're sending to the AI
        logger.info("=== CHAT CONTEXT DEBUG ===")
        logger.info(f"Raw messages count from API: {len(api_messages)}")
        logger.info(f"Compact messages count after processing: {len(compact_messages)}")
        logger.info(f"Sample compact messages: {compact_messages[:3] if compact_messages else 'None'}")
        logger.info(f"Full JSON context being sent to AI:\n{compact_json_context}")
        logger.info("=== END CHAT CONTEXT DEBUG ===")
        
        # Step 5: Prepare AI messages
        processor = ChatContextProcessor()
        system_prompt = processor.generate_system_prompt()
        
        ai_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\nPlease respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use compact JSON format specified in system prompt."}
        ]
        
        # DEBUG: Show the final AI messages
        logger.info("=== AI MESSAGES DEBUG ===")
        logger.info(f"System prompt length: {len(system_prompt)} characters")
        logger.info(f"User message length: {len(ai_messages[1]['content'])} characters")
        logger.info(f"Total AI messages: {len(ai_messages)}")
        logger.info("=== END AI MESSAGES DEBUG ===")
        
        # Step 6: Call AI service with universal settings
        logger.info("=== AI SERVICE CALL DEBUG ===")
        logger.info(f"Calling AI service with {len(compact_messages)} compact messages")
        logger.info(f"Settings being passed to AI service: {universal_settings}")
        ai_response_data = await ai_service.process_compact_context(
            processed_messages=compact_messages,
            system_prompt=system_prompt,
            settings=universal_settings
        )
        
        ai_response = ai_response_data.get("response", "")
        tokens_used = ai_response_data.get("tokens_used", 0)
        logger.info(f"AI service returned response of length: {len(ai_response)} characters")
        logger.info(f"Tokens used: {tokens_used}")
        logger.info("=== END AI SERVICE CALL DEBUG ===")
        
        # Step 7: Process AI response back to API format and send to Foundry
        api_formatted = ai_chat_processor.process_ai_response(ai_response, compact_messages)
        
        # Step 7.5: Send messages to Foundry via relay server
        if api_formatted:
            # Get client ID for relay server
            client_id = settings.get('relay client id') if settings else None
            if client_id:
                success_count, total_messages = await _send_messages_to_foundry(api_formatted, client_id)
                logger.info(f"Relay server transmission: {success_count}/{total_messages} messages sent successfully")
                
                # Step 8: Return confirmation response
                return APIChatResponse(
                    success=True,
                    response=f"✅ Successfully sent {success_count} message(s) to Foundry chat",
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
                        "relay_error": "No client ID available",
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

async def collect_chat_messages_api(count: int, request_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Collect recent chat messages and dice rolls via Foundry REST API"""
    try:
        import requests
        
        # Get client ID from unified settings with better fallback handling (Phase 2 fix)
        client_id = None
        if request_data:
            # Priority 1: Get from unified settings in request
            settings = request_data.get('settings', {})
            client_id = settings.get('relay client id')
            if client_id:
                logger.info("DEBUG: Client ID found in unified settings")
            else:
                # Priority 2: Try to get from stored settings as fallback
                try:
                    from server import settings_manager
                    stored_settings = settings_manager.get_settings()
                    if stored_settings:
                        client_id = stored_settings.get('relay client id')
                        if client_id:
                            logger.info("DEBUG: Client ID found in stored settings (fallback)")
                except ImportError:
                    pass
                
                if not client_id:
                    # Priority 3: Fallback to separate parameter (backward compatibility)
                    client_id = request_data.get('relayClientId')
                    if client_id:
                        logger.info("DEBUG: Client ID found in separate parameter (backward compatibility)")
        else:
            # Try to get from stored settings when no request data
            try:
                from server import settings_manager
                stored_settings = settings_manager.get_settings()
                if stored_settings:
                    client_id = stored_settings.get('relay client id')
                    if client_id:
                        logger.info("DEBUG: Client ID found in stored settings (no request data)")
            except ImportError:
                pass
        
        # If no client ID provided, try to get one from relay server
        if not client_id:
            logger.info("DEBUG: No client ID provided, attempting to get available clients from relay server")
            try:
                # Try to get list of available clients from relay server (PHASE 2 FIX: Correct endpoint)
                clients_response = requests.get(
                    f"http://localhost:3010/clients",
                    timeout=5
                )
                if clients_response.status_code == 200:
                    clients = clients_response.json()
                    if clients and len(clients) > 0:
                        # Use the first available client
                        client_id = clients[0].get('id')
                        logger.info(f"DEBUG: Using first available client: {client_id}")
                    else:
                        logger.warning("DEBUG: No clients available on relay server")
                else:
                    logger.warning(f"DEBUG: Failed to get clients list: {clients_response.status_code}")
            except Exception as e:
                logger.warning(f"DEBUG: Error getting clients list: {e}")
        
        # If still no client ID, try some common defaults or generate a test one
        if not client_id:
            logger.warning("DEBUG: Still no client ID, trying fallback approaches")
            # Try some common client IDs that might be registered
            fallback_ids = ["foundry-test", "test-client", "default-client"]
            for fallback_id in fallback_ids:
                try:
                    test_response = requests.get(
                        f"http://localhost:3010/chat/messages",
                        params={"clientId": fallback_id, "limit": 1},
                        timeout=3
                    )
                    if test_response.status_code == 200:
                        client_id = fallback_id
                        logger.info(f"DEBUG: Found working fallback client ID: {client_id}")
                        break
                except:
                    continue
            
            # If all fallbacks fail, use a generated ID but expect it to fail
            if not client_id:
                client_id = "generated-test-client"
                logger.warning(f"DEBUG: Using generated client ID (may fail): {client_id}")
        
        logger.info(f"DEBUG: Using client ID for relay server request: {client_id}")
        
        # Get chat messages from relay server with proper authentication
        headers = {}
        # In development mode, we can use a local dev key or bypass auth
        # The relay server uses memory store in local dev which bypasses auth
        headers["x-api-key"] = "local-dev"  # This works for local memory store mode
        
        # TIMING FIX: Small delay to allow Foundry module to store messages
        # The createChatMessage hook in Foundry module runs AFTER message creation
        await asyncio.sleep(0.5)  # 500ms delay for message storage
        
        # Collect both chat messages AND rolls for complete context
        chat_messages = []
        roll_messages = []
        
        # Step1: Get chat messages (always force fresh data)
        chat_response = requests.get(
            f"http://localhost:3010/messages",  # PHASE 3 FIX: Use correct Gold API endpoint
            params={"clientId": client_id, "limit": count, "sort": "timestamp", "order": "desc", "refresh": True},
            headers=headers,
            timeout=3  # PHASE 2 FIX: Reduce timeout to prevent blocking
        )
        
        logger.info(f"DEBUG: Chat messages response status: {chat_response.status_code}")
        logger.info(f"DEBUG: Chat messages response text: {chat_response.text}")
        
        if chat_response.status_code == 200:
            try:
                response_data = chat_response.json()
                logger.info(f"DEBUG: Parsed chat response data: {response_data}")
                
                # Extract messages from response structure
                if isinstance(response_data, dict):
                    if 'messages' in response_data:
                        chat_messages = response_data['messages']
                        logger.info(f"DEBUG: Extracted messages from 'messages' field: {len(chat_messages) if chat_messages else 0}")
                    else:
                        logger.warning(f"DEBUG: No 'messages' field found in chat response. Available keys: {list(response_data.keys())}")
                elif isinstance(response_data, list):
                    # Direct list response (fallback)
                    chat_messages = response_data
                    logger.info(f"DEBUG: Chat response is direct list: {len(chat_messages)} messages")
                else:
                    logger.warning(f"DEBUG: Unexpected chat response format: {type(response_data)}")
                
                logger.info(f"DEBUG: Final chat messages count: {len(chat_messages) if chat_messages else 0}")
            except json.JSONDecodeError as e:
                logger.error(f"DEBUG: Failed to parse chat JSON: {e}")
                logger.error(f"DEBUG: Raw chat response: {chat_response.text}")
        else:
            logger.error(f"Failed to collect chat messages: {chat_response.status_code}")
            logger.error(f"DEBUG: Raw chat response: {chat_response.text}")
        
        # Step 2: Get roll messages for the same time period
        rolls_response = requests.get(
            f"http://localhost:3010/rolls",
            params={"clientId": client_id, "limit": count, "sort": "timestamp", "order": "desc", "refresh": True},
            headers=headers,
            timeout=3
        )
        
        logger.info(f"DEBUG: Rolls response status: {rolls_response.status_code}")
        logger.info(f"DEBUG: Rolls response text: {rolls_response.text}")
        
        if rolls_response.status_code == 200:
            try:
                rolls_data = rolls_response.json()
                logger.info(f"DEBUG: Parsed rolls response data: {rolls_data}")
                
                # Extract rolls from response structure
                if isinstance(rolls_data, dict):
                    # Check for 'data' field first (relay server puts rolls here)
                    if 'data' in rolls_data:
                        roll_messages = rolls_data['data']
                        logger.info(f"DEBUG: Extracted rolls from 'data' field: {len(roll_messages) if roll_messages else 0}")
                    # Fallback to 'rolls' field for backward compatibility
                    elif 'rolls' in rolls_data:
                        roll_messages = rolls_data['rolls']
                        logger.info(f"DEBUG: Extracted rolls from 'rolls' field: {len(roll_messages) if roll_messages else 0}")
                    else:
                        logger.warning(f"DEBUG: No 'data' or 'rolls' field found in rolls response. Available keys: {list(rolls_data.keys())}")
                elif isinstance(rolls_data, list):
                    # Direct list response (fallback)
                    roll_messages = rolls_data
                    logger.info(f"DEBUG: Rolls response is direct list: {len(roll_messages)} rolls")
                else:
                    logger.warning(f"DEBUG: Unexpected rolls response format: {type(rolls_data)}")
                
                logger.info(f"DEBUG: Final roll messages count: {len(roll_messages) if roll_messages else 0}")
            except json.JSONDecodeError as e:
                logger.error(f"DEBUG: Failed to parse rolls JSON: {e}")
                logger.error(f"DEBUG: Raw rolls response: {rolls_response.text}")
        else:
            logger.error(f"Failed to collect rolls: {rolls_response.status_code}")
            logger.error(f"DEBUG: Raw rolls response: {rolls_response.text}")
        
        # Step 3: Merge and sort all messages chronologically
        all_messages = []
        
        # Add chat messages with type marker
        for msg in chat_messages:
            msg['_source'] = 'chat'
            msg['_timestamp'] = msg.get('timestamp', 0)
            all_messages.append(msg)
        
        # Add roll messages with type marker
        for roll in roll_messages:
            roll['_source'] = 'roll'
            roll['_timestamp'] = roll.get('timestamp', 0)
            all_messages.append(roll)
        
        # Sort by timestamp (newest first, then we'll reverse for chronological)
        all_messages.sort(key=lambda x: x.get('_timestamp', 0), reverse=True)
        
        # Take the most recent 'count' messages and reverse to chronological order
        merged_messages = list(reversed(all_messages[:count]))
        
        logger.info(f"DEBUG: Merged {len(chat_messages)} chat messages and {len(roll_messages)} roll messages")
        logger.info(f"DEBUG: Final merged count: {len(merged_messages)}")
        logger.info(f"DEBUG: Message sources: {[msg.get('_source') for msg in merged_messages[:5]]}")
        
        return merged_messages
            
    except Exception as e:
        logger.error(f"Error collecting messages via API: {e}")
        return []
