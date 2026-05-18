"""
Sample script demonstrating AWS RDS IAM authentication connection

Usage:
    python scripts/demo_rds_connection.py

This script demonstrates:
1. Loading environment variables
2. Establishing a connection via IAM authentication
3. Executing queries
4. Error handling
"""

import logging
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.rds_connection import connect_to_rds, test_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_basic_connection():
    """Demonstrate basic connection and version query"""
    logger.info("=" * 60)
    logger.info("DEMO 1: Basic Connection Test")
    logger.info("=" * 60)
    
    conn = connect_to_rds()
    if not conn:
        logger.error("Failed to establish connection")
        return False
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT version();')
        version = cur.fetchone()[0]
        logger.info(f"✓ Database version: {version}")
        cur.close()
        return True
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return False
    finally:
        conn.close()
        logger.info("✓ Connection closed\n")


def demo_transaction_query():
    """Demonstrate querying transaction data"""
    logger.info("=" * 60)
    logger.info("DEMO 2: Query Transaction Data")
    logger.info("=" * 60)
    
    conn = connect_to_rds()
    if not conn:
        logger.error("Failed to establish connection")
        return False
    
    try:
        cur = conn.cursor()
        
        # Query transaction count (adjust table name as needed)
        logger.info("Fetching transaction statistics...")
        query = """
        SELECT 
            CASE 
                WHEN EXISTS (SELECT 1 FROM information_schema.tables 
                            WHERE table_name = 'transactions')
                THEN 'Transactions table exists'
                ELSE 'Transactions table not found'
            END as status;
        """
        cur.execute(query)
        result = cur.fetchone()
        logger.info(f"✓ Result: {result[0]}")
        
        cur.close()
        return True
    except Exception as e:
        logger.error(f"Query failed: {e}")
        return False
    finally:
        conn.close()
        logger.info("✓ Connection closed\n")


def demo_connection_pooling():
    """Demonstrate multiple connections (connection pooling pattern)"""
    logger.info("=" * 60)
    logger.info("DEMO 3: Multiple Connections")
    logger.info("=" * 60)
    
    num_connections = 3
    connections = []
    
    try:
        # Establish multiple connections
        for i in range(num_connections):
            logger.info(f"Creating connection {i+1}/{num_connections}...")
            conn = connect_to_rds()
            if conn:
                connections.append(conn)
                cur = conn.cursor()
                cur.execute("SELECT 'Connection %d active' as msg;" % (i+1))
                msg = cur.fetchone()[0]
                logger.info(f"✓ {msg}")
                cur.close()
            else:
                logger.warning(f"Failed to create connection {i+1}")
        
        logger.info(f"✓ Successfully created {len(connections)}/{num_connections} connections\n")
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
    finally:
        # Close all connections
        for i, conn in enumerate(connections):
            try:
                conn.close()
                logger.info(f"Connection {i+1} closed")
            except Exception as e:
                logger.error(f"Error closing connection {i+1}: {e}")


def demo_env_configuration():
    """Demonstrate environment variable configuration"""
    logger.info("=" * 60)
    logger.info("DEMO 4: Environment Configuration")
    logger.info("=" * 60)
    
    required_vars = [
        'RDS_DB_HOST',
        'RDS_DB_PORT',
        'RDS_DB_NAME',
        'RDS_DB_USER',
        'AWS_REGION'
    ]
    
    logger.info("Required environment variables:")
    all_set = True
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'PASSWORD' in var or 'SECRET' in var:
                display_value = f"****{value[-4:]}" if len(value) > 4 else "****"
            else:
                display_value = value
            logger.info(f"✓ {var}: {display_value}")
        else:
            logger.warning(f"✗ {var}: NOT SET")
            all_set = False
    
    if all_set:
        logger.info("✓ All environment variables are configured\n")
    else:
        logger.warning("✗ Some environment variables are missing. See .env.example\n")
    
    return all_set


def main():
    """Run all demonstrations"""
    logger.info("\n")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " AWS RDS IAM Authentication - Demonstration Script".center(58) + "║")
    logger.info("║" + f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(59) + "║")
    logger.info("╚" + "═" * 58 + "╝")
    logger.info("\n")
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            '.env'
        )
        if os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"✓ Loaded environment from: {env_file}\n")
        else:
            logger.warning(f"⚠ .env file not found at: {env_file}")
            logger.warning("  Copy .env.example to .env and configure it\n")
    except ImportError:
        logger.warning("python-dotenv not installed. Ensure env vars are set manually.\n")
    
    # Demo 1: Configuration check
    config_ok = demo_env_configuration()
    
    if not config_ok:
        logger.error("Configuration is incomplete. Please set up .env file.")
        return False
    
    # Demo 2: Basic connection test
    if not test_connection():
        logger.error("Connection test failed. Check AWS credentials and RDS configuration.")
        return False
    
    # Demo 3: Basic queries
    if not demo_basic_connection():
        logger.error("Basic connection demo failed")
        return False
    
    # Demo 4: Table queries
    if not demo_transaction_query():
        logger.warning("Transaction query demo failed (table may not exist)")
    
    # Demo 5: Multiple connections
    if not demo_connection_pooling():
        logger.warning("Connection pooling demo encountered issues")
    
    logger.info("=" * 60)
    logger.info("All demonstrations completed!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Review the rds_connection module in ingestion/")
    logger.info("2. Integrate with your data pipelines")
    logger.info("3. Run: make test-rds to validate with pytest")
    logger.info("\n")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
