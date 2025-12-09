"""
The Gold Box - Startup Services Module

Handles all global service initialization during server startup.

License: CC-BY-NC-SA 4.0 (compatible with dependencies)
"""

import logging
import asyncio
from typing import Dict, Any, List
from fastapi import FastAPI

logger = logging.getLogger(__name__)

def initialize_websocket_manager():
    """
    Initialize the WebSocket connection manager.
    
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
                logger.info(f"WebSocket client connected: {client_id}")
            
            async def disconnect(self, client_id: str):
                """Remove and disconnect a WebSocket client"""
                if client_id in self.connection_info:
                    websocket = self.connection_info[client_id]["websocket"]
                    try:
                        await websocket.close()
                    except:
                        pass
                    
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
                """Handle incoming WebSocket message"""
                try:
                    import time
                    message_type = message.get("type")
                    
                    # Handle ping messages
                    if message_type == "ping":
                        await self.send_to_client(client_id, {
                            "type": "pong",
                            "timestamp": time.time()
                        })
                        return
                    
                    # Handle chat requests using existing logic
                    if message_type == "chat_request":
                        # Import:: full message processing logic from original server
                        from shared.core.message_protocol import MessageProtocol
                        from services.message_services.message_collector import get_message_collector, add_client_message, add_client_roll, get_combined_client_messages
                        from services.system_services.universal_settings import extract_universal_settings, get_provider_config
                        from services.ai_services.ai_service import get_ai_service
                        from shared.core.processor import ChatContextProcessor
                        from api.api_chat import APIChatProcessor
                        
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
                        
                        # Handle message collection from WebSocket clients
                        messages = message_data.get("messages", [])
                        context_count = message_data.get("context_count", 15)
                        scene_id = message_data.get("scene_id")
                        
                        # Add each message to the message collector for this client
                        for msg in messages:
                            if isinstance(msg, dict):
                                add_client_message(client_id, msg)
                            elif isinstance(msg, str):
                                # Convert string messages to dict format
                                add_client_message(client_id, {
                                    "content": msg,
                                    "type": "chat",
                                    "timestamp": int(time.time() * 1000)
                                })
                        
                        logger.info(f"Collected {len(messages)} messages from WebSocket client {client_id}")
                        
                        # Get stored messages from message collector for processing
                        stored_messages = get_combined_client_messages(client_id, context_count)
                        logger.info(f"Retrieved {len(stored_messages)} stored messages for processing")
                        
                        logger.info(f"Processing WebSocket chat request from {client_id}: {len(stored_messages)} messages")
                    
                        # Get stored settings for processing from ServiceRegistry
                        from services.system_services.registry import ServiceRegistry
                        try:
                            settings_manager = ServiceRegistry.get('settings_manager')
                            stored_settings = settings_manager.get_settings()
                        except ValueError:
                            logger.error("❌ WebSocket: Settings manager not available in registry")
                            return
                        
                        # Extract universal settings with proper request data structure
                        request_data_for_settings = {
                            'settings': stored_settings
                        }
                        universal_settings = extract_universal_settings(request_data_for_settings, "websocket_chat")
                        
                        # Check user's chat processing mode setting
                        chat_processing_mode = universal_settings.get('chat processing mode', 'general')
                        logger.info(f"WebSocket: Using chat processing mode: {chat_processing_mode}")
                        
                        # Get provider config
                        provider_config = get_provider_config(universal_settings, use_tactical=False)
                        
                        # Add client ID to universal settings for response delivery
                        universal_settings['relay client id'] = client_id
                        logger.info(f"WebSocket: Added client ID to settings: {client_id}")
                        
                        # Process AI directly via WebSocket
                        logger.info("WebSocket: Processing AI directly via WebSocket (bypassing HTTP endpoints)")
                        
                        # Import AI service directly - this will use the singleton get_ai_service() 
                        # which has been fixed to use the key manager's provider manager
                        ai_service = get_ai_service()
                        logger.info("WebSocket: Using singleton AI service (should reuse provider manager)")
                        processor = ChatContextProcessor()
                        
                        # Convert stored messages to compact JSON for AI
                        api_chat_processor = APIChatProcessor()
                        compact_messages = api_chat_processor.process_api_messages(stored_messages)
                        
                        # Get AI role from settings for enhanced role-based prompt generation
                        ai_role = universal_settings.get('ai role', 'gm')
                        
                        # Generate enhanced system prompt based on AI role
                        from api.api_chat import _generate_enhanced_system_prompt
                        import json
                        system_prompt = _generate_enhanced_system_prompt(ai_role, compact_messages)
                        compact_json_context = json.dumps(compact_messages, indent=2)
                        
                        # Prepare AI messages
                        ai_messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Chat Context (Compact JSON Format):\n{compact_json_context}\n\nPlease respond to this conversation as an AI assistant for tabletop RPGs. If you need to generate game mechanics, use compact JSON format specified in system prompt."}
                        ]
                        
                        logger.info("=== AI SERVICE CALL DEBUG ===")
                        logger.info(f"Calling AI service with {len(stored_messages)} compact messages")
                        logger.info(f"Settings being passed to AI service: {universal_settings}")
                        
                        # Call AI service directly
                        ai_response_data = await ai_service.process_compact_context(
                            processed_messages=compact_messages,
                            system_prompt=system_prompt,
                            settings=universal_settings
                        )
                        
                        ai_response = ai_response_data.get("response", "")
                        tokens_used = ai_response_data.get("tokens_used", 0)
                        logger.info(f"AI service returned response of length: {len(ai_response)} characters")
                        logger.info(f"Tokens used: {tokens_used}")
                        
                        # Use AIChatProcessor to properly process AI responses
                        from services.ai_services.ai_chat_processor import AIChatProcessor
                        ai_chat_processor = AIChatProcessor()
                        api_formatted = ai_chat_processor.process_ai_response(ai_response, compact_messages)
                        
                        logger.info(f"AI response processed: {api_formatted}")
                        
                        # Send processed messages to Foundry via WebSocket
                        if api_formatted and api_formatted.get("success", False):
                            client_id_for_ws = universal_settings.get('relay client id')
                            if client_id_for_ws:
                                from api.api_chat import _send_messages_to_websocket
                                success_count, total_messages = await _send_messages_to_websocket(api_formatted, client_id_for_ws)
                                logger.info(f"WebSocket transmission: {success_count}/{total_messages} messages sent successfully")
                                logger.info(f"✅ Successfully sent {success_count} message(s) to Foundry chat")  # Log success message here only
                                
                                # Create success result (no response content - only metadata)
                                result = {
                                    'success': True,
                                    'response': "",  # Empty response - success message only in logs
                                    'metadata': {
                                        'context_count': len(compact_messages),
                                        'tokens_used': tokens_used,
                                        'messages_sent': success_count,
                                        'total_messages': total_messages,
                                        'api_formatted': api_formatted,
                                        'provider_used': provider_config['provider'],
                                        'model_used': provider_config['model']
                                    }
                                }
                            else:
                                logger.warning("No client ID available for WebSocket transmission")
                                # Return response with API formatted data for frontend display
                                result = {
                                    'success': True,
                                    'response': ai_response,  # Return raw AI response as fallback
                                    'metadata': {
                                        'context_count': len(compact_messages),
                                        'tokens_used': tokens_used,
                                        'messages_sent': 0,
                                        'websocket_error': "No client ID available",
                                        'api_formatted': api_formatted,
                                        'provider_used': provider_config['provider'],
                                        'model_used': provider_config['model']
                                    }
                                }
                        else:
                            logger.error("Failed to process AI response to API format")
                            result = {
                                'success': False,
                                'error': "Failed to process AI response for WebSocket transmission"
                            }
                        
                        # Send response back via WebSocket (only if there's actual response content)
                        if result['success']:
                            response_content = result.get('response', '')
                            metadata = result.get('metadata', {})
                            
                            # Only send response if there's actual content (not empty)
                            if response_content.strip():  # Only send if response has content
                                try:
                                    # Extract request ID from original message
                                    original_request_id = MessageProtocol.extract_request_id(message)
                                    logger.info(f"DEBUG: Original request ID: {original_request_id}")
                                    
                                    # Create chat response message with same request ID
                                    chat_response_message = MessageProtocol.create_chat_response(
                                        response_content,
                                        metadata,
                                        original_request_id
                                    )
                                    
                                    logger.info(f"DEBUG: Created response message with request_id: {chat_response_message.get('request_id')}")
                                    
                                    # Send response via WebSocket
                                    send_success = await self.send_to_client(client_id, chat_response_message)
                                    
                                    if send_success:
                                        logger.info(f"✅ WebSocket chat response sent successfully to {client_id}")
                                    else:
                                        logger.error(f"❌ Failed to send WebSocket chat response to {client_id}")
                                except Exception as e:
                                    logger.error(f"❌ Exception creating/sending WebSocket response: {e}")
                                    # Try to send a simple error message as fallback
                                    await self.send_to_client(client_id, {
                                        "type": "error",
                                        "data": {
                                            "error": f"Response creation failed: {e}",
                                            "timestamp": time.time()
                                        }
                                    })
                            else:
                                # No response content - AI messages already sent individually, no need for wrapper response
                                logger.info(f"✅ Multi-message response sent individually to {client_id}, no wrapper response needed")
                        else:
                            error_msg = result.get('error', 'Unknown error')
                            logger.error(f"❌ WebSocket chat error for {client_id}: {error_msg}")
                            
                            try:
                                await self.send_to_client(client_id, {
                                    "type": "error",
                                    "data": {
                                        "error": error_msg,
                                        "timestamp": time.time()
                                    }
                                })
                                logger.info(f"✅ Error message sent to {client_id}")
                            except Exception as e:
                                logger.error(f"❌ Failed to send error message to {client_id}: {e}")
                    else:
                        logger.warning(f"Unhandled message type {message_type} from {client_id}")
                        await self.send_to_client(client_id, {
                            "type": "error",
                            "data": {
                                "error": f"Unknown message type: {message_type}",
                                "timestamp": time.time()
                            }
                        })
                        
                except Exception as e:
                    logger.error(f"Error handling WebSocket message from {client_id}: {e}")
                    await self.send_to_client(client_id, {
                        "type": "error",
                        "data": {
                            "error": f"Message processing error: {e}",
                            "timestamp": time.time()
                        }
                    })
        
        websocket_manager = WebSocketConnectionManager()
        logger.info("WebSocket connection manager initialized")
        
        # Export to server module for other files to import
        try:
            import server
            server.websocket_manager = websocket_manager
        except ImportError:
            # This can happen during initial imports, but that's OK
            pass
        
        return websocket_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize WebSocket connection manager: {e}")
        return None

def setup_settings_manager():
    """
    Initialize the global settings manager.
    
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
                    logger.info(f"Frontend settings updated: {len(frontend_settings)} settings loaded")
                    return True
                except Exception as e:
                    logger.error(f"Failed to update frontend settings: {e}")
                    return False
            
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
        logger.info("Settings manager initialized")
        
        # Export settings_manager to server module for other files to import
        try:
            import server
            server.settings_manager = settings_manager
            server.get_settings_manager = lambda: settings_manager
        except ImportError:
            # This can happen during initial imports, but that's OK
            pass
        
        return settings_manager
        
    except Exception as e:
        logger.error(f"Failed to initialize settings manager: {e}")
        return None


async def start_websocket_chat_handler():
    """
    Initialize WebSocket chat handler (now using FastAPI built-in WebSocket).
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("WebSocket endpoint /ws registered with FastAPI")
        logger.info("WebSocket chat handler started successfully")
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
    
    # Initialize client manager
    from services.system_services.client_manager import ClientManager
    client_manager = ClientManager()
    if client_manager:
        if not ServiceRegistry.register('client_manager', client_manager):
            logger.error("Failed to register client manager")
        else:
            services['client_manager'] = client_manager
    
    # Start WebSocket chat handler
    services['websocket_started'] = asyncio.run(start_websocket_chat_handler())
    
    # Validate service initialization
    services_valid = (
        services.get('websocket_manager') is not None and
        services.get('settings_manager') is not None and
        services.get('client_manager') is not None
    )
    
    services['services_valid'] = services_valid
    
    if services_valid:
        logger.info("✅ All global services initialized and registered")
        # Mark registry as fully initialized
        ServiceRegistry.initialize_complete()
    else:
        logger.warning("⚠️ Some global services failed to initialize")
    
    return services

def setup_application_routers(app: FastAPI) -> bool:
    """
    Setup application routers and endpoints.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Include API chat router
        from api.api_chat import router as api_chat_router
        app.include_router(api_chat_router)
        logger.info("API chat router included")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup application routers: {e}")
        return False
