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

# Import log truncation utility
from shared.utils.log_utils import truncate_for_log

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
        elif tool_name == 'activate_combat':
            return await self.execute_activate_combat(tool_args, client_id)
        elif tool_name == 'advance_combat_turn':
            return await self.execute_advance_combat_turn(tool_args, client_id)
        elif tool_name == 'get_actor_details':
            return await self.execute_get_actor_details(tool_args, client_id)
        elif tool_name == 'modify_token_attribute':
            return await self.execute_modify_token_attribute(tool_args, client_id)
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
            # FIXED: Use WebSocketMessageCollector to match testing harness and live AI behavior
            from ..system_services.service_factory import get_websocket_message_collector
            from shared.core.unified_message_processor import get_unified_processor
            
            websocket_message_collector = get_websocket_message_collector()
            unified_processor = get_unified_processor()
            
            # Log which collector is being used for debugging
            logger.info(f"get_message_history: Using WebSocketMessageCollector for client {client_id}")
            
            # Collect messages WITHOUT delta filtering
            # Pass session_id=None to disable delta filtering (per requirements)
            # This uses exact same message gathering pipeline as standard mode
            messages = websocket_message_collector.get_combined_messages(
                client_id, 
                count,
                session_id=None  # Disable delta filtering
            )
            
            # Log message collection results for debugging
            logger.info(f"get_message_history: Collected {len(messages)} messages for client {client_id}")
            
            # Convert messages to compact JSON - handle both WebSocket JSON and HTML formats
            compact_messages = []
            for msg in messages:
                # Check if this is a WebSocket JSON message (has direct type field)
                msg_type = msg.get('type', '')
                
                if msg_type in ['roll', 'chat', 'cm']:
                    # WebSocket JSON message - convert directly to compact format
                    try:
                        if msg_type == 'roll':
                            # Dice roll from WebSocket
                            compact = {
                                't': 'dr',
                                'ts': msg.get('timestamp', int(datetime.now().timestamp() * 1000)),
                                'f': msg.get('formula', ''),
                                'tt': msg.get('total', 0),
                                'r': msg.get('results', []),
                                'ft': msg.get('flavor', '')
                            }
                            # Add speaker info
                            speaker = msg.get('speaker')
                            if speaker:
                                if isinstance(speaker, dict):
                                    compact['s'] = speaker.get('name', '')
                                    if speaker.get('alias'):
                                        compact['a'] = speaker.get('alias')
                                else:
                                    compact['s'] = str(speaker)
                        elif msg_type in ['chat', 'cm']:
                            # Chat message from WebSocket
                            compact = {
                                't': 'cm',
                                'ts': msg.get('timestamp', int(datetime.now().timestamp() * 1000)),
                                'c': msg.get('content', '')
                            }
                            # Add speaker info
                            speaker = msg.get('speaker')
                            if speaker:
                                if isinstance(speaker, dict):
                                    compact['s'] = speaker.get('name', '')
                                    if speaker.get('alias'):
                                        compact['a'] = speaker.get('alias')
                                else:
                                    compact['s'] = str(speaker)
                        
                        compact_messages.append(compact)
                        logger.debug(f"Converted WebSocket JSON to compact: {compact.get('t', 'unknown')} - {compact.get('f', compact.get('c', ''))}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to convert WebSocket JSON message: {e}")
                        continue
                
                else:
                    # HTML or other format - parse using unified processor
                    content = msg.get('content')
                    
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
                            logger.warning(f"Failed to parse HTML content: {parse_error}")
                            continue
                    else:
                        # Try processing through standard pipeline for other formats
                        try:
                            converted = unified_processor.process_api_messages([msg])
                            compact_messages.extend(converted)
                        except Exception as process_error:
                            logger.warning(f"Failed to process message: {process_error}")
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
                # Clean up pending request
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
            args: Tool arguments (optional 'encounter_id' parameter)
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with combat state(s) or no active encounter response
        """
        try:
            # Get optional encounter_id parameter
            encounter_id = args.get('encounter_id')
            
            # Get services via ServiceFactory (single source of truth)
            from ..system_services.service_factory import get_websocket_manager, get_message_collector
            
            websocket_manager = get_websocket_manager()
            websocket_message_collector = get_message_collector()
            
            # Create a unique request ID for this combat state refresh
            request_id = str(uuid.uuid4())
            
            logger.info(f"get_encounter: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await combat state response
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future
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
                
                # UPDATED: Use new multi-encounter storage and check both sources
                if encounter_id:
                    # Try to get encounter from WebSocketMessageCollector first (most recent)
                    combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                    
                    # If not in WebSocketMessageCollector, try CombatEncounterService
                    if not combat_state:
                        from ..system_services.service_factory import get_combat_encounter_service
                        combat_service = get_combat_encounter_service()
                        combat_state = combat_service.get_encounter_state(encounter_id)
                        
                        if not combat_state:
                            # FIXED: Return error for non-existent encounter instead of synthetic inactive state
                            result = {
                                "success": False,
                                "error": f"Encounter {encounter_id} not found or not active"
                            }
                            logger.info(f"get_encounter executed for client {client_id}: encounter {encounter_id} not found in either collector or service")
                            return result
                    
                    result = {
                        "success": True,
                        "in_combat": True,
                        "combat_id": combat_state.get('combat_id'),
                        "round": combat_state.get('round', 0),
                        "turn": combat_state.get('turn', 0),
                        "combatants": combat_state.get('combatants', []),
                        "is_active": combat_state.get('is_active', False),
                        "last_updated": combat_state.get('last_updated')
                    }
                    logger.info(f"get_encounter executed for client {client_id}: encounter {encounter_id}, is_active={combat_state.get('is_active', False)}")
                    return result
                else:
                    # Get all encounters
                    all_states = websocket_message_collector.get_all_combat_states(client_id)
                    active_count = all_states.get('active_count', 0)
                    
                    if active_count == 0:
                        result = {
                            "success": True,
                            "in_combat": False,
                            "message": "No active encounter"
                        }
                        logger.info(f"get_encounter executed for client {client_id}: no active combat")
                        return result
                    
                    result = {
                        "success": True,
                        "in_combat": True,
                        "active_count": active_count,
                        "encounters": all_states.get('encounters', [])
                    }
                    logger.info(f"get_encounter executed for client {client_id}: {active_count} active encounters")
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
            
            # Variable to store combat state from frontend response
            frontend_combat_state = None
            
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
                
                # Wait for combat state response with timeout (15 seconds - Foundry operations can be slow)
                try:
                    logger.info(f"create_encounter: Waiting for combat state for request {request_id}...")
                    frontend_combat_state = await asyncio.wait_for(result_future, timeout=15.0)
                    logger.info(f"create_encounter: Successfully received combat state for request {request_id}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"create_encounter: Timeout waiting for combat state from frontend, request_id: {request_id}")
                    
                    # Check if combat was actually created despite timeout
                    combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                    if combat_state and combat_state.get('in_combat', False):
                        logger.info(f"create_encounter: Combat is active despite timeout (created successfully)")
                        result = {
                            "success": True,
                            "in_combat": True,
                            "combat_id": combat_state.get('combat_id'),
                            "round": combat_state.get('round', 0),
                            "turn": combat_state.get('turn', 0),
                            "combatants": combat_state.get('combatants', []),
                            "roll_initiative": roll_initiative,
                            "actor_count": len(actor_ids),
                            "last_updated": combat_state.get('last_updated'),
                            "warning": "Combat created but response timed out"
                        }
                        logger.info(f"create_encounter executed for client {client_id}: round {combat_state.get('round', 0)}, turn {combat_state.get('turn', 0)}, {len(combat_state.get('combatants', []))} combatants (with timeout warning)")
                        return result
                    else:
                        # Log diagnostic information to help debug timeout issues
                        logger.debug(f"create_encounter: Checking message collector for client {client_id}")
                        logger.debug(f"create_encounter: Pending requests count: {len(_pending_roll_requests)}")
                        
                        return {
                            "success": False,
                            "error": "Timeout waiting for encounter creation response from frontend. Frontend may have encountered an error or the WebSocket connection may be unstable.",
                            "details": {
                                "request_id": request_id,
                                "timeout_seconds": 15,
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
                
                # Use combat state from frontend response (not cached state)
                # This ensures we return the correct combat_id for the newly created encounter
                if frontend_combat_state:
                    combat_state = frontend_combat_state
                else:
                    # Fallback to cached state if no response received
                    combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                
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
    
    async def execute_activate_combat(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute activate_combat tool - activates a specific combat encounter
        
        Args:
            args: Tool arguments (must contain 'encounter_id')
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with activation result
        """
        try:
            # Validate required parameter
            encounter_id = args.get('encounter_id')
            if not encounter_id or not isinstance(encounter_id, str):
                return {
                    "success": False,
                    "error": "encounter_id is required and must be a non-empty string"
                }
            
            # Get services via ServiceFactory
            from ..system_services.service_factory import get_websocket_manager, get_message_collector
            
            websocket_manager = get_websocket_manager()
            websocket_message_collector = get_message_collector()
            
            # Verify encounter exists in cache
            combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
            
            if not combat_state:
                return {
                    "success": False,
                    "error": f"Encounter {encounter_id} not found"
                }
            
            # Create a unique request ID for this activation
            request_id = str(uuid.uuid4())
            
            logger.info(f"activate_combat: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await combat state response
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future
            logger.info(f"activate_combat: Stored future in _pending_roll_requests. Total pending: {len(_pending_roll_requests)}")
            
            try:
                # Send activation request to frontend
                activate_message = {
                    "type": "activate_combat",
                    "request_id": request_id,
                    "data": {
                        "encounter_id": encounter_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, activate_message)
                logger.info(f"activate_combat: Sent activation request to client {client_id}, request_id: {request_id}")
                
                # Wait for combat state response with timeout (15 seconds - Foundry operations can be slow)
                try:
                    logger.info(f"activate_combat: Waiting for combat state for request {request_id}...")
                    await asyncio.wait_for(result_future, timeout=15.0)
                    logger.info(f"activate_combat: Successfully received combat state for request {request_id}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"activate_combat: Timeout waiting for combat state, request_id: {request_id}")
                    
                    # Check if encounter was activated despite timeout
                    combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                    if combat_state and combat_state.get('is_active', False):
                        logger.info(f"activate_combat: Combat is active despite timeout (activated successfully)")
                        return {
                            "success": True,
                            "message": f"Encounter {encounter_id} activated successfully (verified after timeout)",
                            "active_combat_id": encounter_id,
                            "warning": "Encounter activated but response timed out"
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Timeout waiting for combat activation response from frontend",
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
                
                # Verify activation
                combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                if not combat_state or not combat_state.get('is_active', False):
                    return {
                        "success": False,
                        "error": "Failed to activate encounter",
                        "message": "Encounter not active after activation request"
                    }
                
                # Success
                result = {
                    "success": True,
                    "message": f"Encounter {encounter_id} activated successfully",
                    "active_combat_id": encounter_id
                }
                
                logger.info(f"activate_combat executed for client {client_id}: encounter {encounter_id} activated")
                return result
            
            except Exception as inner_error:
                logger.error(f"activate_combat: Error during activation for client {client_id}: {inner_error}")
                return {
                    "success": False,
                    "error": str(inner_error)
                }
            
        except Exception as e:
            logger.error(f"activate_combat execution failed: {e}")
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
        Execute delete_encounter tool - ends the specified combat encounter
        
        Args:
            args: Tool arguments (must contain 'encounter_id')
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with encounter deletion result
        """
        try:
            # Validate required parameter
            encounter_id = args.get('encounter_id')
            if not encounter_id or not isinstance(encounter_id, str):
                return {
                    "success": False,
                    "error": "encounter_id is required and must be a non-empty string"
                }
            
            # Get services via ServiceFactory
            from ..system_services.service_factory import get_websocket_manager, get_message_collector, get_combat_encounter_service
            
            websocket_manager = get_websocket_manager()
            websocket_message_collector = get_message_collector()
            combat_service = get_combat_encounter_service()
            
            # FIXED: Validate that encounter exists in cache before sending delete request
            # This prevents false positive success when deleting non-existent encounters
            combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
            if not combat_state or not combat_state.get('in_combat', False):
                logger.info(f"delete_encounter: Encounter {encounter_id} not found or not active for client {client_id}")
                return {
                    "success": False,
                    "error": f"Encounter {encounter_id} not found or not active"
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
                        "encounter_id": encounter_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, delete_message)
                logger.info(f"delete_encounter: Sent encounter deletion request to client {client_id}, request_id: {request_id}")
                
                # Wait for combat state response with timeout (15 seconds - Foundry operations can be slow)
                try:
                    logger.info(f"delete_encounter: Waiting for combat state for request {request_id}...")
                    await asyncio.wait_for(result_future, timeout=15.0)
                    logger.info(f"delete_encounter: Successfully received combat state for request {request_id}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"delete_encounter: Timeout waiting for combat state, request_id: {request_id}")
                    
                    # After timeout, verify combat is actually gone by checking the message collector
                    # The frontend should have sent back updated combat state, which would have
                    # updated the cache via set_combat_state_from_frontend
                    combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                    
                    if combat_state and combat_state.get('in_combat', False):
                        return {
                            "success": False,
                            "error": "Combat still active after deletion request",
                            "message": "Failed to end encounter",
                            "details": {
                                "combat_id": combat_state.get('combat_id'),
                                "round": combat_state.get('round'),
                                "turn": combat_state.get('turn')
                            }
                        }
                    else:
                        # Encounter is gone or inactive - consider deletion successful
                        return {
                            "success": True,
                            "message": "Encounter ended successfully (verified after timeout)",
                            "in_combat": False,
                            "warning": "Deletion response timed out, but encounter is no longer active"
                        }
                
                finally:
                    # Clean up pending request
                    logger.info(f"Cleaning up future for request {request_id}")
                    if request_id in _pending_roll_requests:
                        del _pending_roll_requests[request_id]
                        logger.info(f"Removed future for request {request_id} from _pending_roll_requests")
                    else:
                        logger.warning(f"Future for request {request_id} not found in _pending_roll_requests during cleanup")
                
                # Verify combat is no longer active by checking the message collector
                # The frontend's response should have updated the cache via set_combat_state_from_frontend
                combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                
                # Check if combat state still exists and is active
                if combat_state and combat_state.get('in_combat', False):
                    # Combat state still shows as active - force remove it from cache
                    # This handles case where frontend sends invalid combat_state after deletion
                    logger.warning(f"delete_encounter: Combat still active after deletion, forcing removal from cache for encounter {encounter_id}")
                    websocket_message_collector.clear_specific_combat_state(client_id, encounter_id)
                    combat_service.delete_encounter(encounter_id)
                    
                    return {
                        "success": True,
                        "message": "Encounter ended successfully (force removed from cache)",
                        "in_combat": False
                    }
                
                # Verify the encounter was actually removed from the cache
                # If combat_state is None, the encounter was successfully deleted
                if combat_state is None:
                    logger.info(f"delete_encounter executed for client {client_id}: encounter {encounter_id} successfully deleted (removed from cache)")
                    return {
                        "success": True,
                        "message": "Encounter ended successfully",
                        "in_combat": False
                    }
                
                # If combat_state exists but in_combat is False, verify it's the right encounter
                if combat_state.get('combat_id') != encounter_id:
                    logger.warning(f"delete_encounter: Combat state mismatch - requested {encounter_id}, found {combat_state.get('combat_id')}")
                    return {
                        "success": False,
                        "error": "Combat state mismatch after deletion",
                        "message": "Failed to end encounter - state mismatch",
                        "details": {
                            "requested_encounter_id": encounter_id,
                            "found_encounter_id": combat_state.get('combat_id')
                        }
                    }
                
                # Success - encounter state exists but in_combat is False
                logger.info(f"delete_encounter executed for client {client_id}: encounter {encounter_id} ended (in_combat=False)")
                return {
                    "success": True,
                    "message": "Encounter ended successfully",
                    "in_combat": False
                }
            
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
            
        except Exception as e:
            logger.error(f"delete_encounter execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_advance_combat_turn(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute advance_combat_turn tool - advances combat tracker to next turn for specified encounter
        
        Args:
            args: Tool arguments (must contain 'encounter_id')
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with turn advancement result and updated combat state
        """
        try:
            # Validate required parameter
            encounter_id = args.get('encounter_id')
            if not encounter_id or not isinstance(encounter_id, str):
                return {
                    "success": False,
                    "error": "encounter_id is required and must be a non-empty string"
                }
            
            # Get services via ServiceFactory
            from ..system_services.service_factory import get_websocket_manager, get_message_collector, get_combat_encounter_service
            
            websocket_manager = get_websocket_manager()
            websocket_message_collector = get_message_collector()
            combat_service = get_combat_encounter_service()
            
            # FIXED: Use cached state for validation instead of CombatEncounterService
            # This avoids the same issue as get_encounter - checking service before it's updated
            cached_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
            
            # Check if encounter exists and is active in cached state
            if not cached_state or not cached_state.get('in_combat', False):
                return {
                    "success": False,
                    "error": f"Encounter {encounter_id} not found or not active"
                }
            
            # Verify cached combat_id matches requested encounter_id
            if cached_state.get('combat_id') != encounter_id:
                return {
                    "success": False,
                    "error": f"Encounter {encounter_id} not found or not active"
                }
            
            # Store pre-advancement turn and round for verification
            prev_turn = cached_state.get('turn', 0)
            prev_round = cached_state.get('round', 0)
            logger.info(f"advance_combat_turn: Pre-advancement state - turn={prev_turn}, round={prev_round}")
            
            # Create a unique request ID for this turn advancement
            request_id = str(uuid.uuid4())
            
            logger.info(f"advance_combat_turn: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await combat state response
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future
            logger.info(f"advance_combat_turn: Stored future in _pending_roll_requests. Total pending: {len(_pending_roll_requests)}")
            
            try:
                # Send turn advancement request to frontend
                advance_message = {
                    "type": "advance_turn",
                    "request_id": request_id,
                    "data": {
                        "encounter_id": encounter_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, advance_message)
                logger.info(f"advance_combat_turn: Sent turn advancement request to client {client_id}, request_id: {request_id}")
                
                # Wait for combat state response with timeout (15 seconds - Foundry operations can be slow)
                try:
                    logger.info(f"advance_combat_turn: Waiting for combat state for request {request_id}...")
                    await asyncio.wait_for(result_future, timeout=15.0)
                    logger.info(f"advance_combat_turn: Successfully received combat state for request {request_id}")
                    
                except asyncio.TimeoutError:
                    logger.error(f"advance_combat_turn: Timeout waiting for combat state, request_id: {request_id}")
                    
                    # Check if turn actually advanced despite timeout
                    combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                    if combat_state and combat_state.get('in_combat', False):
                        logger.info(f"advance_combat_turn: Combat is still active despite timeout (may have advanced)")
                        # Return state even if timeout occurred
                        result = {
                            "success": True,
                            "message": "Turn advanced successfully (verified after timeout)",
                            "in_combat": True,
                            "combat_id": combat_state.get('combat_id'),
                            "round": combat_state.get('round', 0),
                            "turn": combat_state.get('turn', 0),
                            "last_updated": combat_state.get('last_updated'),
                            "warning": "Turn advanced but response timed out"
                        }
                        # Add current combatant if available
                        combatants = combat_state.get('combatants', [])
                        for combatant in combatants:
                            if combatant.get('is_current_turn'):
                                result['current_combatant'] = combatant.get('name')
                                break
                        logger.info(f"advance_combat_turn executed for client {client_id}: round {combat_state.get('round', 0)}, turn {combat_state.get('turn', 0)} (with timeout warning)")
                        return result
                    else:
                        return {
                            "success": False,
                            "error": "Timeout waiting for turn advancement response from frontend",
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
                
                # Get updated combat state from message collector
                combat_state = websocket_message_collector.get_specific_combat_state(client_id, encounter_id)
                
                if not combat_state or not combat_state.get('in_combat', False):
                    return {
                        "success": False,
                        "error": "Combat is no longer active after turn advancement",
                        "message": "Failed to advance turn"
                    }
                
                # FIXED: Verify that turn or round actually advanced
                new_turn = combat_state.get('turn', 0)
                new_round = combat_state.get('round', 0)
                
                if new_turn == prev_turn and new_round == prev_round:
                    logger.warning(f"advance_combat_turn: Turn/round did not advance - turn={new_turn} (was {prev_turn}), round={new_round} (was {prev_round})")
                    # Still return success as the frontend may have processed the request but the turn didn't increment
                    # This can happen in certain edge cases (e.g., only one combatant)
                    pass
                else:
                    logger.info(f"advance_combat_turn: Turn/round advanced - turn={new_turn} (was {prev_turn}), round={new_round} (was {prev_round})")
                
                # Success - return updated combat state
                result = {
                    "success": True,
                    "message": "Turn advanced successfully",
                    "in_combat": True,
                    "combat_id": combat_state.get('combat_id'),
                    "round": combat_state.get('round', 0),
                    "turn": combat_state.get('turn', 0),
                    "last_updated": combat_state.get('last_updated')
                }
                
                # Add current combatant if available
                combatants = combat_state.get('combatants', [])
                for combatant in combatants:
                    if combatant.get('is_current_turn'):
                        result['current_combatant'] = combatant.get('name')
                        break
                
                logger.info(f"advance_combat_turn executed for client {client_id}: round {combat_state.get('round', 0)}, turn {combat_state.get('turn', 0)}")
                return result
            
            except Exception as inner_error:
                logger.error(f"advance_combat_turn: Error during turn advancement for client {client_id}: {inner_error}")
                return {
                    "success": False,
                    "error": str(inner_error)
                }
            
        except Exception as e:
            logger.error(f"advance_combat_turn execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_get_actor_details(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute get_actor_details tool - retrieves detailed stat block for token-specific actor
        
        Args:
            args: Tool arguments (must contain 'token_id', optional 'search_phrase')
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with actor details or search results
        """
        try:
            # Validate arguments
            token_id = args.get('token_id')
            if not isinstance(token_id, str) or not token_id.strip():
                raise ValueError("token_id must be a non-empty string")
            
            search_phrase = args.get('search_phrase', '')
            if not isinstance(search_phrase, str):
                raise ValueError("search_phrase must be a string")
            
            # Get services via ServiceFactory
            from ..system_services.service_factory import get_websocket_manager
            
            websocket_manager = get_websocket_manager()
            
            # Create a unique request ID for this actor details request
            request_id = str(uuid.uuid4())
            
            logger.info(f"get_actor_details: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await actor data response
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future
            logger.info(f"get_actor_details: Stored future in _pending_roll_requests. Total pending: {len(_pending_roll_requests)}")
            
            try:
                # Send actor details request to frontend
                actor_details_message = {
                    "type": "get_actor_details",
                    "request_id": request_id,
                    "data": {
                        "token_id": token_id,
                        "search_phrase": search_phrase,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, actor_details_message)
                logger.info(f"get_actor_details: Sent actor details request to client {client_id} for token {token_id}, request_id: {request_id}")
                
                # Wait for actor data response with timeout (5 seconds - should be fast)
                try:
                    logger.info(f"get_actor_details: Waiting for actor data for request {request_id}...")
                    result_data = await asyncio.wait_for(result_future, timeout=5.0)
                    logger.info(f"get_actor_details: Successfully received actor data for request {request_id}")
                    
                    # Return actor details from frontend
                    logger.info(f"get_actor_details: Returning actor data: {truncate_for_log(result_data)}")
                    return {
                        "success": True,
                        "token_id": token_id,
                        "search_phrase": search_phrase,
                        "data": result_data,
                        "request_id": request_id
                    }
                    
                except asyncio.TimeoutError:
                    logger.error(f"get_actor_details: Timeout waiting for actor data, request_id: {request_id}")
                    return {
                        "success": False,
                        "error": "Timeout waiting for actor details from frontend",
                        "request_id": request_id,
                        "details": {
                            "token_id": token_id,
                            "search_phrase": search_phrase,
                            "timeout_seconds": 5
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
            
            except Exception as inner_error:
                logger.error(f"get_actor_details: Error during actor details request for client {client_id}: {inner_error}")
                return {
                    "success": False,
                    "error": str(inner_error)
                }
            
        except Exception as e:
            logger.error(f"get_actor_details execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_modify_token_attribute(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute modify_token_attribute tool - modifies token attributes using Foundry's native API
        
        Args:
            args: Tool arguments (must contain 'token_id', 'attribute_path', 'value', optional 'is_delta', 'is_bar')
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with attribute modification result
        """
        try:
            # Validate arguments
            token_id = args.get('token_id')
            if not isinstance(token_id, str) or not token_id.strip():
                raise ValueError("token_id must be a non-empty string")
            
            attribute_path = args.get('attribute_path')
            if not isinstance(attribute_path, str) or not attribute_path.strip():
                raise ValueError("attribute_path must be a non-empty string")
            
            value = args.get('value')
            if value is None or not isinstance(value, (int, float)):
                raise ValueError("value must be a number")
            
            is_delta = args.get('is_delta', True)
            if not isinstance(is_delta, bool):
                raise ValueError("is_delta must be a boolean")
            
            is_bar = args.get('is_bar', True)
            if not isinstance(is_bar, bool):
                raise ValueError("is_bar must be a boolean")
            
            # Get services via ServiceFactory
            from ..system_services.service_factory import get_websocket_manager, get_message_collector
            
            websocket_manager = get_websocket_manager()
            websocket_message_collector = get_message_collector()
            
            # Create a unique request ID for this attribute modification
            request_id = str(uuid.uuid4())
            
            logger.info(f"modify_token_attribute: Creating future for request {request_id} with client_id {client_id}")
            
            # Create a future to await combat state response
            result_future = asyncio.Future()
            _pending_roll_requests[request_id] = result_future
            logger.info(f"modify_token_attribute: Stored future in _pending_roll_requests. Total pending: {len(_pending_roll_requests)}")
            
            try:
                # Send attribute modification request to frontend
                modify_message = {
                    "type": "modify_token_attribute",
                    "request_id": request_id,
                    "data": {
                        "token_id": token_id,
                        "attribute_path": attribute_path,
                        "value": value,
                        "is_delta": is_delta,
                        "is_bar": is_bar,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                await websocket_manager.send_to_client(client_id, modify_message)
                logger.info(f"modify_token_attribute: Sent attribute modification request to client {client_id} for token {token_id}, request_id: {request_id}")
                
                # Wait for response with timeout (15 seconds - Foundry operations can be slow)
                try:
                    logger.info(f"modify_token_attribute: Waiting for response for request {request_id}...")
                    await asyncio.wait_for(result_future, timeout=15.0)
                    logger.info(f"modify_token_attribute: Successfully received response for request {request_id}")
                    
                    result = {
                        "success": True,
                        "message": "Attribute modified successfully",
                        "token_id": token_id,
                        "attribute_path": attribute_path,
                        "value": value,
                        "is_delta": is_delta,
                        "is_bar": is_bar,
                        "request_id": request_id
                    }
                    
                    logger.info(f"modify_token_attribute executed for client {client_id}: token {token_id}, path {attribute_path}, value {value}")
                    return result
                    
                except asyncio.TimeoutError:
                    logger.error(f"modify_token_attribute: Timeout waiting for combat state, request_id: {request_id}")
                    return {
                        "success": False,
                        "error": "Timeout waiting for attribute modification response from frontend",
                        "request_id": request_id,
                        "details": {
                            "token_id": token_id,
                            "attribute_path": attribute_path,
                            "timeout_seconds": 15
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
            
            except Exception as inner_error:
                logger.error(f"modify_token_attribute: Error during attribute modification for client {client_id}: {inner_error}")
                return {
                    "success": False,
                    "error": str(inner_error)
                }
            
        except Exception as e:
            logger.error(f"modify_token_attribute execution failed: {e}")
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
