#!/usr/bin/env python3
"""
AI Tool Executor for The Gold Box
Executes AI tools with proper separation of concerns
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

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
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def execute_get_message_history(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute get_message_history tool - returns compact JSON format (same as non-tool AI chat)
        
        Args:
            args: Tool arguments (must contain 'limit')
            client_id: Client ID for message collection
        
        Returns:
            Dict with compact JSON messages (token-efficient format)
        """
        try:
            # Validate arguments
            limit = args.get('limit', 15)
            if not isinstance(limit, int) or limit < 1 or limit > 50:
                raise ValueError("limit must be an integer between 1 and 50")
            
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
                limit,
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
    
    async def execute_post_message(
        self,
        args: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute post_message tool - with dice-roll detection
        
        Args:
            args: Tool arguments (must contain 'content')
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with success status
        """
        try:
            # Validate arguments
            content = args.get('content', '')
            if not content:
                raise ValueError("content is required")
            
            # Check if content is a dice roll (AI trying to create roll via post_message)
            # Pattern detection: dice formulas, roll keywords, etc.
            import re
            dice_pattern = r'\d+d\d+[\+\-]\d+|\d+d\d+'
            
            is_dice_roll = re.search(dice_pattern, content) is not None
            is_roll_keyword = any(keyword in content.lower() for keyword in ['roll ', 'rolls', 'attack roll', 'damage'])
            
            if is_dice_roll or is_roll_keyword:
                # AI is trying to create a dice roll - translate to roll_dice call
                logger.warning(f"AI attempting dice roll via post_message, translating to roll_dice")
                
                # Extract formula from content
                formula_match = re.search(r'(\d+d\d+[\+\-]\d+|\d+d\d+)', content)
                if formula_match:
                    formula = formula_match.group(1)
                    flavor = content.replace(formula, '').strip()
                    
                    # Call roll_dice instead
                    return await self.execute_roll_dice(
                        {'rolls': [{'formula': formula, 'flavor': flavor}]},
                        client_id
                    )
            
            # Get services via ServiceFactory (single source of truth)
            from ..system_services.service_factory import get_websocket_manager
            from shared.core.unified_message_processor import get_unified_processor
            
            websocket_manager = get_websocket_manager()
            unified_processor = get_unified_processor()
            
            # Build message object
            msg_data = {
                'content': content,
                'type': args.get('type', 'chat-message')
            }
            
            # Add optional fields
            if 'speaker_name' in args:
                msg_data['author'] = {'name': args['speaker_name']}
            if 'flavor' in args:
                msg_data['flavor'] = args['flavor']
            
            # Ensure message has a type field
            if 'type' not in msg_data:
                msg_data['type'] = 'chat-message'
            
            # Send via WebSocket to frontend
            ws_message = {
                "type": "chat_response",
                "data": {
                    "message": msg_data,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            success = await websocket_manager.send_to_client(client_id, ws_message)
            
            logger.info(f"post_message executed: {'success' if success else 'failed'} for client {client_id}")
            
            return {
                "success": success
            }
            
        except Exception as e:
            logger.error(f"post_message execution failed: {e}")
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
        Execute roll_dice tool - requests dice rolls from frontend
        
        Args:
            args: Tool arguments (must contain 'rolls' array)
            client_id: Client ID for WebSocket communication
        
        Returns:
            Dict with pending roll status (results come back via frontend)
        """
        try:
            # Validate arguments
            rolls = args.get('rolls', [])
            if not isinstance(rolls, list) or not rolls:
                raise ValueError("rolls must be a non-empty array")
            
            for roll in rolls:
                if not isinstance(roll, dict) or 'formula' not in roll:
                    raise ValueError("Each roll must be a dict with 'formula' field")
            
            # Get WebSocket manager
            from ..system_services.service_factory import get_websocket_manager
            websocket_manager = get_websocket_manager()
            
            # Send dice roll requests to frontend
            results = []
            for roll in rolls:
                formula = roll.get('formula', '')
                flavor = roll.get('flavor', '')
                
                ws_message = {
                    "type": "dice_roll_request",
                    "data": {
                        "formula": formula,
                        "flavor": flavor,
                        "timestamp": datetime.now().isoformat()
                    }
                }
                
                success = await websocket_manager.send_to_client(client_id, ws_message)
                results.append({
                    "formula": formula,
                    "success": success
                })
            
            logger.info(f"roll_dice executed: {len(results)} dice roll requests sent to frontend for client {client_id}")
            
            return {
                "success": True,
                "message": f"Dice roll requests sent. Results will be available in next chat context.",
                "requests": results
            }
            
        except Exception as e:
            logger.error(f"roll_dice execution failed: {e}")
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
        Execute get_encounter tool - retrieves current combat state
        
        Args:
            args: Tool arguments (none required)
            client_id: Client ID for context (not used but kept for consistency)
        
        Returns:
            Dict with combat state or 'no active encounter' message
        """
        try:
            # Get combat encounter service
            from ..system_services.service_factory import get_combat_encounter_service
            combat_service = get_combat_encounter_service()
            
            # Get current combat context
            combat_context = combat_service.get_combat_context()
            
            # Check if combat is active
            if combat_context.get('in_combat', False):
                # Combat is active - return full encounter data
                encounter_data = {
                    "success": True,
                    "in_combat": True,
                    "encounter_id": combat_context.get('combat_id'),
                    "round": combat_context.get('round', 0),
                    "turn": combat_context.get('turn', 0),
                    "combatants": combat_context.get('combatants', []),
                    "current_turn_actor": combat_context.get('current_turn_actor')
                }
                
                logger.info(f"get_encounter: Active encounter {encounter_data['encounter_id']}, Round {encounter_data['round']}, Turn {encounter_data['turn']}")
                
                return encounter_data
            else:
                # No active encounter
                logger.info("get_encounter: No active encounter")
                
                return {
                    "success": True,
                    "in_combat": False,
                    "message": "No active encounter"
                }
            
        except Exception as e:
            logger.error(f"get_encounter execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
def get_ai_tool_executor() -> AIToolExecutor:
    """Get AI tool executor instance"""
    return AIToolExecutor()
