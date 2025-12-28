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
    
    def generate_initial_prompt(
        self,
        client_id: str,
        universal_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate initial prompt (same format as real AI would receive)
        
        Args:
            client_id: The Foundry client ID
            universal_settings: Settings from frontend
            
        Returns:
            Dictionary with initial_prompt and session data
        """
        try:
            # Generate system prompt based on AI role
            ai_role = universal_settings.get('ai role', 'gm')
            
            # Get combat context
            combat_context = self._get_combat_context()
            
            # Build combat context message
            combat_context_message = {
                'type': 'combat_context',
                'combat_context': combat_context
            }
            
            # Generate enhanced system prompt
            system_prompt = self._unified_processor.generate_enhanced_system_prompt(
                ai_role,
                [combat_context_message]
            )
            
            # Get delta counts
            message_delta = universal_settings.get('message_delta', {})
            new_count = message_delta.get('new_messages', 0)
            deleted_count = message_delta.get('deleted_messages', 0)
            
            # Add delta information
            delta_display = f"""

Changes since last prompt: [New Messages: {new_count}, Deleted Messages: {deleted_count}]
"""
            
            # Build initial prompt
            initial_prompt = system_prompt + delta_display
            
            # Get AI role instruction
            ai_role_lower = ai_role.lower()
            role_messages = {
                'gm': 'Take your turn as Game Master.',
                "gm's assistant": 'Take your turn as GM\'s Assistant.',
                'player': 'Take your turn as Player.'
            }
            user_message = role_messages.get(ai_role_lower, 'Take your turn as Game Master.')
            
            initial_prompt += f"\n\n{user_message}"
            
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
    
    def end_test(self, test_session_id: str, testing_session_manager) -> Dict[str, Any]:
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
    
    def _handle_stop_command(self, test_session_id: str, testing_session_manager) -> Dict[str, Any]:
        """Handle stop command"""
        return self.end_test(test_session_id, testing_session_manager)
    
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
