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
def get_ai_tool_executor() -> AIToolExecutor:
    """Get AI tool executor instance"""
    return AIToolExecutor()
