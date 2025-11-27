#!/usr/bin/env python3
"""
Simple test to debug the exact relay server format issue
"""

import requests
import json
from datetime import datetime

def test_variations():
    """Test different variations to find working format"""
    
    print("=== Testing Format Variations ===")
    
    relay_url = "http://localhost:3010/chat"
    client_id = "foundry-I1xuWKewrC5fQH5U"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "local-dev"
    }
    
    # Test variations based on error analysis
    variations = [
        {
            "name": "Flat structure (no nested message)",
            "data": {
                "clientId": client_id,
                "message": "Test flat structure",
                "speaker": "Test Script",
                "type": "ic"
            }
        },
        {
            "name": "Nested with all required fields",
            "data": {
                "clientId": client_id,
                "message": {
                    "message": "Test nested structure",
                    "speaker": "Test Script", 
                    "type": "ic"
                }
            }
        },
        {
            "name": "Nested with timestamp",
            "data": {
                "clientId": client_id,
                "message": {
                    "message": "Test with timestamp",
                    "speaker": "Test Script",
                    "type": "ic", 
                    "timestamp": int(datetime.now().timestamp() * 1000)
                }
            }
        }
    ]
    
    for i, variation in enumerate(variations):
        print(f"\n--- Test {i+1}: {variation['name']} ---")
        print(f"Data: {json.dumps(variation['data'], indent=2)}")
        
        try:
            response = requests.post(
                relay_url,
                json=variation['data'],
                headers=headers,
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ SUCCESS!")
                try:
                    response_data = response.json()
                    print(f"Response: {json.dumps(response_data, indent=2)}")
                except:
                    print(f"Response: {response.text}")
                return variation['data'], True
            else:
                print(f"❌ FAILED: {response.text}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    return None, False

def check_client_status():
    """Check what clients are actually available"""
    print("=== Checking Client Status ===")
    
    try:
        response = requests.get("http://localhost:3010/clients", timeout=5)
        if response.status_code == 200:
            clients = response.json()
            print(f"Available clients: {json.dumps(clients, indent=2)}")
            
            if clients.get('total', 0) == 0:
                print("⚠️  WARNING: No clients registered!")
                print("This means Foundry VTT is not connected to relay server.")
                print("The client ID we're using may be invalid or Foundry may not be running.")
                return False
            else:
                print(f"✅ Found {clients.get('total', 0)} registered clients")
                return True
        else:
            print(f"❌ Failed to get clients: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking clients: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting relay server format debugging...")
    
    # First check if any clients are registered
    clients_ok = check_client_status()
    
    if not clients_ok:
        print("\n❌ ISSUE: No clients registered with relay server!")
        print("This is likely the root cause of the timeout issues.")
        print("The API chat endpoint is trying to send messages to a client that doesn't exist.")
        return
    
    # If clients exist, test message formats
    working_format, success = test_variations()
    
    if success:
        print(f"\n✅ Found working format: {working_format}")
    else:
        print("\n❌ No working format found")

if __name__ == "__main__":
    main()
