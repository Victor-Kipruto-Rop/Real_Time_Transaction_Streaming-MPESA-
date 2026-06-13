"""
M-Pesa Analytics Platform - API Usage Examples

This script demonstrates how to interact with the M-Pesa Analytics API.
"""

import requests
import json
from datetime import datetime, timedelta


class MPesaAnalyticsClient:
    """Client for M-Pesa Analytics API"""
    
    def __init__(self, base_url: str, api_token: str):
        """
        Initialize the client
        
        Args:
            base_url: Base URL of the API (e.g., http://localhost:5000)
            api_token: API authentication token
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
    
    def health_check(self):
        """Check API health status"""
        response = requests.get(f'{self.base_url}/health')
        return response.json()
    
    def get_transaction(self, transaction_id: str):
        """
        Get a specific transaction by ID
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Transaction details
        """
        response = requests.get(
            f'{self.base_url}/api/transactions/{transaction_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def list_transactions(self, start_date=None, end_date=None, 
                         phone_number=None, limit=50, page=1):
        """
        List transactions with filters
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            phone_number: Filter by phone number
            limit: Results per page
            page: Page number
            
        Returns:
            List of transactions
        """
        params = {
            'limit': limit,
            'page': page
        }
        
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if phone_number:
            params['phone_number'] = phone_number
        
        response = requests.get(
            f'{self.base_url}/api/transactions',
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_daily_summary(self, date: str):
        """
        Get daily transaction summary
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Daily summary statistics
        """
        response = requests.get(
            f'{self.base_url}/api/summary/daily',
            headers=self.headers,
            params={'date': date}
        )
        response.raise_for_status()
        return response.json()
    
    def get_customer_transactions(self, phone_number: str, limit=50):
        """
        Get transaction history for a customer
        
        Args:
            phone_number: Customer phone number
            limit: Number of results
            
        Returns:
            Customer transaction history
        """
        response = requests.get(
            f'{self.base_url}/api/customers/{phone_number}/transactions',
            headers=self.headers,
            params={'limit': limit}
        )
        response.raise_for_status()
        return response.json()
    
    def get_analytics_report(self, start_date: str, end_date: str, 
                            metrics='volume,customers,trends'):
        """
        Get comprehensive analytics report
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            metrics: Comma-separated metrics
            
        Returns:
            Analytics report
        """
        response = requests.get(
            f'{self.base_url}/api/analytics/report',
            headers=self.headers,
            params={
                'start_date': start_date,
                'end_date': end_date,
                'metrics': metrics
            }
        )
        response.raise_for_status()
        return response.json()
    
    def initiate_stk_push(self, phone_number: str, amount: float, 
                         account_reference: str, transaction_desc: str):
        """
        Initiate STK Push payment
        
        Args:
            phone_number: Customer phone number
            amount: Amount to charge
            account_reference: Account reference
            transaction_desc: Transaction description
            
        Returns:
            STK Push response
        """
        payload = {
            'phone_number': phone_number,
            'amount': amount,
            'account_reference': account_reference,
            'transaction_desc': transaction_desc
        }
        
        response = requests.post(
            f'{self.base_url}/api/stk-push',
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def query_stk_push(self, checkout_request_id: str):
        """
        Query STK Push payment status
        
        Args:
            checkout_request_id: Checkout Request ID
            
        Returns:
            Payment status
        """
        response = requests.get(
            f'{self.base_url}/api/stk-push/{checkout_request_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()


def example_usage():
    """Example usage of the API client"""
    
    # Initialize client
    client = MPesaAnalyticsClient(
        base_url='http://localhost:5000',
        api_token='your_api_token_here'
    )
    
    print("1. Health Check")
    print("-" * 50)
    health = client.health_check()
    print(json.dumps(health, indent=2))
    print()
    
    print("2. Get Transaction by ID")
    print("-" * 50)
    try:
        transaction = client.get_transaction('TXN1234567890')
        print(json.dumps(transaction, indent=2))
    except requests.exceptions.HTTPError as e:
        print(f"Error: {e}")
    print()
    
    print("3. List Recent Transactions")
    print("-" * 50)
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    transactions = client.list_transactions(
        start_date=week_ago,
        end_date=today,
        limit=10
    )
    print(f"Found {transactions['pagination']['total']} transactions")
    print(f"Showing {len(transactions['data'])} results")
    print()
    
    print("4. Get Daily Summary")
    print("-" * 50)
    summary = client.get_daily_summary(today)
    print(json.dumps(summary, indent=2))
    print()
    
    print("5. Get Customer Transactions")
    print("-" * 50)
    customer = client.get_customer_transactions('254712345678', limit=5)
    print(json.dumps(customer, indent=2))
    print()
    
    print("6. Get Analytics Report")
    print("-" * 50)
    report = client.get_analytics_report(
        start_date=week_ago,
        end_date=today,
        metrics='volume,customers,trends'
    )
    print(json.dumps(report, indent=2))
    print()
    
    print("7. Initiate STK Push")
    print("-" * 50)
    stk_response = client.initiate_stk_push(
        phone_number='254712345678',
        amount=100,
        account_reference='TEST001',
        transaction_desc='Test payment'
    )
    print(json.dumps(stk_response, indent=2))
    
    # Query STK Push status
    if 'CheckoutRequestID' in stk_response:
        print("\n8. Query STK Push Status")
        print("-" * 50)
        status = client.query_stk_push(stk_response['CheckoutRequestID'])
        print(json.dumps(status, indent=2))


if __name__ == '__main__':
    example_usage()
