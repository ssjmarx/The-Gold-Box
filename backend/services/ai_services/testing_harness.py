#!/usr/bin/env python3
"""
Testing Harness for The Gold Box
Acts as a "mock AI service" during testing
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List

from shared.core.unified_message_processor import get_unified_processor

logger = logging.getLogger(__name__)

class TestingHarness:
    """
    Acts as the "mock AI service" during testing
    
    Responsibilities:
    - Generate initial prompts (same format as real AI would receive)
    - Process user commands and convert to AI responses
    - Execute tools and return results
    - Handle function calling loop in test mode
    - Maintain conversation history for test sessions
    - Return responses in same format as real AI service
    """
    
    def __init__(self):
        """Initialize testing harness"""
        self._unified_processor = get_unified_processor()
        logger.info("TestingHarness initialized")
    
    async def generate_initial_prompt(
        self,
        client_id: str,
        universal_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate initial prompt (same format as real AI would receive)
        
        Uses shared utility to ensure consistency with production code.
        
        Args:
            client_id: The Foundry client ID
            universal_settings: Settings from frontend
            
        Returns:
            Dictionary with initial_prompt and session data
        """
        try:
            # Retrieve game delta from WebSocketMessageCollector
            # We need to wait for the delta because chat_request is processed asynchronously
            from services.message_services.websocket_message_collector import get_websocket_message_collector
            message_collector = get_websocket_message_collector()
            
            # DEBUG: Log delta retrieval
            logger.info(f"===== TESTING HARNESS DELTA RETRIEVAL =====")
            logger.info(f"generate_initial_prompt called for client {client_id}")
            
            # Wait for delta to be available (chat_request is processed as background task)
            # Poll for up to 3 seconds to get the delta from the latest chat_request
            max_wait_seconds = 3
            poll_interval = 0.1  # 100ms
            waited_seconds = 0
            
            game_delta = message_collector.get_game_delta(client_id)
            
            while not game_delta or (game_delta.get('hasChanges') == False and waited_seconds < max_wait_seconds):
                await asyncio.sleep(poll_interval)
                waited_seconds += poll_interval
                game_delta = message_collector.get_game_delta(client_id)
                
                if game_delta and game_delta.get('hasChanges') == True:
                    logger.info(f"Found delta with hasChanges=True after {waited_seconds:.1f}s")
                    break
            
            logger.info(f"Retrieved game_delta from collector after {waited_seconds:.1f}s: {json.dumps(game_delta, indent=2) if game_delta else 'None'}")
            
            # Update universal_settings with fresh delta
            if game_delta:
                universal_settings['message_delta'] = game_delta
                logger.info(f"Updated universal_settings with game_delta: hasChanges={game_delta.get('hasChanges', False)}")
            else:
                # No delta available - ensure we have default
                if 'message_delta' not in universal_settings:
                    universal_settings['message_delta'] = {'hasChanges': False}
                    logger.info(f"No game_delta available, using default: hasChanges=False")
            
            logger.info(f"universal_settings keys: {list(universal_settings.keys())}")
            message_delta = universal_settings.get('message_delta', {})
            logger.info(f"message_delta from universal_settings: {json.dumps(message_delta, indent=2)}")
            logger.info(f"message_delta hasChanges: {message_delta.get('hasChanges', 'NOT SET')}")
            logger.info(f"===== END TESTING HARNESS DELTA RETRIEVAL =====")
            # Get combat context
            combat_context = self._get_combat_context()
            
            # Build combat context message
            combat_context_message = {
                'type': 'combat_context',
                'combat_context': combat_context
            }
            
            # Generate system prompt based on AI role
            ai_role = universal_settings.get('ai role', 'gm')
            system_prompt = self._unified_processor.generate_enhanced_system_prompt(
                ai_role,
                [combat_context_message]
            )
            
            # Use shared utility for consistent delta injection
            # This ensures testing harness uses exact same logic as production
            from shared.utils.ai_prompt_builder import build_initial_messages_with_delta
            
            initial_messages = build_initial_messages_with_delta(
                universal_settings=universal_settings,
                system_prompt=system_prompt
            )
            
            # Extract initial_prompt from the messages array
            initial_prompt = initial_messages[0]['content']
            
            # Get delta from settings for return value
            message_delta = universal_settings.get('message_delta', {})
            
            return {
                'success': True,
                'initial_prompt': initial_prompt,
                'ai_role': ai_role,
                'combat_context': combat_context,
                'message_delta': message_delta
            }
            
        except Exception as e:
            logger.error(f"Error generating initial prompt: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_command(
        self,
        test_session_id: str,
        command_string: str,
        client_id: str,
        testing_session_manager,
        testing_command_processor
    ) -> Dict[str, Any]:
        """
        Process user command during testing
        
        Args:
            test_session_id: The test session ID
            command_string: Raw command from user
            client_id: The Foundry client ID
            testing_session_manager: TestingSessionManager instance
            testing_command_processor: TestingCommandProcessor instance
            
        Returns:
            Response dictionary
        """
        # Parse command
        parsed_command = testing_command_processor.parse_command(command_string)
        
        if not parsed_command:
            return {
                'success': False,
                'error': 'Unable to parse command'
            }
        
        # Validate command
        is_valid, error_msg = testing_command_processor.validate_command(parsed_command)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg
            }
        
        # Get command type
        command = parsed_command.get('command')
        
        # Handle special commands
        if command == 'stop':
            return self._handle_stop_command(test_session_id, testing_session_manager)
        
        elif command == 'status':
            return self._handle_status_command(test_session_id, testing_session_manager)
        
        elif command == 'help':
            return {
                'success': True,
                'help': testing_command_processor.get_command_help()
            }
        
        # Handle tool calls
        elif command in ['get_message_history', 'post', 'post_message', 'tool_call']:
            return await self._handle_tool_call(
                test_session_id,
                parsed_command,
                client_id,
                testing_session_manager,
                testing_command_processor
            )
        
        else:
            return {
                'success': False,
                'error': f'Unknown command: {command}'
            }
    
    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        client_id: str
    ) -> Dict[str, Any]:
        """
        Execute an AI tool call
        
        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments
            client_id: The Foundry client ID
            
        Returns:
            Tool result dictionary
        """
        try:
            # Get tool executor
            from services.system_services.service_factory import get_ai_tool_executor
            tool_executor = get_ai_tool_executor()
            
            # Execute tool
            result = await tool_executor.execute_tool(tool_name, arguments, client_id)
            
            return {
                'success': True,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_conversation_history(self, test_session_id: str, testing_session_manager) -> List[Dict[str, Any]]:
        """
        Return conversation history for test session
        
        Args:
            test_session_id: The test session ID
            testing_session_manager: TestingSessionManager instance
            
        Returns:
            List of conversation messages
        """
        session = testing_session_manager.get_session(test_session_id)
        if not session:
            return []
        
        return session.get('conversation_history', [])
    
    def simulate_ai_response(self, test_session_id: str, testing_session_manager) -> Dict[str, Any]:
        """
        Generate a mock AI response (for testing purposes)
        
        Args:
            test_session_id: The test session ID
            testing_session_manager: TestingSessionManager instance
            
        Returns:
            Mock AI response dictionary
        """
        session = testing_session_manager.get_session(test_session_id)
        if not session:
            return {
                'success': False,
                'error': 'Test session not found'
            }
        
        # Generate simple mock response
        mock_response = {
            'success': True,
            'response': '[Testing Mode - Mock AI Response]\n\nThis is a simulated AI response for testing purposes.',
            'iterations': 0,
            'tokens_used': 0
        }
        
        return mock_response
    
    async def end_test(self, test_session_id: str, testing_session_manager) -> Dict[str, Any]:
        """
        End test session and return summary
        
        Args:
            test_session_id: The test session ID
            testing_session_manager: TestingSessionManager instance
            
        Returns:
            Session summary dictionary
        """
        session_summary = testing_session_manager.end_session(test_session_id)
        
        if session_summary:
            # Send ai_turn_complete message to client via WebSocket
            try:
                from services.system_services.service_factory import get_websocket_manager
                ws_manager = get_websocket_manager()
                
                client_id = session_summary.get('client_id')
                if client_id:
                    completion_message = {
                        "type": "ai_turn_complete",
                        "data": {
                            "success": True,
                            "tokens_used": 0,
                            "iterations": session_summary.get('commands_executed', 0),
                            "test_mode": True
                        }
                    }
                    await ws_manager.send_to_client(client_id, completion_message)
                    logger.info(f"Sent ai_turn_complete message to client {client_id} for test session {test_session_id}")
            except Exception as e:
                logger.error(f"Error sending ai_turn_complete message for test session: {e}")
            
            # Clean up session
            testing_session_manager.cleanup_session(test_session_id)
            
            return {
                'success': True,
                'message': 'Test session ended',
                'session_summary': session_summary
            }
        else:
            return {
                'success': False,
                'error': 'Test session not found'
            }
    
    async def _handle_stop_command(self, test_session_id: str, testing_session_manager) -> Dict[str, Any]:
        """Handle stop command"""
        return await self.end_test(test_session_id, testing_session_manager)
    
    def _handle_status_command(self, test_session_id: str, testing_session_manager) -> Dict[str, Any]:
        """Handle status command"""
        session = testing_session_manager.get_session(test_session_id)
        
        if not session:
            return {
                'success': False,
                'error': 'Test session not found'
            }
        
        session_state = {
            'test_session_id': test_session_id,
            'client_id': session['client_id'],
            'state': session['state'],
            'conversation_length': len(session.get('conversation_history', [])),
            'commands_executed': session.get('commands_executed', 0),
            'tools_used': session.get('tools_used', []),
            'start_time': session['start_time'].isoformat(),
            'last_activity': session['last_activity'].isoformat(),
            'has_initial_prompt': session.get('initial_prompt') is not None
        }
        
        return {
            'success': True,
            'session_state': session_state
        }
    
    async def _handle_tool_call(
        self,
        test_session_id: str,
        parsed_command: Dict[str, Any],
        client_id: str,
        testing_session_manager,
        testing_command_processor
    ) -> Dict[str, Any]:
        """Handle tool call commands"""
        # Extract tool name and arguments
        tool_name = parsed_command.get('tool_name')
        arguments = parsed_command.get('arguments', {})
        
        # Increment command counter
        testing_session_manager.increment_commands_executed(test_session_id)
        
        # Record tool used
        testing_session_manager.record_tool_used(test_session_id, tool_name)
        
        # Add to conversation history
        conversation_message = {
            'role': 'user',
            'tool_call': {
                'name': tool_name,
                'arguments': arguments
            }
        }
        testing_session_manager.add_conversation_message(test_session_id, conversation_message)
        
        # Execute tool
        tool_result = await self.execute_tool_call(tool_name, arguments, client_id)
        
        if tool_result['success']:
            # Add result to conversation history
            result_message = {
                'role': 'tool',
                'tool_name': tool_name,
                'result': tool_result['result']
            }
            testing_session_manager.add_conversation_message(test_session_id, result_message)
            
            # Format response
            formatted_response = testing_command_processor.format_response(
                tool_result['result'],
                tool_name
            )
            
            formatted_response['session_state'] = 'awaiting_input'
            
            return formatted_response
        else:
            return {
                'success': False,
                'error': tool_result['error']
            }
    
    def _get_combat_context(self) -> Dict[str, Any]:
        """Get current combat context"""
        try:
            from services.system_services.service_factory import get_combat_encounter_service
            combat_service = get_combat_encounter_service()
            return combat_service.get_combat_context()
        except Exception as e:
            logger.error(f"Error getting combat context: {e}")
            return {'in_combat': False}

def get_testing_harness() -> TestingHarness:
    """
    Get or create testing harness instance
    
    Returns:
        TestingHarness instance
    """
    # This will be integrated with ServiceFactory later
    return TestingHarness()
