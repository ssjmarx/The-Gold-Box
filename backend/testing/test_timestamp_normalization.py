#!/usr/bin/env python3
"""
Test script for timestamp normalization in Message Delta Service
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.message_services.message_delta_service import MessageDeltaService

def test_timestamp_normalization():
    """Test the timestamp normalization function"""
    service = MessageDeltaService()
    
    # Test cases with different timestamp formats
    test_cases = [
        # (input, expected_output, description)
        (1766483110135, 1766483110, "Microsecond timestamp"),
        (1703952000, 1703952000000, "Second timestamp (Dec 30, 2023)"),
        (1703952000000, 1703952000000, "Millisecond timestamp"),
        (1640995200, 1640995200000, "Second timestamp (Jan 1, 2022)"),
        (1640995200000, 1640995200000, "Millisecond timestamp (Jan 1, 2022)"),
        ("1766483110135", 1766483110, "String microsecond timestamp"),
        ("1703952000", 1703952000000, "String second timestamp"),
        (None, None, "None timestamp"),
        ("invalid", None, "Invalid string timestamp"),
    ]
    
    print("Testing timestamp normalization:")
    print("=" * 60)
    
    for input_ts, expected, description in test_cases:
        result = service._normalize_timestamp(input_ts)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}")
        print(f"  Input: {input_ts}")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")
        print()
    
    # Test message filtering with real timestamps
    print("Testing message filtering with real data:")
    print("=" * 60)
    
    # Simulate messages like from the logs
    test_messages = [
        {"timestamp": 1766382712920, "content": "Old message 1"},
        {"timestamp": 1766382972846, "content": "Old message 2"},
        {"timestamp": 1766382987759, "content": "Old message 3"},
        {"timestamp": 1766483016980, "content": "Newer message 1"},
        {"timestamp": 1766483102194, "content": "Newer message 2"},
        {"timestamp": 1766483110135, "content": "Newest message"},
    ]
    
    # Test filtering with a session timestamp
    session_timestamp = 1766483050000  # Should filter out older messages
    
    print(f"Session timestamp: {session_timestamp}")
    print("Messages before filtering:")
    for msg in test_messages:
        normalized = service._normalize_timestamp(msg['timestamp'])
        comparison = ">" if normalized > session_timestamp else "<="
        print(f"  {msg['timestamp']} -> {normalized} {comparison} {session_timestamp}: {msg['content']}")
    
    print("\nMessages after filtering:")
    filtered = []
    for msg in test_messages:
        normalized = service._normalize_timestamp(msg['timestamp'])
        if normalized is not None and normalized > session_timestamp:
            filtered.append(msg)
            print(f"  {msg['timestamp']} -> {normalized}: {msg['content']}")
    
    print(f"\nFiltered {len(filtered)}/{len(test_messages)} messages")

if __name__ == "__main__":
    test_timestamp_normalization()
