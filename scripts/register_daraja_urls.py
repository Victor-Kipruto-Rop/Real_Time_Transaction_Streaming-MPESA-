#!/usr/bin/env python3
"""
Register C2B validation and confirmation URLs with Daraja API
"""
import os
import sys
import requests
import json
from base64 import b64encode
from dotenv import load_dotenv


def get_access_token():
    """Get Daraja OAuth access token"""
    consumer_key = os.getenv('DARAJA_CONSUMER_KEY')
    consumer_secret = os.getenv('DARAJA_CONSUMER_SECRET')
    environment = os.getenv('DARAJA_ENVIRONMENT', 'sandbox')
    
    if environment == 'production':
        api_url = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    else:
        api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    
    credentials = f"{consumer_key}:{consumer_secret}"
    encoded_credentials = b64encode(credentials.encode()).decode()
    
    headers = {'Authorization': f'Basic {encoded_credentials}'}
    
    response = requests.get(api_url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Failed to get access token: {response.text}")


def register_urls(access_token):
    """Register C2B URLs with Daraja"""
    environment = os.getenv('DARAJA_ENVIRONMENT', 'sandbox')
    shortcode = os.getenv('DARAJA_C2B_SHORTCODE', '174379')
    validation_url = os.getenv('C2B_VALIDATION_URL')
    confirmation_url = os.getenv('C2B_CONFIRMATION_URL')
    
    if not validation_url or not confirmation_url:
        print("✗ Error: C2B_VALIDATION_URL and C2B_CONFIRMATION_URL must be set in .env")
        sys.exit(1)
    
    if environment == 'production':
        api_url = 'https://api.safaricom.co.ke/mpesa/c2b/v1/registerurl'
    else:
        api_url = 'https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'ShortCode': shortcode,
        'ResponseType': 'Completed',
        'ConfirmationURL': confirmation_url,
        'ValidationURL': validation_url
    }
    
    print(f"\nRegistering C2B URLs...")
    print(f"API URL: {api_url}")
    print(f"Shortcode: {shortcode}")
    print(f"Validation URL: {validation_url}")
    print(f"Confirmation URL: {confirmation_url}")
    
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def main():
    """Main function"""
    load_dotenv()
    
    consumer_key = os.getenv('DARAJA_CONSUMER_KEY')
    consumer_secret = os.getenv('DARAJA_CONSUMER_SECRET')
    
    if not consumer_key or not consumer_secret:
        print("✗ Error: DARAJA_CONSUMER_KEY and DARAJA_CONSUMER_SECRET must be set in .env")
        sys.exit(1)
    
    try:
        print("Step 1: Getting OAuth access token...")
        access_token = get_access_token()
        print(f"✓ Access token obtained: {access_token[:20]}...")
        
        print("\nStep 2: Registering C2B URLs...")
        success = register_urls(access_token)
        
        if success:
            print("\n✓ C2B URLs registered successfully!")
            print("\nYour webhook endpoints are now configured to receive:")
            print("  - Validation requests")
            print("  - Confirmation callbacks")
            return True
        else:
            print("\n✗ C2B URL registration failed!")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
