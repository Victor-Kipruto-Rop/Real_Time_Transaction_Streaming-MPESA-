#!/usr/bin/env python3
"""
Test Daraja C2B transaction simulation
"""
import os
import sys
import requests
import json
from datetime import datetime
from dotenv import load_dotenv


def get_access_token():
    """Get Daraja OAuth access token"""
    from base64 import b64encode
    
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


def simulate_c2b_transaction(access_token):
    """Simulate a C2B transaction"""
    environment = os.getenv('DARAJA_ENVIRONMENT', 'sandbox')
    shortcode = os.getenv('DARAJA_C2B_SHORTCODE', '174379')
    
    if environment == 'production':
        api_url = 'https://api.safaricom.co.ke/mpesa/c2b/v1/simulate'
    else:
        api_url = 'https://sandbox.safaricom.co.ke/mpesa/c2b/v1/simulate'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'ShortCode': shortcode,
        'CommandID': 'CustomerPayBillOnline',
        'Amount': '100',
        'Msisdn': '254708374149',  # Test number for sandbox
        'BillRefNumber': f'TEST{datetime.now().strftime("%Y%m%d%H%M%S")}'
    }
    
    print(f"\nSimulating C2B transaction...")
    print(f"API URL: {api_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_c2b_simulation():
    """Test C2B transaction simulation"""
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
        
        print("\nStep 2: Simulating C2B transaction...")
        success = simulate_c2b_transaction(access_token)
        
        if success:
            print("\n✓ C2B transaction simulation successful!")
            print("\nNote: Check your webhook endpoint for the confirmation callback")
            return True
        else:
            print("\n✗ C2B transaction simulation failed!")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


if __name__ == '__main__':
    success = test_c2b_simulation()
    sys.exit(0 if success else 1)
