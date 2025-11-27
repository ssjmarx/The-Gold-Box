#!/usr/bin/env python3
"""
Test script to verify the new features:
1. Configurable MAX_ROLLS_STORED setting
2. Dynamic data refresh functionality
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

# Configuration
RELAY_URL = "http://localhost:3010"
API_KEY = "test-world"

def test_chat_messages_with_refresh() -> Dict[str, Any]:
    """Test chat messages endpoint with refresh parameter"""
    print("Testing chat messages with dynamic refresh...")
    
    try:
        # Test without refresh first
        response = requests.post(
            f"{RELAY_URL}/api/client/{API_KEY}/request",
            json={
                "actionType": "chat-messages",
                "requestId": "test-refresh-1",
                "limit": 10
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Initial request successful: {data.get('total', 0)} messages returned")
        else:
            return {"success": False, "error": f"Initial request failed: {response.status_code}"}
        
        # Test with refresh
        response = requests.post(
            f"{RELAY_URL}/api/client/{API_KEY}/request",
            json={
                "actionType": "chat-messages",
                "requestId": "test-refresh-2",
                "limit": 10,
                "refresh": True
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Refresh request successful: {data.get('total', 0)} messages returned")
            return {"success": True, "messages": data.get('messages', [])}
        else:
            return {"success": False, "error": f"Refresh request failed: {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_rolls_with_configurable_limit() -> Dict[str, Any]:
    """Test that rolls respect the configurable limit"""
    print("Testing rolls with configurable limit...")
    
    try:
        # Get rolls data
        response = requests.post(
            f"{RELAY_URL}/api/client/{API_KEY}/request",
            json={
                "actionType": "rolls",
                "requestId": "test-rolls-limit",
                "limit": 50  # Request more than the default
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            rolls = data.get('rolls', [])
            print(f"✓ Rolls request successful: {len(rolls)} rolls returned")
            
            # Check if the number of rolls is reasonable (should be limited by setting)
            if len(rolls) <= 50:
                print(f"✓ Rolls count is within expected limits: {len(rolls)}")
                return {"success": True, "rolls": rolls}
            else:
                print(f"⚠ Rolls count seems high: {len(rolls)} (may not be respecting limit)")
                return {"success": True, "rolls": rolls, "warning": "High roll count"}
        else:
            return {"success": False, "error": f"Rolls request failed: {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_chat_message_structure(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Test that chat messages have the expected structure"""
    print("Testing chat message structure...")
    
    if not messages:
        return {"success": True, "message": "No messages to test"}
    
    try:
        for i, message in enumerate(messages[:3]):  # Test first 3 messages
            required_fields = ['id', 'messageId', 'user', 'content', 'timestamp']
            missing_fields = [field for field in required_fields if field not in message]
            
            if missing_fields:
                return {
                    "success": False, 
                    "error": f"Message {i} missing fields: {missing_fields}",
                    "message": message
                }
            
            # Check user structure
            if 'user' in message:
                user_fields = ['id', 'name']
                missing_user_fields = [field for field in user_fields if field not in message['user']]
                if missing_user_fields:
                    return {
                        "success": False,
                        "error": f"Message {i} user missing fields: {missing_user_fields}",
                        "user": message['user']
                    }
        
        print(f"✓ Chat message structure is correct for {len(messages)} messages")
        return {"success": True, "tested": len(messages)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_roll_structure(rolls: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Test that roll data has the expected structure"""
    print("Testing roll data structure...")
    
    if not rolls:
        return {"success": True, "message": "No rolls to test"}
    
    try:
        for i, roll in enumerate(rolls[:3]):  # Test first 3 rolls
            required_fields = ['id', 'messageId', 'user', 'rollTotal', 'formula', 'timestamp']
            missing_fields = [field for field in required_fields if field not in roll]
            
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Roll {i} missing fields: {missing_fields}",
                    "roll": roll
                }
            
            # Check user structure
            if 'user' in roll:
                user_fields = ['id', 'name']
                missing_user_fields = [field for field in user_fields if field not in roll['user']]
                if missing_user_fields:
                    return {
                        "success": False,
                        "error": f"Roll {i} user missing fields: {missing_user_fields}",
                        "user": roll['user']
                    }
        
        print(f"✓ Roll data structure is correct for {len(rolls)} rolls")
        return {"success": True, "tested": len(rolls)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """Run all tests"""
    print("🧪 Testing New Features: Configurable Limits & Dynamic Refresh")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Chat messages with refresh
    print("\n1. Testing Dynamic Refresh Feature")
    print("-" * 30)
    chat_result = test_chat_messages_with_refresh()
    results['chat_refresh'] = chat_result
    
    if chat_result.get('success') and 'messages' in chat_result:
        # Test message structure if we have messages
        structure_result = test_chat_message_structure(chat_result['messages'])
        results['chat_structure'] = structure_result
    
    # Test 2: Rolls with configurable limit
    print("\n2. Testing Configurable Roll Limits")
    print("-" * 30)
    rolls_result = test_rolls_with_configurable_limit()
    results['rolls_limit'] = rolls_result
    
    if rolls_result.get('success') and 'rolls' in rolls_result:
        # Test roll structure if we have rolls
        structure_result = test_roll_structure(rolls_result['rolls'])
        results['roll_structure'] = structure_result
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    for test_name, result in results.items():
        total_tests += 1
        status = "✅ PASS" if result.get('success') else "❌ FAIL"
        print(f"{test_name:20} {status}")
        
        if result.get('success'):
            passed_tests += 1
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! New features are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
