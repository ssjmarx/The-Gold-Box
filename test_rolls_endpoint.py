#!/usr/bin/env python3
"""
Test script to directly test rolls endpoint and debug data structure
"""

import requests
import json
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_rolls_endpoint():
    """Test the rolls endpoint directly"""
    print("=== Testing Rolls Endpoint Directly ===")
    
    client_id = "foundry-I1xuWKewrC5fQH5U"
    headers = {"x-api-key": "local-dev"}
    
    # Test the rolls endpoint
    try:
        print(f"Testing rolls endpoint with client ID: {client_id}")
        
        response = requests.get(
            "http://localhost:3010/rolls",
            params={"clientId": client_id, "limit": 10},
            headers=headers,
            timeout=5
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Parsed JSON data:")
                print(json.dumps(data, indent=2))
                
                # Analyze the structure
                if isinstance(data, dict):
                    print(f"Keys in response: {list(data.keys())}")
                    
                    # Check for rolls in different locations
                    if 'data' in data:
                        print(f"Found 'data' field with {len(data.get('data', []))} items")
                        if data.get('data'):
                            for i, roll in enumerate(data['data'][:3]):
                                print(f"  Roll {i+1}: {json.dumps(roll, indent=4)}")
                    
                    if 'rolls' in data:
                        print(f"Found 'rolls' field with {len(data.get('rolls', []))} items")
                        if data.get('rolls'):
                            for i, roll in enumerate(data['rolls'][:3]):
                                print(f"  Roll {i+1}: {json.dumps(roll, indent=4)}")
                else:
                    print("No 'data' or 'rolls' field found in response")
            except json.JSONDecodeError:
                print("Response is not JSON format")
        else:
            print(f"Request failed with status: {response.status_code}")
            print(f"Response text: {response.text}")
    
    except Exception as e:
        print(f"Error testing rolls endpoint: {e}")

if __name__ == "__main__":
    test_rolls_endpoint()
