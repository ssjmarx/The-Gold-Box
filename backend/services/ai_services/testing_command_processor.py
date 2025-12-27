#!/usr/bin/env python3
"""
Testing Command Processor for The Gold Box
Parses simplified curl commands and converts to AI tool calls
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class TestingCommandProcessor:
    """
    Parses simplified curl commands and converts to AI tool calls
    
    Available Simple Commands:
    - get_messages [count] - Retrieve chat messages (default: 15)
    - post "message content" - Post simple chat message
    - post_messages <json> - Post full message structure
    - tool_name param1=value1 param2=value2 - Call any AI tool
    - stop - End testing session
    - status - Show current test session state
    - help - List available commands
    """
    
    def __init__(self):
        """Initialize testing command processor"""
        self._available_commands = [
            'get_messages',
            'post',
            'post_messages',
            'stop',
            'status',
            'help'
        ]
        logger.info("TestingCommandProcessor initialized")
    
    def parse_command(self, command_string: str) -> Optional[Dict[str, Any]]:
        """
        Parse user command string
        
        Args:
            command_string: Raw command from user
            
        Returns:
            Parsed command dictionary or None if invalid
        """
        if not command_string or not command_string.strip():
            return None
        
        command_string = command_string.strip()
        
        # Check for stop command
        if command_string.lower() == 'stop':
            return {
                'command': 'stop',
                'tool_name': None,
                'arguments': None
            }
        
        # Check for status command
        if command_string.lower() == 'status':
            return {
                'command': 'status',
                'tool_name': None,
                'arguments': None
            }
        
        # Check for help command
        if command_string.lower() == 'help':
            return {
                'command': 'help',
                'tool_name': None,
                'arguments': None
            }
        
        # Try to parse as get_messages
        get_messages_match = re.match(r'^get_messages\s*(\d+)?$', command_string, re.IGNORECASE)
        if get_messages_match:
            count = int(get_messages_match.group(1)) if get_messages_match.group(1) else 15
            return {
                'command': 'get_messages',
                'tool_name': 'get_messages',
                'arguments': {'count': count}
            }
        
        # Try to parse as simple post
        post_match = re.match(r'^post\s+"([^"]*)"$', command_string, re.IGNORECASE)
        if post_match:
            message_content = post_match.group(1)
            return {
                'command': 'post',
                'tool_name': 'post_messages',
                'arguments': {
                    'messages': [
                        {
                            'content': message_content,
                            'type': 'chat-message'
                        }
                    ]
                }
            }
        
        # Try to parse as post_messages with JSON
        post_messages_match = re.match(r'^post_messages\s+(.+)$', command_string, re.IGNORECASE)
        if post_messages_match:
            json_str = post_messages_match.group(1)
            try:
                messages = json.loads(json_str)
                return {
                    'command': 'post_messages',
                    'tool_name': 'post_messages',
                    'arguments': {'messages': messages}
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON in post_messages: {e}")
                return None
        
        # Try to parse as generic tool call
        # Format: tool_name param1=value1 param2=value2
        tool_match = re.match(r'^(\w+)\s*(.*)$', command_string)
        if tool_match:
            tool_name = tool_match.group(1)
            args_string = tool_match.group(2).strip()
            
            # Parse arguments
            arguments = self._parse_arguments(args_string)
            
            return {
                'command': 'tool_call',
                'tool_name': tool_name,
                'arguments': arguments
            }
        
        logger.warning(f"Unable to parse command: {command_string}")
        return None
    
    def _parse_arguments(self, args_string: str) -> Dict[str, Any]:
        """
        Parse arguments from command string
        
        Args:
            args_string: Arguments string (e.g., 'count=15 "name=value"')
            
        Returns:
            Dictionary of parsed arguments
        """
        arguments = {}
        
        if not args_string:
            return arguments
        
        # Try to parse as JSON first
        try:
            return json.loads(args_string)
        except json.JSONDecodeError:
            pass
        
        # Parse as key=value pairs
        # Handle quoted values
        # Pattern: key="quoted value" or key=value
        pattern = r'(\w+)=("[^"]*"|\'[^\']*\'|\S+)'
        matches = re.findall(pattern, args_string)
        
        for key, value in matches:
            # Remove quotes from value
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            
            # Try to convert to int or float
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string
            
            arguments[key] = value
        
        return arguments
    
    def convert_to_tool_call(self, parsed_command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert parsed command to tool call format
        
        Args:
            parsed_command: Parsed command dictionary
            
        Returns:
            Tool call in OpenAI format or None if not a tool call
        """
        if not parsed_command:
            return None
        
        command = parsed_command.get('command')
        
        # Non-tool commands
        if command in ['stop', 'status', 'help']:
            return None
        
        tool_name = parsed_command.get('tool_name')
        arguments = parsed_command.get('arguments', {})
        
        if not tool_name:
            return None
        
        # Convert to OpenAI tool call format
        tool_call = {
            'id': f"test_call_{hash(tool_name + str(arguments))}",
            'type': 'function',
            'function': {
                'name': tool_name,
                'arguments': json.dumps(arguments)
            }
        }
        
        return tool_call
    
    def validate_command(self, parsed_command: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate parsed command
        
        Args:
            parsed_command: Parsed command dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not parsed_command:
            return False, "Command is empty or invalid"
        
        command = parsed_command.get('command')
        
        if command not in self._available_commands + ['tool_call']:
            return False, f"Unknown command: {command}"
        
        # Validate tool calls
        if command == 'tool_call':
            tool_name = parsed_command.get('tool_name')
            if not tool_name:
                return False, "Tool name is required for tool calls"
            
            arguments = parsed_command.get('arguments', {})
            
            # Validate get_messages arguments
            if tool_name == 'get_messages':
                count = arguments.get('count', 15)
                if not isinstance(count, int) or count < 1 or count > 50:
                    return False, "get_messages count must be an integer between 1 and 50"
            
            # Validate post_messages arguments
            if tool_name == 'post_messages':
                messages = arguments.get('messages', [])
                if not isinstance(messages, list):
                    return False, "post_messages requires a 'messages' array"
                
                if len(messages) == 0:
                    return False, "post_messages requires at least one message"
                
                for i, msg in enumerate(messages):
                    if not isinstance(msg, dict):
                        return False, f"Message {i} must be a dictionary"
                    
                    if 'content' not in msg:
                        return False, f"Message {i} is missing 'content' field"
        
        return True, None
    
    def get_available_commands(self) -> List[str]:
        """
        Get list of available commands
        
        Returns:
            List of command names
        """
        return self._available_commands.copy()
    
    def get_command_help(self) -> str:
        """
        Get help text for available commands
        
        Returns:
            Help text string
        """
        help_text = """
Available Testing Commands:

1. get_messages [count]
   Retrieve recent chat messages from Foundry
   Example: get_messages 15
   Default count: 15

2. post "message content"
   Post a simple chat message to Foundry
   Example: post "Hello from testing!"

3. post_messages <json>
   Post full message structure with options
   Example: post_messages messages=[{"content": "Hello", "type": "chat-message"}]

4. <tool_name> param1=value1 param2=value2
   Call any AI tool with parameters
   Example: get_messages count=20
   Example: post_messages messages=[{"content": "Test", "type": "chat-card"}]

5. stop
   End the testing session
   Example: stop

6. status
   Show current test session state
   Example: status

7. help
   Display this help message
   Example: help

Tips:
- Use double quotes for string values with spaces
- JSON can be used for complex structures
- All tool names from the AI system are available
"""
        return help_text.strip()
    
    def format_response(self, result: Any, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Format tool result for user display
        
        Args:
            result: Result from tool execution
            tool_name: Name of tool that was called
            
        Returns:
            Formatted response dictionary
        """
        if tool_name == 'get_messages':
            # Tool executor returns 'content' field, not 'messages'
            messages = result.get('content', [])
            return {
                'success': True,
                'result': {
                    'messages': messages,
                    'count': len(messages)
                }
            }
        
        elif tool_name == 'post_messages':
            # Tool executor returns 'sent_count' and 'results', not 'messages_sent' and 'message_ids'
            return {
                'success': True,
                'result': {
                    'messages_sent': result.get('sent_count', 0),
                    'results': result.get('results', [])
                }
            }
        
        else:
            # Generic tool response
            return {
                'success': True,
                'result': result
            }

def get_testing_command_processor() -> TestingCommandProcessor:
    """
    Get or create the testing command processor instance
    
    Returns:
        TestingCommandProcessor instance
    """
    # This will be integrated with ServiceFactory later
    return TestingCommandProcessor()
