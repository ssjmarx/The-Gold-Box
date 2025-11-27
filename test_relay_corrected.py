#!/usr/bin/env python3
"""
Corrected relay server test with proper message format
"""

import requests
import json
from datetime import datetime

def test_correct_format():
    """Test with the correct message format based on relay server code"""
    
    print("=== Testing Correct Relay Server Format ===")
    
    relay_url = "http://localhost:3010/chat"
    client_id = "foundry-I1xuWKewrC5fQH5U"
    
    # Correct format based on relay server requirements:
    # - clientId (string)
    # - message (object)
    # - message.message (string) - REQUIRED
    # - message.speaker (string) - REQUIRED  
    # - message.type (string) - REQUIRED
    # - message.timestamp (number) - optional
    
    post_data = {
        "clientId": client_id,
        "message": {
            "message": "Test message with correct format",
            "speaker": "Test Script",
            "type": "ic",  # in-character
            "timestamp": int(datetime.now().timestamp() * 1000)  # milliseconds
        }
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
            print("✅ SUCCESS!")
            try:
                response_data = response.json()
                print(f"Response JSON: {json.dumps(response_data, indent=2)}")
            except:
                print(f"Response Text: {response.text}")
            return True
        else:
            print(f"❌ FAILED: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    test_correct_format()
