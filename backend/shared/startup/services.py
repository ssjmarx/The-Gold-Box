"""
The Gold Box - Startup Services Module
Handles all global service initialization during server startup.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
import asyncio
import re
import json
import time
from typing import Dict, Any, List
from fastapi import FastAPI

logger = logging.getLogger(__name__)

class StartupServicesException(Exception):
    """Exception raised when startup services operations fail"""
    pass

class MessageProcessingException(Exception):
    """Exception raised when message processing fails"""
    pass

class ServiceConfigurationException(Exception):
    """Exception raised when service configuration is invalid"""
    pass

def initialize_websocket_manager():
    """
    Initialize WebSocket connection manager.
    
    Returns:
        WebSocketConnectionManager instance or None if failed
    """
    try:
        # WebSocket connection manager using FastAPI's built-in WebSocket support
        class WebSocketConnectionManager:
            """Manages WebSocket connections using FastAPI's built-in WebSocket support"""
            
            def __init__(self):
                self.active_connections: List = []
                self.connection_info: Dict[str, Dict[str, Any]] = {}
            
            async def connect(self, websocket, client_id: str, connection_info: Dict[str, Any]):
                """Accept and register a new WebSocket connection"""
                await websocket.accept()
                self.active_connections.append(websocket)
                self.connection_info[client_id] = {
                    "websocket": websocket,
                    "connected_at": "datetime.now().isoformat()",  # Simplified for startup
                    **connection_info
                }
            
            async def disconnect(self, client_id: str):
                """Remove and disconnect a WebSocket client"""
                if client_id in self.connection_info:
                    websocket = self.connection_info[client_id]["websocket"]
                    try:
                        await websocket.close()
                    except Exception as e:
                        logger.debug(f"WebSocket close during message sending cleanup: {e}")
                    
                    # Remove from active connections
                    if websocket in self.active_connections:
                        self.active_connections.remove(websocket)
                    
                    del self.connection_info[client_id]
                    logger.info(f"WebSocket client disconnected: {client_id}")
            
            async def send_to_client(self, client_id: str, message: Dict[str, Any]):
                """Send message to specific client"""
                if client_id in self.connection_info:
                    websocket = self.connection_info[client_id]["websocket"]
                    try:
                        import time
                        message["timestamp"] = time.time()
                        await websocket.send_json(message)
                        return True
                    except Exception as e:
                        logger.error(f"Error sending to WebSocket client {client_id}: {e}")
                        # Remove disconnected client
                        await self.disconnect(client_id)
                        return False
                else:
                    logger.warning(f"Attempted to send to unknown WebSocket client: {client_id}")
                    return False
            
            async def handle_message(self, client_id: str, message: Dict[str, Any]):
                """Handle incoming WebSocket message with fast-path/slow-path pattern"""
                try:
                    import time
                    message_type = message.get("type")
                    
                    # Log all incoming message types (except ping/pong for performance)
                    if message_type != "ping":
                        logger.info(f"WebSocket: Received message type '{message_type}' from client {client_id}")
                    
                    # FAST PATH: Handle immediate messages without blocking
                    # These must complete quickly and synchronously
                    
                    # Handle ping messages silently (don't log raw ping/pong data)
                    if message_type == "ping":
                        await self.send_to_client(client_id, {
                            "type": "pong",
                            "timestamp": time.time()
                        })
                        return
                    
                    # Handle roll results from frontend (for AI tool roll_dice) - CRITICAL FAST PATH
                    # This must be processed immediately to avoid timeouts in AI tool execution
                    if message_type == "roll_result":
                        logger.info(f"WebSocket: [FAST PATH] Routing roll_result message to handler for client {client_id}")
                        await self._handle_roll_result(client_id, message)
                        return
                    
                    # Handle settings sync from frontend (frontend is source of truth) - FAST PATH
                    if message_type == "settings_sync":
                        logger.info(f"WebSocket: [FAST PATH] Handling settings_sync for client {client_id}")
                        await self._handle_settings_sync(client_id, message)
                        return
                    
                    # SLOW PATH: Handle long-running messages as background tasks
                    # These can take significant time and must not block the message loop
                    
                    # Handle individual chat messages from frontend
                    if message_type == "chat_message":
                        logger.info(f"WebSocket: [SLOW PATH] Creating background task for chat_message")
                        asyncio.create_task(self._handle_chat_message(client_id, message))
                        return
                    
                    # Handle individual dice rolls from frontend
                    if message_type == "dice_roll":
                        logger.info(f"WebSocket: [SLOW PATH] Creating background task for dice_roll")
                        asyncio.create_task(self._handle_dice_roll(client_id, message))
                        return
                    
                    # Handle combat context messages from frontend
                    if message_type == "combat_context":
                        logger.info(f"WebSocket: [SLOW PATH] Creating background task for combat_context")
                        asyncio.create_task(self._handle_combat_context(client_id, message))
                        return
                    
                    # Handle chat requests - check for active test session first - SLOW PATH
                    if message_type == "chat_request":
                        # Check if there's an active test session for this client
                        from services.system_services.service_factory import get_testing_session_manager
                        testing_session_manager = get_testing_session_manager()
                        active_test_session = testing_session_manager.get_session_by_client(client_id)
                        
                        if active_test_session:
                            # Route to testing harness instead of AI service - fire and forget
                            logger.info(f"WebSocket: [SLOW PATH] Creating background task for test_chat_request")
                            asyncio.create_task(self._handle_test_chat_request(client_id, message, active_test_session))
                            return
                        
                        # No active test session - use normal AI service logic - fire and forget
                        logger.info(f"WebSocket: [SLOW PATH] Creating background task for chat_request")
                        asyncio.create_task(self._handle_chat_request_full(client_id, message))
                        return
                    
                    # Unknown message type
                    else:
                        logger.warning(f"Unhandled message type {message_type} from {client_id}")
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": f"Unknown message type: {message_type}",
                                "timestamp": time.time()
                            }
                        })
                        
                except (ValueError, KeyError, TypeError) as e:
                    logger.error(f"WebSocket message processing error for {client_id}: {e}")
                    raise MessageProcessingException(f"Message processing failed for {client_id}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected WebSocket error for {client_id}: {e}")
                    raise MessageProcessingException(f"Unexpected WebSocket error for {client_id}: {e}")
            
            async def _store_ai_response_in_history(self, session_id: str, ai_response: str, ai_service, processor):
                """Store AI response in conversation history using the same logic as AI service"""
                try:
                    # Use the same logic as AI service to store in conversation history
                    # This ensures consistency between what's sent to frontend and what's stored in history
                    
                    # Store the raw AI response in OpenAI format for conversation history
                    history_message = {
                        "role": "assistant",
                        "content": ai_response,
                        "timestamp": int(time.time() * 1000)
                    }
                    
                    # Store using AI session manager
                    from services.system_services.service_factory import get_ai_session_manager
                    ai_session_manager = get_ai_session_manager()
                    success = ai_session_manager.add_conversation_message(session_id, history_message)
                    
                    if success:
                        logger.info(f"AI response stored in conversation history for session {session_id}")
                    else:
                        logger.warning(f"Failed to store AI response in conversation history for session {session_id}")
                        
                except Exception as e:
                    logger.error(f"Error storing AI response in conversation history: {e}")
                    # Don't fail the entire operation if history storage fails
            
            def _convert_raw_html_to_compact(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                """Convert raw HTML messages from WebSocket to compact JSON format"""
                compact_messages = []
                
                for msg in messages:
                    try:
                        compact_msg = self._convert_single_message_to_compact(msg)
                        if compact_msg:
                            compact_messages.append(compact_msg)
                    except (ValueError, KeyError, TypeError) as e:
                        logger.warning(f"Failed to process message {msg.get('id', 'unknown')}: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error processing message {msg.get('id', 'unknown')}: {e}")
                        raise MessageProcessingException(f"Message processing failed: {e}")
                
                return compact_messages
            
            async def _handle_settings_sync(self, client_id: str, message: Dict[str, Any]):
                """Handle settings sync from frontend (frontend is source of truth)"""
                try:
                    settings_data = message.get("data", {})
                    settings = settings_data.get("settings", {})
                    
                    if not settings:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "No settings provided in settings_sync message",
                                "timestamp": time.time()
                            }
                        })
                        return
                    
                    # Import frontend settings handler
                    from services.system_services.frontend_settings_handler import receive_frontend_settings, FrontendSettingsException
                    
                    # Receive settings from frontend (frontend is source of truth)
                    try:
                        success = receive_frontend_settings(settings, client_id)
                        if success:
                            await self.send_to_client(client_id, {
                                "type": "settings_sync_response",
                                "data": {
                                    "success": True,
                                    "message": "Settings received and stored successfully",
                                    "timestamp": time.time()
                                }
                            })
                            logger.debug(f"Settings sync completed from client {client_id}")
                        else:
                            await self.send_to_client(client_id, {
                                "type": "error",
                                "data": {
                                    "error": "Failed to process settings sync",
                                    "timestamp": time.time()
                                }
                            })
                    except FrontendSettingsException as e:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": f"Settings validation error: {str(e)}",
                                "timestamp": time.time()
                            }
                        })
                        logger.error(f"Frontend settings validation error from client {client_id}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error handling settings sync from client {client_id}: {e}")
                    await self.send_to_client(client_id, {
                        "type": "error",
                        "data": {
                            "error": f"Settings sync failed: {str(e)}",
                            "timestamp": time.time()
                        }
                    })
            
            async def _handle_chat_message(self, client_id: str, message: Dict[str, Any]):
                """Handle individual chat message from frontend"""
                try:
                    message_data = message.get("data", {})
                    
                    # Validate message data
                    if not message_data:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "No message data provided",
                                "timestamp": time.time()
                            }
                        })
                        return
                    
                    # Use WebSocket message collector with delta filtering
                    from services.message_services.websocket_message_collector import add_client_message_with_delta
                    
                    # Get session ID for delta filtering (create temporary session if needed)
                    from services.system_services.service_factory import get_ai_session_manager, get_message_delta_service
                    ai_session_manager = get_ai_session_manager()
                    message_delta_service = get_message_delta_service()
                    
                    # Get or create temporary session for individual message handling
                    temp_session_id = f"temp_{client_id}_{int(time.time())}"
                    session_id = ai_session_manager.create_or_get_session(client_id, None, "unknown", "unknown")
                    
                    # Add chat message to collector with delta filtering
                    success = add_client_message_with_delta(client_id, message_data, session_id)
                    if not success:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "Failed to store chat message",
                                "timestamp": time.time()
                            }
                        })
                    else:
                        logger.debug(f"Chat message stored from client {client_id}")
                        
                except Exception as e:
                    logger.error(f"Error handling chat message from client {client_id}: {e}")
                    await self.send_to_client(client_id, {
                        "type": "error",
                        "data": {
                            "error": f"Chat message handling failed: {str(e)}",
                            "timestamp": time.time()
                        }
                    })
            
            async def _handle_dice_roll(self, client_id: str, message: Dict[str, Any]):
                """Handle individual dice roll from frontend"""
                try:
                    roll_data = message.get("data", {})
                    
                    # Validate roll data
                    if not roll_data:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "No roll data provided",
                                "timestamp": time.time()
                            }
                        })
                        return
                    
                    # Use WebSocket message collector with delta filtering
                    from services.message_services.websocket_message_collector import add_client_roll_with_delta
                    
                    # Get session ID for delta filtering (create temporary session if needed)
                    from services.system_services.service_factory import get_ai_session_manager, get_message_delta_service
                    ai_session_manager = get_ai_session_manager()
                    message_delta_service = get_message_delta_service()
                    
                    # Get or create temporary session for individual message handling
                    temp_session_id = f"temp_{client_id}_{int(time.time())}"
                    session_id = ai_session_manager.create_or_get_session(client_id, None, "unknown", "unknown")
                    
                    # Add dice roll to collector with delta filtering
                    success = add_client_roll_with_delta(client_id, roll_data, session_id)
                    if not success:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "Failed to store dice roll",
                                "timestamp": time.time()
                            }
                        })
                    else:
                        logger.debug(f"Dice roll stored from client {client_id}: {roll_data.get('formula', 'unknown')}")
                        
                except Exception as e:
                    logger.error(f"Error handling dice roll from client {client_id}: {e}")
                    await self.send_to_client(client_id, {
                        "type": "error",
                        "data": {
                            "error": f"Dice roll handling failed: {str(e)}",
                            "timestamp": time.time()
                        }
                    })
            
            async def _handle_combat_context(self, client_id: str, message: Dict[str, Any]):
                """Handle combat context message from frontend"""
                try:
                    combat_data = message.get("data", {})
                    
                    # Validate combat data
                    if not combat_data:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "No combat data provided",
                                "timestamp": time.time()
                            }
                        })
                        return
                    
                    # Use WebSocket message collector to store combat context
                    from services.message_services.websocket_message_collector import add_client_message
                    
                    # Convert combat data to message format
                    combat_message = {
                        "type": "combat_context",
                        "combat_context": combat_data,
                        "timestamp": int(time.time() * 1000)
                    }
                    
                    # Add combat context message to collector
                    success = add_client_message(client_id, combat_message)
                    if not success:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "Failed to store combat context",
                                "timestamp": time.time()
                            }
                        })
                    else:
                        logger.debug(f"Combat context stored from client {client_id}: in_combat={combat_data.get('in_combat')}")
                        
                except Exception as e:
                    logger.error(f"Error handling combat context from client {client_id}: {e}")
                    await self.send_to_client(client_id, {
                        "type": "error",
                        "data": {
                            "error": f"Combat context handling failed: {str(e)}",
                            "timestamp": time.time()
                        }
                    })
            
            def _convert_single_message_to_compact(self, message: Dict[str, Any]) -> Dict[str, Any]:
                """Convert a single raw HTML message to compact JSON format - DELEGATE TO UNIFIED PROCESSOR"""
                # Import unified processor at function level to avoid circular import issues
                from shared.core.unified_message_processor import get_unified_processor
                
                content = message.get("content", "")
                original_timestamp = message.get("timestamp")
                
                # Skip empty messages
                if not content or not content.strip():
                    return None
                
                # Use unified processor for all HTML parsing - no duplicate logic
                processor = get_unified_processor()
                parsed = processor.html_to_compact_json(content)
                
                # Override with original timestamp if provided, otherwise use current time
                if 'ts' in parsed:
                    if original_timestamp is not None:
                        parsed['ts'] = original_timestamp
                else:
                    # Generate timestamp from message if not provided
                    parsed['ts'] = int(time.time() * 1000)
                
                return parsed
            
            async def _handle_roll_result(self, client_id: str, message: Dict[str, Any]):
                """Handle roll_result message from frontend (for AI tool roll_dice)"""
                try:
                    logger.info(f"_handle_roll_result called for client {client_id}")
                    logger.info(f"Full roll_result message: {message}")
                    
                    # Extract request_id and results from message
                    request_id = message.get("request_id")
                    result_data = message.get("data", {})
                    results = result_data.get("results", [])
                    
                    logger.info(f"Extracted from roll_result message: request_id={request_id}, results_count={len(results)}")
                    
                    if not request_id:
                        logger.warning(f"Received roll_result without request_id from client {client_id}")
                        logger.warning(f"Full message: {message}")
                        return
                    
                    logger.info(f"Received roll_result for request {request_id} with {len(results)} results")
                    logger.info(f"Result data structure: {result_data}")
                    
                    # Forward to AI tool executor to resolve pending request
                    from services.ai_tools.ai_tool_executor import handle_roll_result
                    logger.info(f"Calling handle_roll_result() for request {request_id}")
                    handle_roll_result(request_id, result_data)
                    logger.info(f"handle_roll_result() completed for request {request_id}")
                    
                except Exception as e:
                    logger.error(f"Error handling roll_result from client {client_id}: {e}", exc_info=True)
            
            async def _handle_test_chat_request(self, client_id: str, message: Dict[str, Any], active_test_session: Dict[str, Any]):
                """Handle chat_request when there's an active test session - route to testing harness"""
                try:
                    from services.system_services.service_factory import get_testing_harness, get_testing_command_processor, get_testing_session_manager
                    from shared.core.message_protocol import MessageProtocol
                    from services.message_services.websocket_message_collector import add_client_message_with_delta
                    
                    test_session_id = active_test_session['test_session_id']
                    
                    # Extract message data
                    message_data = MessageProtocol.extract_message_data(message)
                    if not message_data:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "Invalid chat request data",
                                "timestamp": time.time()
                            }
                        })
                        return
                    
                    # IMPORTANT: Store messages in WebSocket message collector
                    # This ensures get_messages can retrieve them later
                    # Same logic as normal chat_request handling
                    from services.system_services.service_factory import get_ai_session_manager
                    ai_session_manager = get_ai_session_manager()
                    
                    # Get or create session for message storage
                    # Use test session ID as session_id for consistency
                    session_id = ai_session_manager.create_or_get_session(client_id, None, "test", "test")
                    
                    # Store all messages from chat_request
                    messages = message_data.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, dict):
                            # Add message to collector with delta filtering
                            add_client_message_with_delta(client_id, msg, session_id)
                            logger.debug(f"Stored message in test mode for client {client_id}")
                        elif isinstance(msg, str):
                            # Convert string messages to dict format
                            add_client_message_with_delta(client_id, {
                                "content": msg,
                                "type": "chat",
                                "timestamp": int(time.time() * 1000)
                            }, session_id)
                    
                    logger.info(f"Stored {len(messages)} messages in WebSocket collector for test session {test_session_id}")
                    
                    # Extract universal settings from the test session
                    universal_settings = active_test_session.get('universal_settings', {})
                    
                    # For testing, we want to trigger the initial prompt response
                    # This simulates what AI would receive
                    initial_prompt = active_test_session.get('initial_prompt', '')
                    
                    if initial_prompt:
                        # Send initial prompt as AI response (testing mode)
                        await self.send_to_client(client_id, {
                            "type": "test_chat_response",
                            "data": {
                                "test_session_id": test_session_id,
                                "initial_prompt": initial_prompt,
                                "message": "Testing session started. Send commands via test endpoint.",
                                "timestamp": time.time()
                            }
                        })
                        logger.info(f"Sent test chat response for session {test_session_id} to client {client_id}")
                    
                except Exception as e:
                    logger.error(f"Error handling test chat request for {client_id}: {e}")
                    await self.send_to_client(client_id, {
                        "type": "error",
                        "data": {
                            "error": f"Test chat request failed: {str(e)}",
                            "timestamp": time.time()
                        }
                    })
            
            async def _handle_chat_request_full(self, client_id: str, message: Dict[str, Any]):
                """Handle full chat_request with AI processing (runs as background task)"""
                try:
                    # Import full message processing logic from original file
                    from shared.core.message_protocol import MessageProtocol
                    from services.message_services.message_collector import add_client_message, add_client_roll, get_combined_client_messages, clear_client_data
                    from services.system_services.universal_settings import extract_universal_settings, get_provider_config
                    from services.ai_services.ai_service import get_ai_service
                    from shared.core.unified_message_processor import get_unified_processor
                    
                    message_data = MessageProtocol.extract_message_data(message)
                    if not message_data:
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "Invalid chat request data",
                                "timestamp": time.time()
                            }
                        })
                        return
                    
                    # Handle combat state from WebSocket message data (same as API chat endpoint)
                    combat_state = message_data.get("combat_state")
                    if combat_state:
                        # Update CombatEncounterService with latest combat state
                        try:
                            from services.system_services.service_factory import get_combat_encounter_service
                            combat_service = get_combat_encounter_service()
                            update_success = combat_service.update_combat_state(combat_state)
                            if update_success:
                                # logger.info(f"CombatEncounterService updated with combat state from WebSocket: {combat_state}")
                                pass
                            else:
                                logger.warning(f"Failed to update CombatEncounterService with combat state from WebSocket: {combat_state}")
                        except Exception as e:
                            logger.error(f"Error updating CombatEncounterService from WebSocket: {e}")
                    
                    # Handle message collection from WebSocket clients
                    messages = message_data.get("messages", [])
                    # No fallbacks - require explicit context_count parameter
                    if "context_count" not in message_data and "contextCount" not in message_data and "count" not in message_data:
                        raise ValueError("context_count parameter is required - no fallback values allowed")
                    
                    context_count = (
                        message_data.get("context_count") or 
                        message_data.get("contextCount") or 
                        message_data.get("count")
                    )
                        
                    if not isinstance(context_count, int) or context_count <= 0:
                        raise ValueError(f"Invalid context_count: {context_count}. Must be a positive integer.")
                    scene_id = message_data.get("scene_id")
                    
                    # Log actual context count being used for debugging
                    logger.debug(f"Using context count: {context_count} (from message_data keys: {list(message_data.keys())})")
                    
                    # Use new WebSocket message collector with delta filtering
                    from services.message_services.websocket_message_collector import (
                        add_client_message_with_delta, add_client_roll_with_delta, get_combined_client_messages, clear_client_data
                    )
                    
                    # Get frontend settings for processing first (frontend is source of truth)
                    from services.system_services.frontend_settings_handler import get_all_frontend_settings
                    try:
                        stored_settings = get_all_frontend_settings()
                    except Exception as e:
                        logger.error(f"Failed to get frontend settings: {e}")
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": "Failed to retrieve frontend settings",
                                "timestamp": time.time()
                            }
                        })
                        return
                    
                    # Extract universal settings with proper request data structure
                    request_data_for_settings = {
                        'settings': stored_settings
                    }
                    universal_settings = extract_universal_settings(request_data_for_settings, "websocket_chat")
                    
                    # Don't clear client data - let delta service handle filtering
                    # clear_client_data(client_id)
                    
                    # Get or create AI session first before using session_id
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
                    # logger.info(f"AI session for WebSocket client {client_id}: {session_id} ({provider}/{model})")
                    
                    # Force full context if requested
                    if force_full_context:
                        logger.info(f"Force full context for session {session_id} - bypassing delta filtering")
                        message_delta_service.force_full_context(session_id)
                    
                    # Add each message to WebSocket message collector for this client with delta filtering
                    for msg in messages:
                        if isinstance(msg, dict):
                            # Simplified dice roll detection - delegate to unified processor
                            msg_type = msg.get("type", "")
                            content = msg.get("content", "")
                            
                            # Check if this is a dice roll message (basic type check only)
                            is_dice_roll = (msg_type == "roll")
                            
                            if is_dice_roll:
                                # This is a dice roll - add to rolls collection with delta filtering
                                logger.debug(f"Detected dice roll: {content} (type: {msg_type})")
                                add_client_roll_with_delta(client_id, msg, session_id)
                            else:
                                # This is a regular chat message - add with delta filtering
                                add_client_message_with_delta(client_id, msg, session_id)
                        elif isinstance(msg, str):
                            # Convert string messages to dict format and add with delta filtering
                            add_client_message_with_delta(client_id, {
                                "content": msg,
                                "type": "chat",
                                "timestamp": int(time.time() * 1000)
                            }, session_id)
                    
                    # Get delta-filtered messages from WebSocket message collector for processing
                    from services.message_services.websocket_message_collector import get_delta_filtered_client_messages
                    stored_messages = get_delta_filtered_client_messages(client_id, session_id, context_count)
                    
                    # Log actual message count for debugging
                    logger.debug(f"Retrieved {len(stored_messages)} messages from WebSocket collector (requested: {context_count})")
                    
                    # Add session ID to universal settings for response delivery
                    universal_settings['ai_session_id'] = session_id
                    
                    # Add client ID to universal settings for response delivery
                    universal_settings['relay_client_id'] = client_id
                    
                    # Import AI service directly - this will use singleton get_ai_service() 
                    # which has been fixed to use key manager's provider manager
                    ai_service = get_ai_service()
                    processor = get_unified_processor()
                    
                    # Step 1.5: Convert raw HTML messages to compact JSON for AI service
                    compact_stored_messages = self._convert_raw_html_to_compact(stored_messages)
                    
                    # Delta filtering already logged by get_delta_filtered_client_messages()
                    # Force full context if requested
                    if force_full_context:
                        logger.info(f"Force full context for WebSocket session {session_id} - bypassing delta filtering")
                        message_delta_service.force_full_context(session_id)
                    
                    # Use compact messages (AI service will handle conversation history)
                    compact_messages = compact_stored_messages
                    
                    # Get fresh combat context from CombatEncounterService for AI (same as API chat endpoint)
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
                        
                        # logger.info(f"Fresh combat context from service for WebSocket: in_combat={combat_context.get('in_combat', False)}")
                        
                    except Exception as e:
                        logger.error(f"Error getting combat context from service for WebSocket: {e}")
                    
                    # Get AI role from settings for enhanced role-based prompt generation
                    ai_role = universal_settings.get('ai_role', 'gm')
                    
                    # Generate enhanced system prompt based on AI role using unified processor
                    system_prompt = processor.generate_enhanced_system_prompt(ai_role, compact_messages)
                    import json
                    compact_json_context = json.dumps(compact_messages, indent=2)
                    
                    # Generate dynamic combat-aware prompt
                    from services.ai_services.combat_prompt_generator import get_combat_prompt_generator
                    
                    combat_prompt_generator = get_combat_prompt_generator()
                    combat_context = combat_context if combat_context else {}
                    combat_state = combat_state if combat_state else {}
                    
                    dynamic_prompt = combat_prompt_generator.generate_prompt(combat_context, combat_state)
                    
                    # Prepare AI messages (old logic - NOT sent to AI when function calling is enabled)
                    ai_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\n{dynamic_prompt}"}
                    ]
                    
                    # Import shared function for AI processing (function calling or standard)
                    from api.api_chat import process_with_function_calling_or_standard
                    
                    # Extract message_delta from WebSocket request data for function calling mode
                    # Log all keys in message_data for debugging
                    logger.debug(f"WebSocket message_data keys: {list(message_data.keys())}")
                    logger.debug(f"WebSocket message_data content: {json.dumps({k: v for k, v in message_data.items() if k not in ['messages']}, indent=2)}")
                    
                    message_delta = message_data.get("message_delta", {})
                    if message_delta:
                        universal_settings['message_delta'] = message_delta
                        logger.info(f"Frontend delta counts received: New={message_delta.get('new_messages', 0)}, Deleted={message_delta.get('deleted_messages', 0)}")
                    else:
                        logger.warning(f"No message_delta found in WebSocket request. Available keys: {list(message_data.keys())}")
                    
                    # Use shared function for AI processing (function calling or standard)
                    # This logic is shared with HTTP API endpoint to avoid duplication
                    ai_response_data = await process_with_function_calling_or_standard(
                        universal_settings=universal_settings,
                        compact_messages=compact_messages,
                        system_prompt=system_prompt,
                        session_id=session_id,
                        client_id=client_id
                    )
                    
                    ai_response = ai_response_data.get("response", "")
                    
                    # Use unified processor to properly process AI responses
                    api_formatted = processor.process_ai_response(ai_response, compact_messages)
                    
                    # Send processed messages to Foundry via WebSocket
                    # AI response is already stored by ai_service.process_compact_context()
                    if api_formatted and api_formatted.get("success", False):
                        client_id_for_ws = universal_settings.get('relay_client_id')
                        if client_id_for_ws:
                            from api.api_chat import _send_messages_to_websocket
                            await _send_messages_to_websocket(api_formatted, client_id_for_ws)
                        else:
                            logger.warning("No client ID available - cannot send messages to Foundry")
                    else:
                        logger.error("Failed to process AI response to API format")
                    
                except Exception as e:
                    logger.error(f"Error in _handle_chat_request_full for client {client_id}: {e}", exc_info=True)
                    await self.send_to_client(client_id, {
                        "type": "error",
                        "data": {
                            "error": f"Chat request processing failed: {str(e)}",
                            "timestamp": time.time()
                        }
                    })
        
        
        websocket_manager = WebSocketConnectionManager()
        # WebSocket connection manager initialized (no server module exports - use ServiceFactory)
        
        return websocket_manager
        
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize WebSocket connection manager: {e}")
        raise StartupServicesException(f"WebSocket manager initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket connection manager: {e}")
        raise StartupServicesException(f"Unexpected WebSocket manager error: {e}")

def setup_settings_manager():
    """
    Initialize global settings manager.
    
    Returns:
        SettingsManager instance or None if failed
    """
    try:
        # Global settings dictionary for frontend configuration
        frontend_settings = {}

        class SettingsManager:
            """Global settings manager for frontend configuration"""
            
            @staticmethod
            def update_settings(new_settings: Dict) -> bool:
                """Update global frontend settings dictionary"""
                try:
                    nonlocal frontend_settings
                    frontend_settings.clear()
                    frontend_settings.update(new_settings)
                    return True
                except (TypeError, ValueError) as e:
                    logger.error(f"Invalid settings data: {e}")
                    raise ServiceConfigurationException(f"Settings validation failed: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error updating settings: {e}")
                    raise ServiceConfigurationException(f"Settings update failed: {e}")
            
            @staticmethod
            def get_settings() -> Dict:
                """Get current frontend settings"""
                nonlocal frontend_settings
                return frontend_settings.copy()
            
            @staticmethod
            def get_setting(key: str, default=None):
                """Get a specific frontend setting"""
                nonlocal frontend_settings
                return frontend_settings.get(key, default)
            
            @staticmethod
            def clear_settings():
                """Clear all frontend settings"""
                nonlocal frontend_settings
                frontend_settings.clear()
                logger.info("Frontend settings cleared")
        
        settings_manager = SettingsManager()
        logger.info("Settings manager initialized (no server module exports - use ServiceFactory)")
        
        return settings_manager
        
    except (RuntimeError, ValueError) as e:
        logger.error(f"Failed to initialize settings manager: {e}")
        raise StartupServicesException(f"Settings manager initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize settings manager: {e}")
        raise StartupServicesException(f"Unexpected settings manager error: {e}")


async def start_websocket_chat_handler():
    """
    Initialize WebSocket chat handler (now using FastAPI built-in WebSocket).
    
    Returns:
        True if successful, False otherwise
    """
    try:
        return True
        
    except Exception as e:
        logger.error(f"Failed to start WebSocket chat handler: {e}")
        return False

def get_global_services() -> Dict[str, Any]:
    """
    Get and initialize all global services and register with ServiceRegistry.
    
    Returns:
        Dictionary containing all initialized global services
    """
    services = {}
    
    # Import service registry
    from services.system_services.registry import ServiceRegistry
    
    # Initialize WebSocket connection manager
    websocket_manager = initialize_websocket_manager()
    if websocket_manager:
        if not ServiceRegistry.register('websocket_manager', websocket_manager):
            logger.error("Failed to register websocket manager")
        else:
            services['websocket_manager'] = websocket_manager
    
    # Initialize settings manager
    settings_manager = setup_settings_manager()
    if settings_manager:
        if not ServiceRegistry.register('settings_manager', settings_manager):
            logger.error("Failed to register settings manager")
        else:
            services['settings_manager'] = settings_manager
    
    # Initialize frontend settings handler (frontend is source of truth)
    from services.system_services.frontend_settings_handler import get_frontend_settings_handler
    try:
        frontend_settings_handler = get_frontend_settings_handler()
        if not ServiceRegistry.register('frontend_settings_handler', frontend_settings_handler):
            logger.error("Failed to register frontend settings handler")
        else:
            services['frontend_settings_handler'] = frontend_settings_handler
            logger.info("✅ Frontend settings handler initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize frontend settings handler: {e}")
        raise StartupServicesException(f"Frontend settings handler initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize frontend settings handler: {e}")
        raise StartupServicesException(f"Unexpected frontend settings handler error: {e}")
    
    # Initialize client manager directly to avoid ServiceFactory circular dependency
    from services.system_services.client_manager import ClientManager
    try:
        client_manager = ClientManager()
        if not ServiceRegistry.register('client_manager', client_manager):
            logger.error("Failed to register client manager")
            raise StartupServicesException("Client manager registration failed")
        else:
            services['client_manager'] = client_manager
            logger.info("✅ Client manager initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize client manager: {e}")
        raise StartupServicesException(f"Client manager initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize client manager: {e}")
        raise StartupServicesException(f"Unexpected client manager error: {e}")
    
    # Initialize WebSocket message collector directly to avoid ServiceFactory circular dependency
    from services.message_services.websocket_message_collector import get_websocket_message_collector
    try:
        websocket_message_collector = get_websocket_message_collector()
        # Register with BOTH names for compatibility with get_message_collector()
        if not ServiceRegistry.register('websocket_message_collector', websocket_message_collector):
            logger.error("Failed to register websocket message collector")
        elif not ServiceRegistry.register('message_collector', websocket_message_collector):
            logger.error("Failed to register message_collector")
        else:
            services['websocket_message_collector'] = websocket_message_collector
            services['message_collector'] = websocket_message_collector
            logger.info("✅ WebSocket message collector initialized and registered (as both websocket_message_collector and message_collector)")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize websocket message collector: {e}")
        raise StartupServicesException(f"WebSocket message collector initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize websocket message collector: {e}")
        raise StartupServicesException(f"Unexpected websocket message collector error: {e}")
    
    # Initialize input validator directly to avoid ServiceFactory circular dependency
    from shared.security.input_validator import UniversalInputValidator
    try:
        input_validator = UniversalInputValidator()
        if not ServiceRegistry.register('input_validator', input_validator):
            logger.error("Failed to register input validator")
        else:
            services['input_validator'] = input_validator
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize input validator: {e}")
        raise StartupServicesException(f"Input validator initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize input validator: {e}")
        raise StartupServicesException(f"Unexpected input validator error: {e}")
    
    # Initialize attribute mapper directly to avoid ServiceFactory circular dependency
    from shared.core.simple_attribute_mapper import SimpleAttributeMapper
    try:
        attribute_mapper = SimpleAttributeMapper()
        if not ServiceRegistry.register('attribute_mapper', attribute_mapper):
            logger.error("Failed to register attribute mapper")
        else:
            services['attribute_mapper'] = attribute_mapper
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize attribute mapper: {e}")
        raise StartupServicesException(f"Attribute mapper initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize attribute mapper: {e}")
        raise StartupServicesException(f"Unexpected attribute mapper error: {e}")
    
    # Initialize JSON optimizer directly to avoid ServiceFactory circular dependency
    from shared.core.json_optimizer import JSONOptimizer
    try:
        json_optimizer = JSONOptimizer()
        if not ServiceRegistry.register('json_optimizer', json_optimizer):
            logger.error("Failed to register json optimizer")
        else:
            services['json_optimizer'] = json_optimizer
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize json optimizer: {e}")
        raise StartupServicesException(f"JSON optimizer initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize json optimizer: {e}")
        raise StartupServicesException(f"Unexpected JSON optimizer error: {e}")
    
    # Initialize combat encounter service directly to avoid ServiceFactory circular dependency
    from services.message_services.combat_encounter_service import get_combat_encounter_service
    try:
        combat_encounter_service = get_combat_encounter_service()
        if not ServiceRegistry.register('combat_encounter_service', combat_encounter_service):
            logger.error("Failed to register combat encounter service")
        else:
            services['combat_encounter_service'] = combat_encounter_service
            logger.info("✅ Combat encounter service initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize combat encounter service: {e}")
        raise StartupServicesException(f"Combat encounter service initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize combat encounter service: {e}")
        raise StartupServicesException(f"Unexpected combat encounter service error: {e}")
    
    # Initialize whisper service directly to avoid ServiceFactory circular dependency
    from services.message_services.whisper_service import get_whisper_service
    try:
        whisper_service = get_whisper_service()
        if not ServiceRegistry.register('whisper_service', whisper_service):
            logger.error("Failed to register whisper service")
        else:
            services['whisper_service'] = whisper_service
            logger.info("✅ Whisper service initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize whisper service: {e}")
        raise StartupServicesException(f"Whisper service initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize whisper service: {e}")
        raise StartupServicesException(f"Unexpected whisper service error: {e}")
    
    # Initialize chat card translation cache and translator
    from services.message_services.chat_card_translation_cache import get_current_cache, reset_cache, is_cache_active
    try:
        # Reset and initialize translation cache for new AI turn
        reset_cache()
        translation_cache = get_current_cache()
        if not ServiceRegistry.register('chat_card_translation_cache', translation_cache):
            logger.error("Failed to register chat card translation cache")
        else:
            services['chat_card_translation_cache'] = translation_cache
            logger.info("✅ Chat card translation cache initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize chat card translation cache: {e}")
        raise StartupServicesException(f"Chat card translation cache initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize chat card translation cache: {e}")
        raise StartupServicesException(f"Unexpected chat card translation cache error: {e}")
    
    # Initialize chat card translator
    from services.message_services.chat_card_translator import get_translator, reset_translator
    try:
        # Reset and initialize chat card translator for new AI turn
        reset_translator()
        chat_card_translator = get_translator()
        if not ServiceRegistry.register('chat_card_translator', chat_card_translator):
            logger.error("Failed to register chat card translator")
        else:
            services['chat_card_translator'] = chat_card_translator
            logger.info("✅ Chat card translator initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize chat card translator: {e}")
        raise StartupServicesException(f"Chat card translator initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize chat card translator: {e}")
        raise StartupServicesException(f"Unexpected chat card translator error: {e}")
    
    # Initialize AI session manager
    from services.ai_services.ai_session_manager import get_ai_session_manager
    try:
        ai_session_manager = get_ai_session_manager()
        if not ServiceRegistry.register('ai_session_manager', ai_session_manager):
            logger.error("Failed to register AI session manager")
        else:
            services['ai_session_manager'] = ai_session_manager
            logger.info("✅ AI session manager initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize AI session manager: {e}")
        raise StartupServicesException(f"AI session manager initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize AI session manager: {e}")
        raise StartupServicesException(f"Unexpected AI session manager error: {e}")
    
    # Initialize message delta service
    from services.message_services.message_delta_service import get_message_delta_service
    try:
        message_delta_service = get_message_delta_service()
        if not ServiceRegistry.register('message_delta_service', message_delta_service):
            logger.error("Failed to register message delta service")
        else:
            services['message_delta_service'] = message_delta_service
            logger.info("✅ Message delta service initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize message delta service: {e}")
        raise StartupServicesException(f"Message delta service initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize message delta service: {e}")
        raise StartupServicesException(f"Unexpected message delta service error: {e}")
    
    # Initialize AI tool executor for function calling
    from services.ai_tools.ai_tool_executor import get_ai_tool_executor
    try:
        ai_tool_executor = get_ai_tool_executor()
        if not ServiceRegistry.register('ai_tool_executor', ai_tool_executor):
            logger.error("Failed to register AI tool executor")
        else:
            services['ai_tool_executor'] = ai_tool_executor
            logger.info("✅ AI tool executor initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize AI tool executor: {e}")
        raise StartupServicesException(f"AI tool executor initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize AI tool executor: {e}")
        raise StartupServicesException(f"Unexpected AI tool executor error: {e}")
    
    # Initialize AI orchestrator for function calling workflow
    from services.ai_services.ai_orchestrator import get_ai_orchestrator
    try:
        ai_orchestrator = get_ai_orchestrator()
        if not ServiceRegistry.register('ai_orchestrator', ai_orchestrator):
            logger.error("Failed to register AI orchestrator")
        else:
            services['ai_orchestrator'] = ai_orchestrator
            logger.info("✅ AI orchestrator initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize AI orchestrator: {e}")
        raise StartupServicesException(f"AI orchestrator initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize AI orchestrator: {e}")
        raise StartupServicesException(f"Unexpected AI orchestrator error: {e}")
    
    # Initialize testing session manager
    from services.system_services.testing_session_manager import get_testing_session_manager
    try:
        testing_session_manager = get_testing_session_manager()
        if not ServiceRegistry.register('testing_session_manager', testing_session_manager):
            logger.error("Failed to register testing session manager")
        else:
            services['testing_session_manager'] = testing_session_manager
            logger.info("✅ Testing session manager initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize testing session manager: {e}")
        raise StartupServicesException(f"Testing session manager initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize testing session manager: {e}")
        raise StartupServicesException(f"Unexpected testing session manager error: {e}")
    
    # Initialize testing harness
    from services.ai_services.testing_harness import get_testing_harness
    try:
        testing_harness = get_testing_harness()
        if not ServiceRegistry.register('testing_harness', testing_harness):
            logger.error("Failed to register testing harness")
        else:
            services['testing_harness'] = testing_harness
            logger.info("✅ Testing harness initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize testing harness: {e}")
        raise StartupServicesException(f"Testing harness initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize testing harness: {e}")
        raise StartupServicesException(f"Unexpected testing harness error: {e}")
    
    # Initialize testing command processor
    from services.ai_services.testing_command_processor import get_testing_command_processor
    try:
        testing_command_processor = get_testing_command_processor()
        if not ServiceRegistry.register('testing_command_processor', testing_command_processor):
            logger.error("Failed to register testing command processor")
        else:
            services['testing_command_processor'] = testing_command_processor
            logger.info("✅ Testing command processor initialized and registered")
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to initialize testing command processor: {e}")
        raise StartupServicesException(f"Testing command processor initialization failed: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize testing command processor: {e}")
        raise StartupServicesException(f"Unexpected testing command processor error: {e}")
    
    # Initialize AI service - move after ServiceRegistry is ready
    # This will be initialized later in startup sequence
    services['ai_service'] = None  # Placeholder, will be set after registry is ready
    
    # Start WebSocket chat handler
    services['websocket_started'] = asyncio.run(start_websocket_chat_handler())
    
    # Validate core service initialization (excluding ai_service which is initialized after)
    core_services_valid = (
        services.get('websocket_manager') is not None and
        services.get('settings_manager') is not None and
        services.get('frontend_settings_handler') is not None and
        services.get('client_manager') is not None and
        services.get('websocket_message_collector') is not None and
        services.get('attribute_mapper') is not None and
        services.get('json_optimizer') is not None and
        services.get('combat_encounter_service') is not None and
        services.get('whisper_service') is not None and
        services.get('chat_card_translation_cache') is not None and
        services.get('chat_card_translator') is not None and
        services.get('testing_session_manager') is not None and
        services.get('testing_harness') is not None and
        services.get('testing_command_processor') is not None
    )
    
    services['services_valid'] = core_services_valid
    
    # Registry is already marked as ready from validate_requirements()
    # No need to call initialize_complete() again
    
    if core_services_valid:
        # Initialize AI service after registry is ready - create directly to avoid factory circular dependency
        try:
            from services.ai_services.ai_service import AIService
            # Get provider manager from already registered services
            provider_manager = ServiceRegistry.get('provider_manager')
            ai_service = AIService(provider_manager)
            if ai_service:
                if not ServiceRegistry.register('ai_service', ai_service):
                    logger.error("Failed to register AI service")
                    services['services_valid'] = False
                else:
                    services['ai_service'] = ai_service
                    logger.info("✅ AI service initialized and registered")
            else:
                logger.error("Failed to create AI service")
                services['services_valid'] = False
        except (ImportError, RuntimeError, ValueError) as e:
            logger.error(f"Failed to initialize AI service: {e}")
            raise StartupServicesException(f"AI service initialization failed: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            raise StartupServicesException(f"Unexpected AI service error: {e}")
        
        if services['services_valid']:
            logger.info("✅ All global services initialized and registered")
            # Mark registry as fully initialized
            ServiceRegistry.initialize_complete()
        else:
            logger.warning("⚠️  Some global services failed to initialize")
    else:
        logger.warning("⚠️  Core services failed to initialize")
    
    return services

async def run_server_startup() -> bool:
    """
    Run complete server startup sequence.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Starting complete server startup sequence...")
        
        # Get and initialize all global services
        services = get_global_services()
        
        # Check if all services initialized successfully
        if services.get('services_valid', False):
            logger.info("✅ Server startup completed successfully")
            return True
        else:
            logger.error("❌ Server startup failed - some services did not initialize properly")
            return False
            
    except Exception as e:
        logger.error(f"Server startup failed with exception: {e}")
        return False

def setup_application_routers(app: FastAPI) -> bool:
    """
    Setup application routers and endpoints.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Import routers - they will use service factory when accessed, not during setup
        from api.api_chat import router as api_chat_router
        from api.health import create_health_router
        from api.system import create_system_router
        from api.session import create_session_router
        from api.admin import create_admin_router
        
        # Get components for router setup
        from .config import get_server_config
        
        config = get_server_config()
        
        # Create and include routers - routers will use service factory when needed
        health_router = create_health_router(config)
        system_router = create_system_router(config)
        session_router = create_session_router(config)
        admin_router = create_admin_router(config)
        
        # Include routers in app
        app.include_router(health_router, prefix="/api")
        app.include_router(system_router, prefix="/api")
        app.include_router(session_router, prefix="/api")
        app.include_router(admin_router, prefix="/api")
        app.include_router(api_chat_router, prefix="/api")
        
        logger.info("All application routers included successfully")
        return True
        
    except (ImportError, RuntimeError) as e:
        logger.error(f"Failed to setup application routers: {e}")
        raise StartupServicesException(f"Router setup failed: {e}")
    except Exception as e:
        logger.error(f"Failed to setup application routers: {e}")
        raise StartupServicesException(f"Unexpected router setup error: {e}")
