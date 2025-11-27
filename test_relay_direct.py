#!/usr/bin/env python3
"""
Direct test script to debug relay server communication issues
Tests sending messages directly to the relay server chat endpoint
"""

import requests
import json
import time
import sys
from datetime import datetime

def test_relay_server_direct():
    """Test sending messages directly to relay server"""
    
    print("=== Relay Server Direct Test ===")
    
    # Test configuration
    relay_url = "http://localhost:3010/chat"
    client_id = "foundry-I1xuWKewrC5fQH5U"
    
    # Test message in the exact format expected by relay server
    test_message = {
        "type": "chat-message",
        "content": "Test message from direct script",
        "author": {
            "name": "Test Script",
            "id": "test-script"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    post_data = {
        "clientId": client_id,
        "message": test_message
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "local-dev"
    }
    
    print(f"Target URL: {relay_url}")
    print(f"Client ID: {client_id}")
    print(f"Headers: {headers}")
    print(f"Post data: {json.dumps(post_data, indent=2)}")
    
    # Test with different timeout values
    timeouts = [5, 10, 20, 30, 60]
    
    for timeout in timeouts:
        print(f"\n--- Testing with {timeout}s timeout ---")
        start_time = time.time()
        
        try:
            response = requests.post(
                relay_url,
                json=post_data,
                headers=headers,
                timeout=timeout
            )
            
            elapsed = time.time() - start_time
            print(f"Response received in {elapsed:.2f}s")
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"Response JSON: {json.dumps(response_data, indent=2)}")
                except:
                    print(f"Response Text: {response.text}")
                print(f"✅ SUCCESS with {timeout}s timeout!")
                return True
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response Text: {response.text}")
                
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            print(f"❌ TIMEOUT after {elapsed:.2f}s (limit was {timeout}s)")
        except requests.exceptions.ConnectionError as e:
            elapsed = time.time() - start_time
            print(f"❌ CONNECTION ERROR after {elapsed:.2f}s: {e}")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ OTHER ERROR after {elapsed:.2f}s: {e}")
    
    return False

def test_relay_server_health():
    """Test if relay server is responsive"""
    print("\n=== Relay Server Health Check ===")
    
    try:
        # Test basic connectivity
        response = requests.get("http://localhost:3010/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        print(f"Health check response: {response.text}")
    except:
        print("Health check endpoint not available")
    
    try:
        # Test clients endpoint
        response = requests.get("http://localhost:3010/clients", timeout=5)
        print(f"Clients endpoint status: {response.status_code}")
        if response.status_code == 200:
            clients = response.json()
            print(f"Available clients: {json.dumps(clients, indent=2)}")
    except Exception as e:
        print(f"Clients endpoint error: {e}")

def test_message_format_variations():
    """Test different message formats to see what works"""
    print("\n=== Message Format Variations Test ===")
    
    client_id = "foundry-I1xuWKewrC5fQH5U"
    base_url = "http://localhost:3010/chat"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "local-dev"
    }
    
    # Different message formats to test
    test_formats = [
        {
            "name": "Simple format",
            "data": {
                "clientId": client_id,
                "message": "Hello World"
            }
        },
        {
            "name": "Full message format",
            "data": {
                "clientId": client_id,
                "message": {
                    "type": "chat-message",
                    "content": "Test full format",
                    "author": {"name": "Test Script"},
                    "timestamp": datetime.now().isoformat()
                }
            }
        },
        {
            "name": "Foundry format",
            "data": {
                "clientId": client_id,
                "message.message": "Test Foundry format",
                "message.speaker": "Test Script",
                "message.type": "chat-message",
                "message.timestamp": datetime.now().isoformat()
            }
        },
        {
            "name": "Minimal format",
            "data": {
                "clientId": client_id,
                "message.message": "Minimal test"
            }
        }
    ]
    
    for test_format in test_formats:
        print(f"\n--- Testing {test_format['name']} ---")
        print(f"Data: {json.dumps(test_format['data'], indent=2)}")
        
        try:
            response = requests.post(
                base_url,
                json=test_format['data'],
                headers=headers,
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ SUCCESS with {test_format['name']}")
                try:
                    print(f"Response: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"Response: {response.text}")
            else:
                print(f"❌ FAILED: {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")

def main():
    """Run all tests"""
    print("Starting relay server debug tests...")
    print(f"Current time: {datetime.now()}")
    
    # Test 1: Health check
    test_relay_server_health()
    
    # Test 2: Direct message sending
    success = test_relay_server_direct()
    
    # Test 3: Different message formats
    test_message_format_variations()
    
    # Summary
    print(f"\n=== Test Summary ===")
    if success:
        print("✅ At least one test succeeded - relay server is working")
    else:
        print("❌ All tests failed - relay server has issues")
        print("\nPossible issues:")
        print("1. Relay server not running on localhost:3010")
        print("2. Client ID not registered with relay server")
        print("3. Authentication issues")
        print("4. Message format mismatch")
        print("5. Network connectivity issues")

if __name__ == "__main__":
    main()
