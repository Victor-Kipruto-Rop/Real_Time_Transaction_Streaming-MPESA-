"""
M-Pesa Webhook Simulation

This script simulates M-Pesa webhook callbacks for testing purposes.
"""

import requests
import json
import time
import random
from datetime import datetime
from typing import List, Dict


class WebhookSimulator:
    """Simulate M-Pesa webhook callbacks"""
    
    def __init__(self, webhook_url: str = 'http://localhost:5000'):
        """
        Initialize the simulator
        
        Args:
            webhook_url: Base URL of the webhook receiver
        """
        self.webhook_url = webhook_url.rstrip('/')
        self.headers = {'Content-Type': 'application/json'}
    
    def generate_c2b_transaction(self, transaction_id: str = None) -> Dict:
        """
        Generate a random C2B transaction payload
        
        Args:
            transaction_id: Optional transaction ID
            
        Returns:
            Transaction payload
        """
        if not transaction_id:
            transaction_id = f'TXN{random.randint(1000000000, 9999999999)}'
        
        first_names = ['John', 'Jane', 'Peter', 'Mary', 'David', 'Sarah', 'Michael', 'Emily']
        last_names = ['Doe', 'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller']
        
        return {
            'TransID': transaction_id,
            'TransAmount': str(round(random.uniform(100, 10000), 2)),
            'MSISDN': f'25471{random.randint(1000000, 9999999)}',
            'AccountReference': f'ACC{random.randint(100, 999)}',
            'TransTime': datetime.now().strftime('%Y%m%d%H%M%S'),
            'BillRefNumber': f'BILL{random.randint(100, 999)}',
            'FirstName': random.choice(first_names),
            'MiddleName': random.choice(['K', 'M', 'A', 'L', '']),
            'LastName': random.choice(last_names),
            'OrgAccountBalance': str(round(random.uniform(10000, 100000), 2))
        }
    
    def send_c2b_confirmation(self, payload: Dict = None) -> requests.Response:
        """
        Send C2B confirmation webhook
        
        Args:
            payload: Transaction payload (auto-generated if None)
            
        Returns:
            Response object
        """
        if payload is None:
            payload = self.generate_c2b_transaction()
        
        url = f'{self.webhook_url}/webhook/c2b/confirmation'
        response = requests.post(url, json=payload, headers=self.headers)
        
        return response
    
    def send_c2b_validation(self, payload: Dict = None) -> requests.Response:
        """
        Send C2B validation webhook
        
        Args:
            payload: Transaction payload (auto-generated if None)
            
        Returns:
            Response object
        """
        if payload is None:
            payload = self.generate_c2b_transaction()
        
        # Validation payload is simpler
        validation_payload = {
            'TransID': payload['TransID'],
            'TransAmount': payload['TransAmount'],
            'MSISDN': payload['MSISDN'],
            'AccountReference': payload['AccountReference'],
            'TransTime': payload['TransTime']
        }
        
        url = f'{self.webhook_url}/webhook/c2b/validation'
        response = requests.post(url, json=validation_payload, headers=self.headers)
        
        return response
    
    def generate_stk_callback(self, checkout_request_id: str = None, 
                             success: bool = True) -> Dict:
        """
        Generate STK Push callback payload
        
        Args:
            checkout_request_id: Checkout Request ID
            success: Whether payment was successful
            
        Returns:
            Callback payload
        """
        if not checkout_request_id:
            checkout_request_id = f'ws_CO_{random.randint(100000000000, 999999999999)}'
        
        merchant_request_id = f'REQ{random.randint(10000, 99999)}'
        
        if success:
            callback_metadata = {
                'Item': [
                    {'Name': 'Amount', 'Value': random.randint(100, 10000)},
                    {'Name': 'MpesaReceiptNumber', 'Value': f'RCP{random.randint(1000000000, 9999999999)}'},
                    {'Name': 'TransactionDate', 'Value': int(datetime.now().timestamp())},
                    {'Name': 'PhoneNumber', 'Value': random.randint(254700000000, 254799999999)}
                ]
            }
            
            return {
                'Body': {
                    'stkCallback': {
                        'MerchantRequestID': merchant_request_id,
                        'CheckoutRequestID': checkout_request_id,
                        'ResultCode': 0,
                        'ResultDesc': 'The service request is processed successfully.',
                        'CallbackMetadata': callback_metadata
                    }
                }
            }
        else:
            return {
                'Body': {
                    'stkCallback': {
                        'MerchantRequestID': merchant_request_id,
                        'CheckoutRequestID': checkout_request_id,
                        'ResultCode': 1032,
                        'ResultDesc': 'Request cancelled by user'
                    }
                }
            }
    
    def send_stk_callback(self, payload: Dict = None, success: bool = True) -> requests.Response:
        """
        Send STK Push callback
        
        Args:
            payload: Callback payload (auto-generated if None)
            success: Whether payment was successful
            
        Returns:
            Response object
        """
        if payload is None:
            payload = self.generate_stk_callback(success=success)
        
        url = f'{self.webhook_url}/webhook/stk/callback'
        response = requests.post(url, json=payload, headers=self.headers)
        
        return response
    
    def simulate_load(self, num_transactions: int = 100, delay: float = 0.1):
        """
        Simulate load by sending multiple transactions
        
        Args:
            num_transactions: Number of transactions to send
            delay: Delay between transactions (seconds)
        """
        print(f"Simulating {num_transactions} transactions...")
        
        successful = 0
        failed = 0
        
        for i in range(num_transactions):
            try:
                response = self.send_c2b_confirmation()
                
                if response.status_code in [200, 409]:
                    successful += 1
                    status = '✓'
                else:
                    failed += 1
                    status = '✗'
                
                print(f"{status} Transaction {i+1}/{num_transactions} - Status: {response.status_code}")
                
                time.sleep(delay)
                
            except Exception as e:
                failed += 1
                print(f"✗ Transaction {i+1}/{num_transactions} - Error: {e}")
        
        print(f"\nResults: {successful} successful, {failed} failed")


def example_single_transaction():
    """Example: Send a single transaction"""
    print("Example 1: Single C2B Transaction")
    print("=" * 60)
    
    simulator = WebhookSimulator()
    
    # Generate and send transaction
    payload = simulator.generate_c2b_transaction()
    print("Payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    response = simulator.send_c2b_confirmation(payload)
    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    print()


def example_validation_flow():
    """Example: Send validation then confirmation"""
    print("Example 2: Validation + Confirmation Flow")
    print("=" * 60)
    
    simulator = WebhookSimulator()
    
    # Generate transaction
    payload = simulator.generate_c2b_transaction()
    
    # Send validation
    print("1. Sending validation...")
    validation_response = simulator.send_c2b_validation(payload)
    print(f"   Status: {validation_response.status_code}")
    print(f"   Response: {validation_response.text}")
    print()
    
    # Send confirmation
    print("2. Sending confirmation...")
    confirmation_response = simulator.send_c2b_confirmation(payload)
    print(f"   Status: {confirmation_response.status_code}")
    print(f"   Response: {confirmation_response.text}")
    print()


def example_stk_push():
    """Example: STK Push callback"""
    print("Example 3: STK Push Callback")
    print("=" * 60)
    
    simulator = WebhookSimulator()
    
    # Successful payment
    print("1. Successful payment:")
    success_payload = simulator.generate_stk_callback(success=True)
    print(json.dumps(success_payload, indent=2))
    
    response = simulator.send_stk_callback(success_payload)
    print(f"   Status: {response.status_code}")
    print()
    
    # Failed payment
    print("2. Failed payment:")
    failed_payload = simulator.generate_stk_callback(success=False)
    print(json.dumps(failed_payload, indent=2))
    
    response = simulator.send_stk_callback(failed_payload)
    print(f"   Status: {response.status_code}")
    print()


def example_load_test():
    """Example: Load testing"""
    print("Example 4: Load Testing")
    print("=" * 60)
    
    simulator = WebhookSimulator()
    
    # Simulate 50 transactions with 0.1s delay
    simulator.simulate_load(num_transactions=50, delay=0.1)


if __name__ == '__main__':
    print("M-Pesa Webhook Simulator")
    print("=" * 60)
    print()
    
    # Run examples
    example_single_transaction()
    print("\n")
    
    example_validation_flow()
    print("\n")
    
    example_stk_push()
    print("\n")
    
    # Uncomment to run load test
    # example_load_test()
