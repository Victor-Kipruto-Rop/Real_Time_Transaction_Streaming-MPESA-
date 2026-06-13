#!/usr/bin/env python3
"""
Verify M-Pesa Analytics Platform setup
"""
import os
import sys
import subprocess
from typing import Dict, List, Tuple


class SetupVerifier:
    """Verify platform setup and dependencies"""
    
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []
    
    def check_python_version(self) -> bool:
        """Check Python version"""
        print("Checking Python version...", end=" ")
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            print(f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.8+)")
            return False
    
    def check_dependencies(self) -> bool:
        """Check required Python packages"""
        print("\nChecking Python dependencies...")
        required_packages = [
            'kafka-python',
            'psycopg2',
            'flask',
            'requests',
            'boto3',
            'redis',
            'pydantic'
        ]
        
        all_installed = True
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"  ✓ {package}")
            except ImportError:
                print(f"  ✗ {package} (not installed)")
                all_installed = False
        
        return all_installed
    
    def check_docker(self) -> bool:
        """Check Docker installation"""
        print("\nChecking Docker...", end=" ")
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✓ {version}")
                return True
            else:
                print("✗ Docker not found")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("✗ Docker not found")
            return False
    
    def check_docker_compose(self) -> bool:
        """Check Docker Compose installation"""
        print("Checking Docker Compose...", end=" ")
        try:
            result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✓ {version}")
                return True
            else:
                print("✗ Docker Compose not found")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("✗ Docker Compose not found")
            return False
    
    def check_env_file(self) -> bool:
        """Check .env file existence"""
        print("\nChecking environment configuration...", end=" ")
        if os.path.exists('.env'):
            print("✓ .env file exists")
            return True
        else:
            print("⚠ .env file not found (optional)")
            self.warnings.append("Create .env file from .env.example for custom configuration")
            return True  # Not critical
    
    def check_directory_structure(self) -> bool:
        """Check required directories"""
        print("\nChecking directory structure...")
        required_dirs = [
            'ingestion',
            'streaming',
            'dbt',
            'analytics',
            'ml',
            'dashboards',
            'schemas',
            'tests',
            'scripts'
        ]
        
        all_exist = True
        for directory in required_dirs:
            if os.path.isdir(directory):
                print(f"  ✓ {directory}/")
            else:
                print(f"  ✗ {directory}/ (missing)")
                all_exist = False
        
        return all_exist
    
    def check_docker_services(self) -> bool:
        """Check if Docker services are running"""
        print("\nChecking Docker services...", end=" ")
        try:
            result = subprocess.run(
                ['docker', 'compose', 'ps', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                print("✓ Services are running")
                return True
            else:
                print("⚠ No services running (run 'make infra-up')")
                self.warnings.append("Start services with: make infra-up")
                return True  # Not critical for setup verification
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠ Could not check services")
            return True
    
    def run_all_checks(self) -> bool:
        """Run all verification checks"""
        print("=" * 60)
        print("M-Pesa Analytics Platform - Setup Verification")
        print("=" * 60)
        
        checks = [
            self.check_python_version(),
            self.check_dependencies(),
            self.check_docker(),
            self.check_docker_compose(),
            self.check_env_file(),
            self.check_directory_structure(),
            self.check_docker_services()
        ]
        
        self.checks_passed = sum(checks)
        self.checks_failed = len(checks) - self.checks_passed
        
        print("\n" + "=" * 60)
        print(f"Results: {self.checks_passed} passed, {self.checks_failed} failed")
        
        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        print("=" * 60)
        
        return self.checks_failed == 0


def main():
    """Main verification function"""
    verifier = SetupVerifier()
    success = verifier.run_all_checks()
    
    if success:
        print("\n✓ Setup verification completed successfully!")
        print("\nNext steps:")
        print("  1. Configure .env file (if not done)")
        print("  2. Start services: make infra-up")
        print("  3. Run tests: make test")
        sys.exit(0)
    else:
        print("\n✗ Setup verification failed!")
        print("\nPlease fix the issues above and run again.")
        sys.exit(1)


if __name__ == '__main__':
    main()
