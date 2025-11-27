#!/usr/bin/env python3
"""
Test the corrected relay server message format with the working client ID
"""

import requests
import json
from datetime import datetime

def test_working_format():
    """Test with the working client ID and corrected format"""
    
    print("=== Testing Corrected Message Format ===")
    
    relay_url = "http://localhost:3010/chat"
    client_id = "foundry-I1xuWKewrC5fQH5U"  # Working client ID from messages test
    
    # Use the corrected format from our fix
    post_data = {
        "clientId": client_id,
        "message": {
            "message": "Test message with corrected format",
            "speaker": "The Gold Box AI",
            "type": "ic",  # ic = in-character
            "timestamp": int(datetime.now().timestamp() * 1000)  # milliseconds as required
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "local-dev"
    }
    
    print(f"Testing with client ID: {client_id}")
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
            print("✅ SUCCESS! Message sent successfully")
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

def verify_client_works():
    """Verify the client ID works by checking messages"""
    print("=== Verifying Client ID Works ===")
    
    try:
        response = requests.get(
            f"http://localhost:3010/messages?clientId=foundry-I1xuWKewrC5fQH5U&limit=1",
            headers={"x-api-key": "local-dev"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get('messages'):
                print(f"✅ Client ID verified - found {len(data['messages'])} messages")
                return True
            elif isinstance(data, list) and len(data) > 0:
                print(f"✅ Client ID verified - found {len(data)} messages")
                return True
            else:
                print("⚠️  Client ID works but no messages found")
                return True
        else:
            print(f"❌ Client ID verification failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying client ID: {e}")
        return False

def main():
    """Run the test"""
    print("Testing corrected relay server message format...")
    
    # First verify the client works
    if not verify_client_works():
        print("❌ Cannot proceed - client ID verification failed")
        return
    
    # Test the corrected format
    success = test_working_format()
    
    if success:
        print("\n✅ SUCCESS! The corrected message format works.")
        print("The API chat endpoint should now work with this format.")
    else:
        print("\n❌ Still failing. Need further investigation.")

if __name__ == "__main__":
    main()
