#!/usr/bin/env python3
"""
Validate all integration configurations for M-Pesa Analytics Platform
"""
import os
import sys
import argparse
from typing import Dict, List, Tuple
from dotenv import load_dotenv


class IntegrationValidator:
    """Validate integration configurations"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.validations_passed = 0
        self.validations_failed = 0
        self.warnings = []
    
    def log(self, message: str):
        """Log message if verbose mode is enabled"""
        if self.verbose:
            print(f"  {message}")
    
    def validate_daraja_config(self) -> bool:
        """Validate Daraja API configuration"""
        print("\n1. Validating Daraja API Configuration...")
        
        required_vars = {
            'DARAJA_CONSUMER_KEY': 'Daraja Consumer Key',
            'DARAJA_CONSUMER_SECRET': 'Daraja Consumer Secret',
            'DARAJA_BUSINESS_SHORTCODE': 'Business Shortcode',
            'DARAJA_PASSKEY': 'Passkey',
            'DARAJA_ENVIRONMENT': 'Environment (sandbox/production)'
        }
        
        all_valid = True
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                self.log(f"✓ {description}: {'*' * 10}")
            else:
                print(f"  ✗ {description} ({var}) is not set")
                all_valid = False
        
        # Validate webhook URLs
        webhook_vars = {
            'C2B_VALIDATION_URL': 'C2B Validation URL',
            'C2B_CONFIRMATION_URL': 'C2B Confirmation URL',
            'DARAJA_STK_CALLBACK_URL': 'STK Push Callback URL'
        }
        
        for var, description in webhook_vars.items():
            value = os.getenv(var)
            if value:
                if value.startswith('http://') or value.startswith('https://'):
                    self.log(f"✓ {description}: {value}")
                else:
                    print(f"  ⚠ {description} should start with http:// or https://")
                    self.warnings.append(f"{description} URL format may be invalid")
            else:
                print(f"  ⚠ {description} ({var}) is not set")
                self.warnings.append(f"{description} is optional but recommended")
        
        if all_valid:
            print("  ✓ Daraja configuration is valid")
        else:
            print("  ✗ Daraja configuration is incomplete")
        
        return all_valid
    
    def validate_database_config(self) -> bool:
        """Validate database configuration"""
        print("\n2. Validating Database Configuration...")
        
        required_vars = {
            'POSTGRES_HOST': 'PostgreSQL Host',
            'POSTGRES_PORT': 'PostgreSQL Port',
            'POSTGRES_DB': 'Database Name',
            'POSTGRES_USER': 'Database User',
            'POSTGRES_PASSWORD': 'Database Password'
        }
        
        all_valid = True
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                if var == 'POSTGRES_PASSWORD':
                    self.log(f"✓ {description}: {'*' * 10}")
                else:
                    self.log(f"✓ {description}: {value}")
            else:
                print(f"  ✗ {description} ({var}) is not set")
                all_valid = False
        
        if all_valid:
            print("  ✓ Database configuration is valid")
        else:
            print("  ✗ Database configuration is incomplete")
        
        return all_valid
    
    def validate_kafka_config(self) -> bool:
        """Validate Kafka configuration"""
        print("\n3. Validating Kafka Configuration...")
        
        required_vars = {
            'KAFKA_BROKERS': 'Kafka Brokers',
            'KAFKA_TOPIC_TRANSACTIONS': 'Transactions Topic',
            'KAFKA_GROUP_ID': 'Consumer Group ID'
        }
        
        all_valid = True
        for var, description in required_vars.items():
            value = os.getenv(var)
            if value:
                self.log(f"✓ {description}: {value}")
            else:
                print(f"  ⚠ {description} ({var}) is not set (will use default)")
                self.warnings.append(f"{description} will use default value")
        
        print("  ✓ Kafka configuration is valid (using defaults where needed)")
        return True
    
    def validate_aws_config(self) -> bool:
        """Validate AWS RDS configuration"""
        print("\n4. Validating AWS RDS Configuration...")
        
        aws_vars = {
            'AWS_REGION': 'AWS Region',
            'RDS_HOST': 'RDS Host',
            'RDS_PORT': 'RDS Port',
            'RDS_DB_NAME': 'RDS Database Name',
            'RDS_USERNAME': 'RDS Username'
        }
        
        has_any_aws = any(os.getenv(var) for var in aws_vars.keys())
        
        if not has_any_aws:
            print("  ⚠ AWS RDS configuration not found (optional)")
            self.warnings.append("AWS RDS is optional - using local PostgreSQL")
            return True
        
        all_valid = True
        for var, description in aws_vars.items():
            value = os.getenv(var)
            if value:
                self.log(f"✓ {description}: {value}")
            else:
                print(f"  ✗ {description} ({var}) is not set")
                all_valid = False
        
        if all_valid:
            print("  ✓ AWS RDS configuration is valid")
        else:
            print("  ✗ AWS RDS configuration is incomplete")
        
        return all_valid
    
    def validate_grafana_config(self) -> bool:
        """Validate Grafana configuration"""
        print("\n5. Validating Grafana Configuration...")
        
        grafana_vars = {
            'GRAFANA_ADMIN_USER': 'Grafana Admin User',
            'GRAFANA_ADMIN_PASSWORD': 'Grafana Admin Password',
            'GRAFANA_HOST_PORT': 'Grafana Port'
        }
        
        for var, description in grafana_vars.items():
            value = os.getenv(var)
            if value:
                if 'PASSWORD' in var:
                    self.log(f"✓ {description}: {'*' * 10}")
                else:
                    self.log(f"✓ {description}: {value}")
            else:
                print(f"  ⚠ {description} ({var}) not set (will use default)")
                self.warnings.append(f"{description} will use default value")
        
        print("  ✓ Grafana configuration is valid (using defaults where needed)")
        return True
    
    def validate_security_config(self) -> bool:
        """Validate security configuration"""
        print("\n6. Validating Security Configuration...")
        
        security_vars = {
            'UI_TOKEN': 'UI Authentication Token',
            'RATE_LIMIT_PER_MIN': 'Rate Limit'
        }
        
        for var, description in security_vars.items():
            value = os.getenv(var)
            if value:
                if 'TOKEN' in var:
                    self.log(f"✓ {description}: {'*' * 10}")
                else:
                    self.log(f"✓ {description}: {value}")
            else:
                print(f"  ⚠ {description} ({var}) not set")
                self.warnings.append(f"{description} is recommended for production")
        
        print("  ✓ Security configuration checked")
        return True
    
    def run_all_validations(self) -> bool:
        """Run all validation checks"""
        print("=" * 70)
        print("M-Pesa Analytics Platform - Integration Configuration Validator")
        print("=" * 70)
        
        validations = [
            self.validate_daraja_config(),
            self.validate_database_config(),
            self.validate_kafka_config(),
            self.validate_aws_config(),
            self.validate_grafana_config(),
            self.validate_security_config()
        ]
        
        self.validations_passed = sum(validations)
        self.validations_failed = len(validations) - self.validations_passed
        
        print("\n" + "=" * 70)
        print(f"Results: {self.validations_passed}/{len(validations)} validations passed")
        
        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        print("=" * 70)
        
        return self.validations_failed == 0


def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(
        description='Validate M-Pesa Analytics Platform integration configurations'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    args = parser.parse_args()
    
    load_dotenv()
    
    validator = IntegrationValidator(verbose=args.verbose)
    success = validator.run_all_validations()
    
    if success:
        print("\n✓ All critical configurations are valid!")
        if validator.warnings:
            print("\nNote: Review warnings above for optional improvements")
        sys.exit(0)
    else:
        print("\n✗ Some configurations are invalid or incomplete!")
        print("\nPlease update your .env file and run validation again.")
        sys.exit(1)


if __name__ == '__main__':
    main()
