#!/usr/bin/env python3
"""
Demonstrate AWS RDS IAM authentication connection
"""
import os
import sys
from dotenv import load_dotenv


def demo_rds_connection():
    """Demonstrate RDS connection with IAM authentication"""
    load_dotenv()
    
    print("=" * 60)
    print("AWS RDS IAM Authentication Demo")
    print("=" * 60)
    
    # Check required environment variables
    required_vars = [
        'AWS_REGION',
        'RDS_HOST',
        'RDS_PORT',
        'RDS_DB_NAME',
        'RDS_USERNAME'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("\n✗ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these in your .env file")
        sys.exit(1)
    
    print("\n✓ All required environment variables are set")
    print("\nConfiguration:")
    print(f"  Region: {os.getenv('AWS_REGION')}")
    print(f"  Host: {os.getenv('RDS_HOST')}")
    print(f"  Port: {os.getenv('RDS_PORT')}")
    print(f"  Database: {os.getenv('RDS_DB_NAME')}")
    print(f"  Username: {os.getenv('RDS_USERNAME')}")
    
    try:
        from ingestion.rds_connection import RDSConnection
        
        print("\nStep 1: Initializing RDS connection...")
        rds_conn = RDSConnection(
            host=os.getenv('RDS_HOST'),
            port=int(os.getenv('RDS_PORT', '5432')),
            user=os.getenv('RDS_USERNAME'),
            database=os.getenv('RDS_DB_NAME'),
            region=os.getenv('AWS_REGION')
        )
        print("✓ RDS connection initialized")
        
        print("\nStep 2: Generating IAM authentication token...")
        token = rds_conn.generate_auth_token()
        print(f"✓ Token generated: {token[:30]}...")
        
        print("\nStep 3: Connecting to RDS...")
        conn = rds_conn.connect()
        print("✓ Connected to RDS successfully!")
        
        print("\nStep 4: Testing connection with simple query...")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL version: {version}")
        
        print("\nStep 5: Closing connection...")
        cursor.close()
        conn.close()
        print("✓ Connection closed")
        
        print("\n" + "=" * 60)
        print("✓ RDS IAM Authentication Demo Completed Successfully!")
        print("=" * 60)
        
        return True
        
    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        print("\nMake sure ingestion.rds_connection module exists")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify AWS credentials are configured")
        print("  2. Check RDS instance is accessible")
        print("  3. Verify IAM role has rds-db:connect permission")
        print("  4. Check security group allows connection")
        return False


if __name__ == '__main__':
    success = demo_rds_connection()
    sys.exit(0 if success else 1)
