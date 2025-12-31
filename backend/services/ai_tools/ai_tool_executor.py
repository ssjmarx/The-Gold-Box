#!/usr/bin/env python3
"""
AI Tool Executor for The Gold Box
Executes AI tools with proper separation of concerns
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Dictionary to store pending roll requests
# Key: request_id, Value: asyncio.Future
_pending_roll_requests: Dict[str, asyncio.Future] = {}

class AIToolExecutor:
    """
    Execute AI tools and return results
    
    Uses ServiceFactory pattern for service access:
    - MessageCollector via get_message_collector()
    - WebSocketManager via get_websocket_manager()
    """
    
    def __init__(self):
        """
        Initialize AI tool executor
        
        Note: Services accessed via ServiceFactory, not passed in constructor
        This maintains single source of truth for service access
        """
        logger.info("AIToolExecutor initialized")
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute a specific tool
        
        Args:
            tool_name: Name of tool to execute (e.g., 'get_messages', 'post_messages')
            tool_args: Arguments for the tool (from AI function call)
            client_id: Client ID for message collection (transient, from WebSocket)
        
        Returns:
            Tool execution result in JSON-serializable format
        
        Raises:
            ValueError: If tool_name is unknown or tool_args invalid
        """
        
        # Route to specific tool executor
        if tool_name == 'get_message_history':
            return await self.execute_get_message_history(tool_args, client_id)
        elif tool_name == 'post_message':
            return await self.execute_post_message(tool_args, client_id)
        elif tool_name == 'roll_dice':
            return await self.execute_roll_dice(tool_args, client_id)
        elif tool_name == 'get_encounter':
            return await self.execute_get_encounter(tool_args, client_id)
        elif tool_name == 'create_encounter':
            return await self.execute_create_encounter(tool_args, client_id)
        elif tool_name == 'delete_encounter':
            return await self.execute_delete_encounter(tool_args, client_id)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def execute_get_message_history(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute get_messages tool - returns compact JSON format (same as non-tool AI chat)
        
        Args:
            args: Tool arguments (must contain 'count')
            client_id: Client ID for message collection
        
        Returns:
            Dict with compact JSON messages (token-efficient format)
        """
        try:
            # Validate arguments
            count = args.get('count', 15)
            if not isinstance(count, int) or count < 1 or count > 50:
                raise ValueError("count must be an integer between 1 and 50")
            
            # Get services via ServiceFactory (single source of truth)
            from ..system_services.service_factory import get_message_collector
            from shared.core.unified_message_processor import get_unified_processor
            
            message_collector = get_message_collector()
            unified_processor = get_unified_processor()
            
            # Collect messages WITHOUT delta filtering
            # Pass session_id=None to disable delta filtering (per requirements)
            # This uses exact same message gathering pipeline as standard mode
            messages = message_collector.get_combined_messages(
                client_id, 
                count,
                session_id=None  # Disable delta filtering
            )
            
            # Parse HTML content to compact JSON
            # WebSocket messages have raw HTML in 'content' field that needs parsing
            compact_messages = []
            for msg in messages:
                content = msg.get('content')
                
                # Check if content is HTML (starts with < and contains HTML tags)
                if isinstance(content, str) and '<' in content:
                    try:
                        # Parse HTML to compact JSON
                        compact = unified_processor.html_to_compact_json(content)
                        
                        # Preserve original timestamp
                        if 'timestamp' in msg:
                            compact['ts'] = msg['timestamp']
                        
                        compact_messages.append(compact)
                        logger.debug(f"Parsed HTML to compact: {compact.get('t', 'unknown')}")
                        
                    except Exception as parse_error:
                        # If parsing fails, log warning and try alternative approach
                        logger.warning(f"Failed to parse HTML content: {parse_error}")
                        # Try processing through standard pipeline
                        try:
                            converted = unified_processor.process_api_messages([msg])
                            compact_messages.extend(converted)
                        except:
                            # Skip this message if both approaches fail
                            continue
                else:
                    # Non-HTML content (e.g., roll messages) - process normally
                    try:
                        converted = unified_processor.process_api_messages([msg])
                        compact_messages.extend(converted)
                    except Exception as process_error:
                        logger.warning(f"Failed to process non-HTML message: {process_error}")
                        continue
            
            # Return compact JSON array directly (not JSON string)
            result = {
                "success": True,
                "count": len(compact_messages),
                "content": compact_messages
            }
            
            # Log summary
            logger.info(f"get_message_history executed: {len(compact_messages)} messages collected for client {client_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"get_message_history execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_roll_dice(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute roll_dice tool - sends roll requests to frontend, awaits results
        
        Args:
            args: Tool arguments (must contain 'rolls' array)
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with roll results for each requested roll
        """
        try:
            # Validate arguments
            rolls = args.get('rolls', [])
            if not isinstance(rolls, list) or not rolls:
                raise ValueError("rolls must be a non-empty array")
            
            # Validate each roll
            for i, roll in enumerate(rolls):
                if not isinstance(roll, dict):
                    raise ValueError(f"Roll {i} must be a dictionary")
                if 'formula' not in roll:
                    raise ValueError(f"Roll {i} missing required 'formula' field")
                formula = roll['formula']
                if not isinstance(formula, str) or not formula.strip():
                    raise ValueError(f"Roll {i} must have a non-empty formula string")
            
            # Get services via ServiceFactory
            from ..system_services.service_factory import get_websocket_manager
            from shared.core.message_protocol import MessageProtocol
            
            websocket_manager = get_websocket_manager()
            
            # Create a unique request ID for this roll batch
            request_id = str(uuid.uuid4())
            
            logger.info(f"roll_dice: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await the result
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future
            logger.info(f"roll_dice: Stored future in _pending_roll_requests. Total pending: {len(_pending_roll_requests)}")
            
            try:
                # Send roll request to frontend
                roll_message = {
                    "type": "execute_roll",
                    "request_id": request_id,
                    "data": {
                        "rolls": rolls,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, roll_message)
                logger.info(f"roll_dice: Sent {len(rolls)} roll requests to client {client_id}, request_id: {request_id}")
                
                # Wait for result with timeout (30 seconds)
                try:
                    logger.info(f"roll_dice: Waiting for result for request {request_id}...")
                    result_data = await asyncio.wait_for(result_future, timeout=30.0)
                    logger.info(f"roll_dice: Successfully awaited result for request {request_id}")
                    
                    return {
                        "success": True,
                        "count": len(rolls),
                        "results": result_data.get('results', []),
                        "request_id": request_id
                    }
                    
                except asyncio.TimeoutError:
                    logger.error(f"roll_dice: Timeout waiting for roll results, request_id: {request_id}")
                    # Check if future is still pending
                    if request_id in _pending_roll_requests:
                        logger.error(f"Future still in _pending_roll_requests but timed out")
                    else:
                        logger.error(f"Future removed from _pending_roll_requests before timeout")
                    return {
                        "success": False,
                        "error": "Timeout waiting for roll results from frontend",
                        "request_id": request_id
                    }
                    
            finally:
                # Clean up the pending request
                logger.info(f"Cleaning up future for request {request_id}")
                if request_id in _pending_roll_requests:
                    del _pending_roll_requests[request_id]
                    logger.info(f"Removed future for request {request_id} from _pending_roll_requests")
                else:
                    logger.warning(f"Future for request {request_id} not found in _pending_roll_requests during cleanup")
            
        except Exception as e:
            logger.error(f"roll_dice execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_post_message(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute post_messages tool
        
        Args:
            args: Tool arguments (must contain 'messages' array)
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with success status and message results
        """
        try:
            # Validate arguments
            messages = args.get('messages', [])
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages must be a non-empty array")
            
            # Get services via ServiceFactory (single source of truth)
            from ..system_services.service_factory import get_websocket_manager
            from shared.core.unified_message_processor import get_unified_processor
            
            websocket_manager = get_websocket_manager()
            unified_processor = get_unified_processor()
            
            results = []
            
            # Log all messages being sent to Foundry before sending
            # logger.info(f"post_messages: Sending {len(messages)} messages to Foundry for client {client_id}")
            # for i, msg_data in enumerate(messages):
            #     logger.info(f"  Message {i+1}/{len(messages)}: {msg_data}")
            
            for msg_data in messages:
                try:
                    # Detect format and convert appropriately
                    if 'compact_format' in msg_data:
                        # Compact format - convert to API format
                        api_msg = unified_processor.compact_to_api_format(msg_data['compact_format'])
                    else:
                        # Ensure message has a type field (default to chat-message if missing)
                        if 'type' not in msg_data:
                            msg_data['type'] = 'chat-message'
                        # Already API format or simple message
                        api_msg = msg_data
                    
                    # Send via WebSocket to frontend
                    ws_message = {
                        "type": "chat_response",
                        "data": {
                            "message": api_msg,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    success = await websocket_manager.send_to_client(client_id, ws_message)
                    results.append({
                        "id": msg_data.get('id', 'unknown'),
                        "success": success
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to send individual message: {e}")
                    results.append({
                        "id": msg_data.get('id', 'unknown'),
                        "success": False,
                        "error": str(e)
                    })
            
            logger.info(f"post_message executed: {len(results)}/{len(messages)} messages sent for client {client_id}")
            
            return {
                "success": True,
                "sent_count": len([r for r in results if r.get('success')]),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"post_message execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_get_encounter(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute get_encounter tool - requests fresh combat state from frontend
        
        Args:
            args: Tool arguments (no parameters required)
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with combat state or no active encounter response
        """
        try:
            # Get services via ServiceFactory (single source of truth)
            from ..system_services.service_factory import get_websocket_manager, get_message_collector
            from shared.core.message_protocol import MessageProtocol
            
            websocket_manager = get_websocket_manager()
            websocket_message_collector = get_message_collector()
            
            # Create a unique request ID for this combat state refresh
            request_id = str(uuid.uuid4())
            
            logger.info(f"get_encounter: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await combat state response
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future  # Reuse pending requests dict
            logger.info(f"get_encounter: Stored future in _pending_roll_requests. Total pending: {len(_pending_roll_requests)}")
            
            try:
                # Send combat state refresh request to frontend
                refresh_message = {
                    "type": "combat_state_refresh",
                    "request_id": request_id,
                    "data": {
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, refresh_message)
                logger.info(f"get_encounter: Sent combat_state_refresh request to client {client_id}, request_id: {request_id}")
                
                # Wait for combat state response with timeout (5 seconds - matches health check)
                try:
                    logger.info(f"get_encounter: Waiting for combat state for request {request_id}...")
                    await asyncio.wait_for(result_future, timeout=5.0)
                    logger.info(f"get_encounter: Successfully received combat state for request {request_id}")
                    
                except asyncio.TimeoutError:
                    logger.debug(f"get_encounter: Timeout waiting for combat state, request_id: {request_id}")
                    # Check if future is still pending
                    if request_id in _pending_roll_requests:
                        logger.debug(f"Future still in _pending_roll_requests but timed out")
                    else:
                        logger.debug(f"Future removed from _pending_roll_requests before timeout")
                    
                    # Timeout is acceptable - continue with cached state
                    logger.info(f"get_encounter: Using cached combat state after timeout")
                
                finally:
                    # Clean up pending request
                    logger.info(f"Cleaning up future for request {request_id}")
                    if request_id in _pending_roll_requests:
                        del _pending_roll_requests[request_id]
                        logger.info(f"Removed future for request {request_id} from _pending_roll_requests")
                    else:
                        logger.warning(f"Future for request {request_id} not found in _pending_roll_requests during cleanup")
                
                # Get cached combat state from message collector
                combat_state = websocket_message_collector.get_cached_combat_state(client_id)
                
                if not combat_state or not combat_state.get('in_combat', False):
                    # No active encounter
                    result = {
                        "success": True,
                        "in_combat": False,
                        "message": "No active encounter"
                    }
                    logger.info(f"get_encounter executed for client {client_id}: no active combat")
                    return result
                
                # Active encounter - return full combat state
                result = {
                    "success": True,
                    "in_combat": True,
                    "combat_id": combat_state.get('combat_id'),
                    "round": combat_state.get('round', 0),
                    "turn": combat_state.get('turn', 0),
                    "combatants": combat_state.get('combatants', []),
                    "last_updated": combat_state.get('last_updated')
                }
                
                logger.info(f"get_encounter executed for client {client_id}: round {combat_state.get('round', 0)}, turn {combat_state.get('turn', 0)}, {len(combat_state.get('combatants', []))} combatants")
                return result
            
            except Exception as inner_error:
                logger.error(f"get_encounter: Error during combat state request for client {client_id}: {inner_error}")
                # Continue with cached state even if refresh request fails
                pass
            
        except Exception as e:
            logger.error(f"get_encounter execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_create_encounter(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute create_encounter tool - creates a new combat encounter with specified actors
        
        Args:
            args: Tool arguments (must contain 'actor_ids' array, optional 'roll_initiative' boolean)
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with encounter creation result and combat state
        """
        try:
            # Validate arguments
            actor_ids = args.get('actor_ids', [])
            if not isinstance(actor_ids, list) or not actor_ids:
                raise ValueError("actor_ids must be a non-empty array")
            
            roll_initiative = args.get('roll_initiative', True)
            if not isinstance(roll_initiative, bool):
                raise ValueError("roll_initiative must be a boolean")
            
            # Get services via ServiceFactory
            from ..system_services.service_factory import get_websocket_manager, get_message_collector
            from shared.core.message_protocol import MessageProtocol
            
            websocket_manager = get_websocket_manager()
            websocket_message_collector = get_message_collector()
            
            # Create a unique request ID for this encounter creation
            request_id = str(uuid.uuid4())
            
            logger.info(f"create_encounter: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await combat state response
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future
            logger.info(f"create_encounter: Stored future in _pending_roll_requests. Total pending: {len(_pending_roll_requests)}")
            
            try:
                # Send encounter creation request to frontend
                create_message = {
                    "type": "create_encounter",
                    "request_id": request_id,
                    "data": {
                        "actor_ids": actor_ids,
                        "roll_initiative": roll_initiative,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, create_message)
                logger.info(f"create_encounter: Sent encounter creation request to client {client_id} with {len(actor_ids)} actors, request_id: {request_id}")
                
                # Wait for combat state response with timeout (5 seconds)
                try:
                    logger.info(f"create_encounter: Waiting for combat state for request {request_id}...")
                    await asyncio.wait_for(result_future, timeout=5.0)
                    logger.info(f"create_encounter: Successfully received combat state for request {request_id}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"create_encounter: Timeout waiting for combat state from frontend, request_id: {request_id}")
                    
                    # Log diagnostic information to help debug timeout issues
                    logger.debug(f"create_encounter: Checking message collector for client {client_id}")
                    logger.debug(f"create_encounter: Pending requests count: {len(_pending_roll_requests)}")
                    
                    return {
                        "success": False,
                        "error": "Timeout waiting for encounter creation response from frontend. Frontend may have encountered an error or the WebSocket connection may be unstable.",
                        "details": {
                            "request_id": request_id,
                            "timeout_seconds": 5,
                            "client_id": client_id,
                            "pending_requests": len(_pending_roll_requests)
                        }
                    }
                
                finally:
                    # Clean up pending request
                    logger.info(f"Cleaning up future for request {request_id}")
                    if request_id in _pending_roll_requests:
                        del _pending_roll_requests[request_id]
                        logger.info(f"Removed future for request {request_id} from _pending_roll_requests")
                    else:
                        logger.warning(f"Future for request {request_id} not found in _pending_roll_requests during cleanup")
                
                # Get cached combat state from message collector
                combat_state = websocket_message_collector.get_cached_combat_state(client_id)
                
                if not combat_state or not combat_state.get('in_combat', False):
                    # Encounter creation failed
                    return {
                        "success": False,
                        "error": "Failed to create encounter",
                        "message": "Encounter creation did not result in active combat"
                    }
                
                # Success - return full combat state
                result = {
                    "success": True,
                    "in_combat": True,
                    "combat_id": combat_state.get('combat_id'),
                    "round": combat_state.get('round', 0),
                    "turn": combat_state.get('turn', 0),
                    "combatants": combat_state.get('combatants', []),
                    "roll_initiative": roll_initiative,
                    "actor_count": len(actor_ids),
                    "last_updated": combat_state.get('last_updated')
                }
                
                logger.info(f"create_encounter executed for client {client_id}: round {combat_state.get('round', 0)}, turn {combat_state.get('turn', 0)}, {len(combat_state.get('combatants', []))} combatants")
                return result
            
            except Exception as inner_error:
                logger.error(f"create_encounter: Error during encounter creation for client {client_id}: {inner_error}")
                return {
                    "success": False,
                    "error": str(inner_error)
                }
            
        except Exception as e:
            logger.error(f"create_encounter execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_delete_encounter(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute delete_encounter tool - ends the current combat encounter
        
        Args:
            args: Tool arguments (no parameters required)
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with encounter deletion result
        """
        try:
            # Get services via ServiceFactory
            from ..system_services.service_factory import get_websocket_manager, get_message_collector
            
            websocket_manager = get_websocket_manager()
            websocket_message_collector = get_message_collector()
            
            # Check if combat is active
            combat_state = websocket_message_collector.get_cached_combat_state(client_id)
            if not combat_state or not combat_state.get('in_combat', False):
                return {
                    "success": False,
                    "message": "No active encounter to end"
                }
            
            # Create a unique request ID for this encounter deletion
            request_id = str(uuid.uuid4())
            
            logger.info(f"delete_encounter: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await combat state response
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future
            logger.info(f"delete_encounter: Stored future in _pending_roll_requests. Total pending: {len(_pending_roll_requests)}")
            
            try:
                # Send encounter deletion request to frontend
                delete_message = {
                    "type": "delete_encounter",
                    "request_id": request_id,
                    "data": {
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, delete_message)
                logger.info(f"delete_encounter: Sent encounter deletion request to client {client_id}, request_id: {request_id}")
                
                # Wait for combat state response with timeout (5 seconds)
                try:
                    logger.info(f"delete_encounter: Waiting for combat state for request {request_id}...")
                    await asyncio.wait_for(result_future, timeout=5.0)
                    logger.info(f"delete_encounter: Successfully received combat state for request {request_id}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"delete_encounter: Timeout waiting for combat state, request_id: {request_id}")
                    return {
                        "success": False,
                        "error": "Timeout waiting for encounter deletion response from frontend",
                        "request_id": request_id
                    }
                
                finally:
                    # Clean up pending request
                    logger.info(f"Cleaning up future for request {request_id}")
                    if request_id in _pending_roll_requests:
                        del _pending_roll_requests[request_id]
                        logger.info(f"Removed future for request {request_id} from _pending_roll_requests")
                    else:
                        logger.warning(f"Future for request {request_id} not found in _pending_roll_requests during cleanup")
                
                # Verify combat is no longer active
                combat_state = websocket_message_collector.get_cached_combat_state(client_id)
                if combat_state and combat_state.get('in_combat', False):
                    return {
                        "success": False,
                        "error": "Combat still active after deletion request",
                        "message": "Failed to end encounter"
                    }
                
                # Success
                result = {
                    "success": True,
                    "message": "Encounter ended successfully",
                    "in_combat": False
                }
                
                logger.info(f"delete_encounter executed for client {client_id}: encounter ended")
                return result
            
            except Exception as inner_error:
                logger.error(f"delete_encounter: Error during encounter deletion for client {client_id}: {inner_error}")
                return {
                    "success": False,
                    "error": str(inner_error)
                }
            
        except Exception as e:
            logger.error(f"delete_encounter execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def handle_roll_result(request_id: str, results: Any) -> None:
    """
    Handle incoming roll result from frontend
    Called when backend receives roll_result message
    
    Args:
        request_id: Request ID from original roll_dice call
        results: Roll results from frontend
    """
    if request_id in _pending_roll_requests:
        future = _pending_roll_requests[request_id]
        
        try:
            if not future.done():
                future.set_result(results)
                logger.info(f"Result set successfully for request {request_id}")
            else:
                logger.debug(f"Future already done for request {request_id}")
        except Exception as e:
            logger.error(f"Error setting future result for request {request_id}: {e}")
            # Try to set exception if result setting failed
            if not future.done():
                try:
                    future.set_exception(e)
                except Exception as e2:
                    logger.error(f"Error setting future exception: {e2}")
    else:
        logger.warning(f"Received roll result for unknown request_id: {request_id}")


def handle_combat_state_result(request_id: str, results: Any) -> None:
    """
    Handle incoming combat state result from frontend
    Called when backend receives combat_state message in response to encounter management request
    
    Args:
        request_id: Request ID from original encounter management call (create/delete/get)
        results: Combat state results from frontend (can be None for simple acknowledgment)
    """
    if request_id in _pending_roll_requests:
        future = _pending_roll_requests[request_id]
        
        try:
            if not future.done():
                future.set_result(results)
                logger.info(f"Combat state result set successfully for request {request_id}")
            else:
                logger.debug(f"Future already done for combat state request {request_id}")
        except Exception as e:
            logger.error(f"Error setting combat state future result for request {request_id}: {e}")
            # Try to set exception if result setting failed
            if not future.done():
                try:
                    future.set_exception(e)
                except Exception as e2:
                    logger.error(f"Error setting future exception for combat state: {e2}")
    else:
        logger.warning(f"Received combat state result for unknown request_id: {request_id}")


def get_ai_tool_executor() -> AIToolExecutor:
    """Get AI tool executor instance"""
    return AIToolExecutor()
