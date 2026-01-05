#!/usr/bin/env python3
"""
AI Orchestrator for The Gold Box
Manages function calling workflow - coordinates between AI service and tool execution
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    Orchestrates function calling workflow
    
    Responsibilities:
    - Manage function call loop
    - Decide when to call AI vs execute tools
    - Handle max iterations and continuation
    - Coordinate with AISessionManager for conversation history
    """
    
    def __init__(self):
        """
        Initialize AI orchestrator - services accessed lazily when needed
        
        Uses ServiceFactory pattern for consistent service access:
        - AI service via get_ai_service()
        - Tool executor via get_ai_tool_executor()
        
        Note: Services are resolved lazily to avoid circular dependencies
        during startup initialization
        """
        # Services resolved lazily to avoid startup circular dependencies
        self._ai_service = None
        self._tool_executor = None
    
    def _get_ai_service(self):
        """Lazy load AI service"""
        if self._ai_service is None:
            from ..system_services.service_factory import get_ai_service
            self._ai_service = get_ai_service()
        return self._ai_service
    
    def _get_tool_executor(self):
        """Lazy load tool executor"""
        if self._tool_executor is None:
            from ..system_services.service_factory import get_ai_tool_executor
            self._tool_executor = get_ai_tool_executor()
        return self._tool_executor
    
    async def execute_function_call_loop(
        self,
        initial_messages: List[Dict[str, str]],
        tools: List[Dict],
        config: Dict[str, Any],
        session_id: str,
        client_id: str,
        max_iterations: int = 10
    ) -> Dict[str, Any]:
        """
        Execute function call loop until AI signals completion
        
        Args:
            initial_messages: Starting conversation (system + user prompt)
            tools: Tool definitions for AI (OpenAI format)
            config: Provider configuration
            session_id: Session ID for conversation history storage
            client_id: Client ID for message collection (transient, from WebSocket)
            max_iterations: Maximum tool call iterations (safety limit)
        
        Returns:
            Final AI response when complete
        """
        from ..ai_services.ai_session_manager import get_ai_session_manager
        from ..message_services.websocket_message_collector import get_websocket_message_collector
        from ..system_services.service_factory import get_context_builder
        import json
        
        ai_session_manager = get_ai_session_manager()
        collector = get_websocket_message_collector()
        context_builder = get_context_builder()
        
        # Check if this is first turn for this session
        is_first_turn = not ai_session_manager.is_first_turn_complete(session_id)
        
        # Request fresh world state from frontend on first turn
        if is_first_turn:
            try:
                # Get websocket manager from ServiceRegistry
                from ..system_services.service_factory import get_service_registry
                registry = get_service_registry()
                websocket_manager = registry.get('websocket_manager')
                
                if websocket_manager:
                    # Send world state refresh request
                    await websocket_manager.send_to_client(client_id, {
                        "type": "world_state_refresh",
                        "data": {},
                        "timestamp": time.time()
                    })
                    
                    # Brief pause to allow frontend to respond
                    import asyncio
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error requesting world state refresh: {e}")
        
        # Clear delta after determining first turn status
        # The shared utility will handle context injection based on is_first_turn
        game_delta = collector.get_game_delta(client_id)
        if game_delta:
            collector.clear_game_delta(client_id)
        
        # Use initial_messages as-is (shared utility will inject context/delta)
        conversation = initial_messages.copy()
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call AI with current conversation
            ai_service = self._get_ai_service()
            response_data = await ai_service.call_ai_provider(
                messages=conversation,
                config=config,
                tools=tools
            )
            
            # Check if AI made tool calls
            if response_data.get('has_tool_calls'):
                tool_calls = response_data['tool_calls']
                
                # Build assistant message with tool_calls (OpenAI format)
                assistant_message = {
                    "role": "assistant",
                    "content": response_data.get('response', ''),
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in tool_calls
                    ]
                }
                
                # Append to in-memory conversation
                conversation.append(assistant_message)
                
                # Store in session using existing method
                ai_session_manager.add_conversation_message(session_id, assistant_message)
                
                # Execute each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool with explicit client_id
                    tool_executor = self._get_tool_executor()
                    tool_result = await tool_executor.execute_tool(
                        tool_name, 
                        tool_args, 
                        client_id
                    )
                    
                    # Build tool result message (OpenAI format)
                    tool_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    }
                    
                    # Append to in-memory conversation
                    conversation.append(tool_result_message)
                    
                    # Store in session using existing method
                    ai_session_manager.add_conversation_message(session_id, tool_result_message)
                
                # Continue loop (AI will see tool results and make next decision)
                continue
            
            # No tool calls - AI is done
            
            # Build final assistant message
            final_message = {
                "role": "assistant",
                "content": response_data.get('response', '')
            }
            
            # Append to in-memory conversation
            conversation.append(final_message)
            
            # Store in session using existing method
            ai_session_manager.add_conversation_message(session_id, final_message)
            
            # Mark first turn as complete if this was the first turn
            if is_first_turn:
                ai_session_manager.set_first_turn_complete(session_id)
            
            return {
                'success': True,
                'response': response_data.get('response', ''),
                'iterations': iteration,
                'tokens_used': response_data.get('tokens_used', 0),
                'complete': True  # Signal that AI turn is complete
            }
        
        # Max iterations reached - execute current tool calls, then pause
        
        # Execute remaining tool calls in this iteration (don't lose work)
        if response_data.get('has_tool_calls'):
            tool_calls = response_data['tool_calls']
            
            # Build assistant message with tool_calls
            assistant_message = {
                "role": "assistant",
                "content": response_data.get('response', ''),
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            }
            
            # Append to in-memory conversation
            conversation.append(assistant_message)
            
            # Store in session
            ai_session_manager.add_conversation_message(session_id, assistant_message)
            
            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # Execute tool with explicit client_id
                tool_executor = self._get_tool_executor()
                tool_result = await tool_executor.execute_tool(
                    tool_name, 
                    tool_args, 
                    client_id
                )
                
                # Build tool result message
                tool_result_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                }
                
                # Append to in-memory conversation
                conversation.append(tool_result_message)
                
                # Store in session
                ai_session_manager.add_conversation_message(session_id, tool_result_message)
        
        # Store paused state for potential resume
        paused_state = {
            'conversation': conversation,
            'iterations': iteration,
            'tokens_used': response_data.get('tokens_used', 0),
            'config': config,
            'tools': tools,
            'max_iterations': max_iterations
        }
        ai_session_manager.pause_conversation(session_id, paused_state)
        
        # Return partial success - allow continuation
        return {
            'success': True,
            'partial': True,
            'reached_limit': True,
            'response': '',
            'iterations': iteration,
            'tokens_used': response_data.get('tokens_used', 0)
        }
    
    async def resume_function_call_loop(
        self,
        session_id: str,
        client_id: str
    ) -> Dict[str, Any]:
        """
        Resume a paused function call loop
        
        Args:
            session_id: Session ID for conversation history storage
            client_id: Client ID for message collection (transient, from WebSocket)
        
        Returns:
            Final AI response when complete
        """
        from ..ai_services.ai_session_manager import get_ai_session_manager
        from ..message_services.websocket_message_collector import get_websocket_message_collector
        from ..system_services.service_factory import get_context_builder
        import json
        
        ai_session_manager = get_ai_session_manager()
        
        # Get paused conversation state
        paused_state = ai_session_manager.get_paused_conversation(session_id)
        if not paused_state:
            return {
                'success': False,
                'error': 'No paused conversation found or it has expired'
            }
        
        # Mark as resumed
        ai_session_manager.resume_conversation(session_id)
        
        # Restore conversation state
        conversation = paused_state.get('conversation', [])
        iteration = paused_state.get('iterations', 0)
        
        # Get services needed for continuation
        from ..ai_services.ai_session_manager import get_ai_session_manager as get_ai_session
        ai_session = get_ai_session()
        collector = get_websocket_message_collector()
        
        # Get provider config from paused state
        config = paused_state.get('config', {})
        tools = paused_state.get('tools', [])
        max_iterations = paused_state.get('max_iterations', 20)
        
        # Continue loop
        while iteration < max_iterations:
            iteration += 1
            
            # Call AI with current conversation
            ai_service = self._get_ai_service()
            response_data = await ai_service.call_ai_provider(
                messages=conversation,
                config=config,
                tools=tools
            )
            
            # Check if AI made tool calls
            if response_data.get('has_tool_calls'):
                tool_calls = response_data['tool_calls']
                
                # Build assistant message with tool_calls (OpenAI format)
                assistant_message = {
                    "role": "assistant",
                    "content": response_data.get('response', ''),
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in tool_calls
                    ]
                }
                
                # Append to in-memory conversation
                conversation.append(assistant_message)
                
                # Store in session using existing method
                ai_session_manager.add_conversation_message(session_id, assistant_message)
                
                # Execute each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool with explicit client_id
                    tool_executor = self._get_tool_executor()
                    tool_result = await tool_executor.execute_tool(
                        tool_name, 
                        tool_args, 
                        client_id
                    )
                    
                    # Build tool result message (OpenAI format)
                    tool_result_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    }
                    
                    # Append to in-memory conversation
                    conversation.append(tool_result_message)
                    
                    # Store in session using existing method
                    ai_session_manager.add_conversation_message(session_id, tool_result_message)
                
                # Continue loop (AI will see tool results and make next decision)
                continue
            
            # No tool calls - AI is done
            
            # Build final assistant message
            final_message = {
                "role": "assistant",
                "content": response_data.get('response', '')
            }
            
            # Append to in-memory conversation
            conversation.append(final_message)
            
            # Store in session using existing method
            ai_session_manager.add_conversation_message(session_id, final_message)
            
            return {
                'success': True,
                'response': response_data.get('response', ''),
                'iterations': iteration,
                'tokens_used': response_data.get('tokens_used', 0),
                'complete': True  # Signal that AI turn is complete
            }
        
        # Max iterations reached again - pause again
        # Store paused state for potential resume
        paused_state = {
            'conversation': conversation,
            'iterations': iteration,
            'tokens_used': response_data.get('tokens_used', 0),
            'config': config,
            'tools': tools,
            'max_iterations': max_iterations
        }
        ai_session_manager.pause_conversation(session_id, paused_state)
        
        # Return partial success - allow continuation
        return {
            'success': True,
            'partial': True,
            'reached_limit': True,
            'response': '',
            'iterations': iteration,
            'tokens_used': response_data.get('tokens_used', 0)
        }

def get_ai_orchestrator() -> AIOrchestrator:
    """
    Get AI orchestrator from ServiceRegistry
    
    Returns:
        AIOrchestrator instance from ServiceRegistry
        
    Raises:
        RuntimeError: If ServiceRegistry is not ready or ai_orchestrator is not registered
    """
    from ..system_services.service_factory import get_ai_service, get_ai_tool_executor
    return AIOrchestrator()
