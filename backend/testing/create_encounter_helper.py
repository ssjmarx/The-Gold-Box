#!/usr/bin/env python3
"""
Helper script to construct complete JSON request for encounter management tests
This avoids shell quoting issues by building the entire JSON payload in Python
"""

import json
import sys
import argparse

def build_request(actor_ids_json, test_session_id, roll_initiative=True):
    """
    Build complete JSON request for encounter management
    
    Args:
        actor_ids_json: JSON string of actor IDs
        test_session_id: The test session ID
        roll_initiative: Whether to roll initiative (default: True)
    
    Returns:
        Complete JSON request as string
    """
    # Parse actor IDs
    actor_ids = json.loads(actor_ids_json)
    
    # Build the request
    request = {
        "command": "test_command",
        "test_session_id": test_session_id,
        "test_command": {
            "command": "create_encounter",
            "actor_ids": actor_ids,
            "roll_initiative": roll_initiative
        }
    }
    
    return json.dumps(request)

def main():
    parser = argparse.ArgumentParser(
        description='Build JSON request for encounter management tests'
    )
    parser.add_argument('actor_ids', help='JSON array of actor IDs')
    parser.add_argument('test_session_id', help='Test session ID')
    parser.add_argument('--roll_initiative', 
                        action='store_true', 
                        help='Roll initiative (default: True)')
    parser.add_argument('--no_initiative', 
                        action='store_true', 
                        help='Do NOT roll initiative')
    
    args = parser.parse_args()
    
    # Determine roll_initiative value
    roll_initiative = True
    if args.no_initiative:
        roll_initiative = False
    elif args.roll_initiative:
        roll_initiative = True
    
    # Build and print the request
    request_json = build_request(
        args.actor_ids,
        args.test_session_id,
        roll_initiative
    )
    
    print(request_json)

if __name__ == "__main__":
    main()
