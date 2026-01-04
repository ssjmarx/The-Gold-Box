#!/usr/bin/env python3
"""
Universal Command Helper for Gold Box Testing
Properly constructs JSON requests for test commands without bash escaping issues
"""

import sys
import json
import argparse
import re

def parse_key_value_command(command_str):
    """
    Parse command string with key=value pairs into a dictionary
    Handles both:
    - key=value (unquoted)
    - key="value" (quoted)
    - key='value' (single quoted)
    - key=[{...}] (JSON arrays)
    """
    result = {}
    
    # First, check if there's a JSON array value (greedy match)
    json_array_pattern = r'(\w+)=(\[.*?\])'
    json_match = re.search(json_array_pattern, command_str)
    
    if json_match:
        key = json_match.group(1)
        json_str = json_match.group(2)
        # Try to parse the JSON array
        try:
            result[key] = json.loads(json_str)
        except json.JSONDecodeError:
            result[key] = json_str
        
        # Remove this part from command string
        command_str = command_str[:json_match.start()] + command_str[json_match.end():]
    
    # Match remaining key=value pairs, handling quotes
    pattern = r'(\w+)=(".*?"|\'.*?\'|\S+)'
    matches = re.findall(pattern, command_str)
    
    for match in matches:
        equals_pos = match.find('=')
        if equals_pos == -1:
            continue
            
        key = match[:equals_pos]
        value = match[equals_pos+1:]
        
        # Remove quotes if present
        is_quoted = False
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
            is_quoted = True
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
            is_quoted = True
        
        # Convert booleans
        if value.lower() in ('true', 'false'):
            result[key] = value.lower() == 'true'
        # Convert numbers only if not quoted
        elif not is_quoted:
            try:
                result[key] = int(value)
            except ValueError:
                try:
                    result[key] = float(value)
                except ValueError:
                    result[key] = value
        else:
            # Keep as string
            result[key] = value
    
    return result

def load_session_id():
    """
    Load test session ID from .test_session_id file if it exists
    This allows session persistence across multiple test scripts
    
    Returns:
        Session ID string or None if file doesn't exist
    """
    try:
        with open('.test_session_id', 'r') as f:
            session_id = f.read().strip()
            if session_id and session_id != 'null':
                # print(f"DEBUG: Loaded session_id from file: {session_id}", file=sys.stderr)
                return session_id
    except FileNotFoundError:
        # print(f"DEBUG: No .test_session_id file found", file=sys.stderr)
        pass
    except Exception as e:
        # print(f"DEBUG: Error reading .test_session_id: {e}", file=sys.stderr)
        pass
    return None

def create_command_json(test_session_id, test_command, encounter_id=None):
    """
    Create JSON request for test_command
    
    Args:
        test_session_id: The test session ID (can be None or "null")
        test_command: The command string to execute
        encounter_id: Optional encounter_id for commands that need it
        
    Returns:
        JSON string ready for curl
    """
    # If test_session_id is None or "null", try to load from file
    if not test_session_id or test_session_id.lower() == 'null':
        loaded_session_id = load_session_id()
        if loaded_session_id:
            test_session_id = loaded_session_id
            # print(f"DEBUG: Using loaded session_id: {test_session_id}", file=sys.stderr)
        else:
            # print(f"DEBUG: No session_id available", file=sys.stderr)
            pass
    
    # Debug: show what we're parsing
    # print(f"DEBUG: Parsing command: {test_command}", file=sys.stderr)
    # print(f"DEBUG: encounter_id: {encounter_id}", file=sys.stderr)
    
    request = {
        "command": "test_command",
        "test_session_id": test_session_id,
        "test_command": test_command
    }
    
    # Add encounter_id if provided
    if encounter_id:
        request["encounter_id"] = encounter_id
    
    return json.dumps(request, indent=2, ensure_ascii=False)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Create test command JSON request')
    parser.add_argument('test_session_id', help='Test session ID')
    parser.add_argument('test_command', help='Command to execute')
    parser.add_argument('--encounter_id', help='Encounter ID (optional)', default=None)
    
    args = parser.parse_args()
    
    # Create and output JSON
    json_output = create_command_json(args.test_session_id, args.test_command, args.encounter_id)
    print(json_output)

if __name__ == '__main__':
    main()
