#!/usr/bin/env python3
"""
Helper script to make initial_messages.content field in test results human-readable.

This script identifies JSON objects containing initial_messages, extracts the content field,
and replaces escaped newlines with actual newlines for better readability.

The output does NOT need to be valid JSON - it just needs to be human-readable.
"""

import json
import sys
from pathlib import Path


def find_and_replace_content(content_str):
    """
    Find JSON objects with initial_messages field and make content human-readable.
    
    Args:
        content_str: The entire file content as a string
        
    Returns:
        Modified content with readable initial_messages.content fields
    """
    lines = content_str.split('\n')
    result_lines = []
    
    in_json_object = False
    json_lines = []
    brace_count = 0
    
    for i, line in enumerate(lines):
        stripped_line = line.strip()
        
        # Start of a JSON object
        if stripped_line.startswith('{') and not in_json_object:
            in_json_object = True
            json_lines = [line]
            brace_count = line.count('{') - line.count('}')
        
        # Inside a JSON object
        elif in_json_object:
            json_lines.append(line)
            brace_count += line.count('{') - line.count('}')
            
            # End of JSON object (all braces closed)
            if brace_count <= 0:
                in_json_object = False
                json_text = '\n'.join(json_lines)
                
                try:
                    # Parse as JSON
                    json_obj = json.loads(json_text)
                    
                    # Check if it has initial_messages field
                    if 'initial_messages' in json_obj:
                        # Process each message
                        for msg in json_obj.get('initial_messages', []):
                            if 'content' in msg:
                                content = msg['content']
                                # Try to parse as JSON to format nicely
                                try:
                                    parsed_content = json.loads(content)
                                    # Pretty-print with 2-space indentation
                                    pretty_content = json.dumps(
                                        parsed_content, 
                                        indent=2, 
                                        ensure_ascii=False
                                    )
                                    # Replace escaped newlines with actual newlines
                                    # This makes it human-readable (not valid JSON string)
                                    readable_content = pretty_content.replace('\\n', '\n')
                                    msg['content'] = readable_content
                                except json.JSONDecodeError:
                                    # Content is not JSON, just replace escaped newlines
                                    msg['content'] = content.replace('\\n', '\n').replace('\\"', '"')
                        
                        # Convert back to string (not valid JSON, but human-readable)
                        modified_lines = json_to_readable_string(json_obj)
                        result_lines.extend(modified_lines)
                    else:
                        # No initial_messages, add as is
                        result_lines.append(json_text)
                        
                except json.JSONDecodeError:
                    # Not valid JSON, add as is
                    result_lines.append(json_text)
                
                json_lines = []
                brace_count = 0
        
        # Not in JSON object
        else:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def json_to_readable_string(obj, indent=0):
    """
    Convert a JSON object to a human-readable string format.
    This is NOT valid JSON, but it's much more readable.
    
    Args:
        obj: Python object (dict, list, string, etc.)
        indent: Current indentation level
        
    Returns:
        List of strings representing the formatted output
    """
    indent_str = '  ' * indent
    lines = []
    
    if isinstance(obj, dict):
        if not obj:
            lines.append(f"{indent_str}{{}}")
        else:
            lines.append(f"{indent_str}{{")
            for key, value in obj.items():
                if isinstance(value, str) and '\n' in value:
                    # Multi-line string content
                    lines.append(f"{indent_str}  {key}: {json.dumps(key)}")
                    # Add the multi-line content with proper indentation
                    content_lines = value.split('\n')
                    for content_line in content_lines:
                        lines.append(f"{indent_str}  {content_line}")
                else:
                    # Regular value
                    value_lines = json_to_readable_string(value, indent + 1)
                    if value_lines:
                        lines.append(f"{indent_str}  {json.dumps(key)}: {value_lines[0].strip()}")
                        lines.extend(value_lines[1:])
            lines.append(f"{indent_str}}}")
    
    elif isinstance(obj, list):
        if not obj:
            lines.append(f"{indent_str}[]")
        else:
            lines.append(f"{indent_str}[")
            for item in obj:
                item_lines = json_to_readable_string(item, indent + 1)
                if item_lines:
                    lines.append(f"{indent_str}  {item_lines[0].strip()}")
                    lines.extend(item_lines[1:])
            lines.append(f"{indent_str}]")
    
    elif isinstance(obj, str):
        if '\n' in obj:
            # Multi-line string - already formatted
            lines.extend(obj.split('\n'))
        else:
            lines.append(json.dumps(obj, ensure_ascii=False))
    
    else:
        lines.append(json.dumps(obj, ensure_ascii=False))
    
    return lines


def process_file(file_path):
    """
    Process a file to make initial_messages.content fields human-readable.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified_content = find_and_replace_content(content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"✅ Successfully processed {file_path}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python pretty_print_content.py <file_path>")
        print("\nExample:")
        print("  python pretty_print_content.py test_results.log")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    
    if not file_path.exists():
        print(f"❌ Error: File '{file_path}' does not exist")
        sys.exit(1)
    
    process_file(file_path)