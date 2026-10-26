#!/usr/bin/env python3
"""
Test Daraja API OAuth authentication
"""
import os
import sys
import requests
from base64 import b64encode
from dotenv import load_dotenv


def test_daraja_oauth():
    """Test Daraja OAuth token generation"""
    load_dotenv()
    
    consumer_key = os.getenv('DARAJA_CONSUMER_KEY')
    consumer_secret = os.getenv('DARAJA_CONSUMER_SECRET')
    environment = os.getenv('DARAJA_ENVIRONMENT', 'sandbox')
    
    if not consumer_key or not consumer_secret:
        print("✗ Error: DARAJA_CONSUMER_KEY and DARAJA_CONSUMER_SECRET must be set in .env")
        sys.exit(1)
    
    # Determine API URL based on environment
    if environment == 'production':
        api_url = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    else:
        api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    
    print(f"Testing Daraja OAuth ({environment} environment)...")
    print(f"API URL: {api_url}")
    print(f"Consumer Key: {consumer_key[:10]}...")
    
    # Create authorization header
    credentials = f"{consumer_key}:{consumer_secret}"
    encoded_credentials = b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {encoded_credentials}'
    }
    
    try:
        print("\nSending OAuth request...")
        response = requests.get(api_url, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✓ OAuth authentication successful!")
            print(f"Access Token: {data.get('access_token', '')[:20]}...")
            print(f"Expires In: {data.get('expires_in')} seconds")
            return True
        else:
            print(f"\n✗ OAuth authentication failed!")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Request failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


if __name__ == '__main__':
    success = test_daraja_oauth()
    sys.exit(0 if success else 1)
