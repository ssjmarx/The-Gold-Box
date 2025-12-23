#!/usr/bin/env python3
"""
Test script for AI session management
Tests backend-only session management without frontend AI session manager
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.ai_services.ai_session_manager import get_ai_session_manager
from services.message_services.message_delta_service import get_message_delta_service

def test_session_management():
    """Test AI session management functionality"""
    print("Testing AI Session Management")
    print("=" * 50)
    
    # Get services
    ai_session_manager = get_ai_session_manager()
    message_delta_service = get_message_delta_service()
    
    # Test session creation
    client_id = "test_client_123"
    print(f"Testing with client_id: {client_id}")
    
    # Create new session
    session_id_1 = ai_session_manager.create_or_get_session(client_id)
    print(f"Created session 1: {session_id_1}")
    
    # Get same session again (should return existing)
    session_id_2 = ai_session_manager.create_or_get_session(client_id)
    print(f"Retrieved session 2: {session_id_2}")
    
    # Verify they're the same
    if session_id_1 == session_id_2:
        print("✅ Session persistence working correctly")
    else:
        print("❌ Session persistence failed")
    
    # Test timestamp functionality
    print("\nTesting timestamp functionality:")
    test_messages = [
        {"timestamp": 1640995200000, "content": "Old message"},
        {"timestamp": 1640995201000, "content": "Newer message"},
        {"timestamp": 1640995202000, "content": "Newest message"},
    ]
    
    # Apply delta filtering (should return all messages for new session)
    filtered_1 = message_delta_service.apply_message_delta(session_id_1, test_messages)
    print(f"First call (new session): {len(filtered_1)}/{len(test_messages)} messages")
    
    # Apply delta filtering again (should return only newer messages)
    filtered_2 = message_delta_service.apply_message_delta(session_id_1, test_messages)
    print(f"Second call (existing session): {len(filtered_2)}/{len(test_messages)} messages")
    
    # Test session info
    session_info = ai_session_manager.get_session_info(session_id_1)
    print(f"\nSession info: {session_info}")
    
    # Test session stats
    stats = ai_session_manager.get_stats()
    print(f"\nSession manager stats: {stats}")
    
    print("\nTesting delta filtering with different timestamps:")
    
    # Test with newer message
    newer_messages = [
        {"timestamp": 1640995203000, "content": "Even newer message"},
    ]
    
    filtered_3 = message_delta_service.apply_message_delta(session_id_1, newer_messages)
    print(f"New message test: {len(filtered_3)}/{len(newer_messages)} messages")
    
    # Test force full context
    print(f"\nTesting force full context:")
    message_delta_service.force_full_context(session_id_1)
    filtered_4 = message_delta_service.apply_message_delta(session_id_1, test_messages)
    print(f"After force full context: {len(filtered_4)}/{len(test_messages)} messages")
    
    print("\n" + "=" * 50)
    print("Session management test completed!")

if __name__ == "__main__":
    test_session_management()
