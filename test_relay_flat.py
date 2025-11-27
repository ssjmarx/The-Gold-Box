#!/usr/bin/env python3
"""
Test the correct flat structure for relay server
"""

import requests
import json
from datetime import datetime

def test_flat_format():
    """Test with the correct flat structure based on chat.ts"""
    
    print("=== Testing Flat Structure ===")
    
    relay_url = "http://localhost:3010/chat"
    client_id = "foundry-I1xuWKewrC5fQH5U"
    
    # The relay server expects these fields at the root level, not nested
    post_data = {
        "clientId": client_id,
        "message.message": "Test message with flat structure",
        "message.speaker": "The Gold Box AI", 
        "message.type": "ic",
        "message.timestamp": int(datetime.now().timestamp() * 1000)
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "local-dev"
    }
    
    print(f"Post data: {json.dumps(post_data, indent=2)}")
    
    try:
        response = requests.post(
            relay_url,
            json=post_data,
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! Flat structure works")
            try:
                response_data = response.json()
                print(f"Response JSON: {json.dumps(response_data, indent=2)}")
            except:
                print(f"Response Text: {response.text}")
            return True
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run the test"""
    print("Testing flat structure for relay server...")
    
    success = test_flat_format()
    
    if success:
        print("\n✅ SUCCESS! Flat structure works.")
        print("Need to update API chat endpoint to use this format.")
    else:
        print("\n❌ Flat structure failed.")

if __name__ == "__main__":
    main()
