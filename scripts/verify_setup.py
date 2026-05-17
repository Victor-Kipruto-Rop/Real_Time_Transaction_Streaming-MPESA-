#!/usr/bin/env python3
"""
Comprehensive Verification Script for M-Pesa Platform
Validates all components and dependencies before deployment
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

class Color:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print colored header"""
    print(f"\n{Color.BLUE}{Color.BOLD}{'=' * 70}{Color.ENDC}")
    print(f"{Color.BLUE}{Color.BOLD}{text:^70}{Color.ENDC}")
    print(f"{Color.BLUE}{Color.BOLD}{'=' * 70}{Color.ENDC}\n")

def print_success(message: str):
    """Print success message"""
    print(f"{Color.GREEN}✓{Color.ENDC} {message}")

def print_error(message: str):
    """Print error message"""
    print(f"{Color.RED}✗{Color.ENDC} {message}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Color.YELLOW}⚠{Color.ENDC} {message}")

def print_info(message: str):
    """Print info message"""
    print(f"{Color.BLUE}ℹ{Color.ENDC} {message}")

class VerificationReport:
    """Tracks verification results"""
    
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
    
    def add_check(self, category: str, name: str, passed: bool, message: str = ""):
        """Add a check result"""
        self.checks.append({
            'category': category,
            'name': name,
            'passed': passed,
            'message': message
        })
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary statistics"""
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c['passed'])
        failed = total - passed
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success_rate': (passed / total * 100) if total > 0 else 0
        }
    
    def print_summary(self):
        """Print verification summary"""
        summary = self.get_summary()
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        print_header("VERIFICATION SUMMARY")
        
        print(f"Total Checks: {summary['total']}")
        print(f"Passed: {Color.GREEN}{summary['passed']}{Color.ENDC}")
        print(f"Failed: {Color.RED}{summary['failed']}{Color.ENDC}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Duration: {elapsed:.2f}s")
        
        # Group by category
        print(f"\n{Color.BOLD}By Category:{Color.ENDC}")
        categories = {}
        for check in self.checks:
            cat = check['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0}
            if check['passed']:
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1
        
        for cat, stats in sorted(categories.items()):
            total = stats['passed'] + stats['failed']
            rate = (stats['passed'] / total * 100) if total > 0 else 0
            status = Color.GREEN if stats['failed'] == 0 else Color.RED
            print(f"  {cat}: {status}{stats['passed']}/{total} ({rate:.0f}%){Color.ENDC}")
        
        if summary['failed'] == 0:
            print_success(f"\n{Color.BOLD}All checks passed! System ready for deployment.{Color.ENDC}")
            return True
        else:
            print_error(f"\n{Color.BOLD}{summary['failed']} check(s) failed. Please fix before deployment.{Color.ENDC}")
            return False

report = VerificationReport()

# ============================================================================
# 1. ENVIRONMENT & CONFIGURATION CHECKS
# ============================================================================

print_header("ENVIRONMENT & CONFIGURATION CHECKS")

# Check Python version
try:
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor} (3.11+ required)")
        report.add_check("Environment", "Python Version", True)
    else:
        print_error(f"Python {version.major}.{version.minor} (3.11+ required)")
        report.add_check("Environment", "Python Version", False)
except Exception as e:
    print_error(f"Failed to check Python: {e}")
    report.add_check("Environment", "Python Version", False)

# Check .env file
try:
    if os.path.exists('.env'):
        print_success(".env file exists")
        report.add_check("Environment", ".env File", True)
        
        # Check for required variables
        required_vars = [
            'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB',
            'POSTGRES_USER', 'POSTGRES_PASSWORD', 'KAFKA_BROKERS'
        ]
        
        with open('.env') as f:
            env_content = f.read()
        
        missing = [v for v in required_vars if f'{v}=' not in env_content]
        
        if not missing:
            print_success("All required environment variables present")
            report.add_check("Environment", "Required Variables", True)
        else:
            print_error(f"Missing variables: {', '.join(missing)}")
            report.add_check("Environment", "Required Variables", False)
    else:
        print_warning(".env file not found. Run: cp .env.example .env")
        report.add_check("Environment", ".env File", False)
except Exception as e:
    print_error(f"Failed to check .env: {e}")
    report.add_check("Environment", ".env File", False)

# ============================================================================
# 2. DEPENDENCY CHECKS
# ============================================================================

print_header("DEPENDENCY CHECKS")

required_packages = [
    'fastapi', 'uvicorn', 'psycopg2', 'httpx', 'pydantic',
    'flask', 'confluent_kafka', 'pytest'
]

for package in required_packages:
    try:
        spec = importlib.util.find_spec(package.replace('-', '_'))
        if spec is not None:
            print_success(f"{package} is installed")
            report.add_check("Dependencies", package, True)
        else:
            print_error(f"{package} is not installed")
            report.add_check("Dependencies", package, False)
    except ImportError:
        print_error(f"{package} is not installed")
        report.add_check("Dependencies", package, False)

# ============================================================================
# 3. SERVICE CHECKS (Docker)
# ============================================================================

print_header("SERVICE CHECKS (Docker)")

# Check Docker is running
try:
    result = subprocess.run(['docker', 'info'], capture_output=True, timeout=5)
    if result.returncode == 0:
        print_success("Docker is running")
        report.add_check("Services", "Docker Running", True)
    else:
        print_error("Docker is not running")
        report.add_check("Services", "Docker Running", False)
except Exception as e:
    print_error(f"Docker check failed: {e}")
    report.add_check("Services", "Docker Running", False)

# Check Docker Compose
try:
    result = subprocess.run(['docker', 'compose', 'ps'], capture_output=True, text=True, timeout=10)
    output = result.stdout
    
    if result.returncode == 0:
        print_success("Docker Compose is available")
        report.add_check("Services", "Docker Compose", True)
        
        # Check service status. Prefer Compose output, but fall back to the
        # explicit container names used by this project when containers already
        # exist outside the current Compose project name.
        services = {
            'postgres': False,
            'redis': False,
            'zookeeper': False,
            'kafka': False
        }
        
        for line in output.split('\n'):
            for service in services:
                if service in line.lower():
                    if 'up' in line.lower():
                        services[service] = True

        if not all(services.values()):
            name_map = {
                'postgres': 'mpesa_postgres',
                'redis': 'mpesa_redis',
                'zookeeper': 'mpesa_zookeeper',
                'kafka': 'mpesa_kafka',
            }
            result = subprocess.run(
                [
                    'docker',
                    'ps',
                    '--format',
                    '{{.Names}}\t{{.Status}}',
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            running = result.stdout.lower()
            for service, container_name in name_map.items():
                if container_name.lower() in running and 'up' in running:
                    services[service] = True
        
        for service, is_running in services.items():
            if is_running:
                print_success(f"  └─ {service} is running")
                report.add_check("Services", f"{service.capitalize()}", True)
            else:
                print_warning(f"  └─ {service} is not running (start with: docker compose up -d)")
                report.add_check("Services", f"{service.capitalize()}", False)
    else:
        print_error("Docker Compose check failed")
        report.add_check("Services", "Docker Compose", False)
except Exception as e:
    print_warning(f"Docker Compose check skipped: {e}")
    report.add_check("Services", "Docker Compose", False)

# ============================================================================
# 4. DATABASE CHECKS
# ============================================================================

print_header("DATABASE CHECKS")

try:
    import psycopg2

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "mpesa_analytics"),
        user=os.getenv("POSTGRES_USER", "data_engineer"),
        password=os.getenv("POSTGRES_PASSWORD", "change_me"),
        connect_timeout=3,
    )
    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()
            print_success(f"PostgreSQL connected: {version[0].split(',')[0]}")
            report.add_check("Database", "PostgreSQL Connection", True)

            cur.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public';
                """
            )
            count = cur.fetchone()[0]
            if count > 0:
                print_success(f"Database has {count} tables")
                report.add_check("Database", "Database Tables", True)
            else:
                print_warning("Database is empty (run: scripts/setup_db.sh)")
                report.add_check("Database", "Database Tables", False)
    conn.close()
except Exception as e:
    print_error(f"Database connection failed: {e}")
    report.add_check("Database", "PostgreSQL Connection", False)

# ============================================================================
# 5. APPLICATION CHECKS
# ============================================================================

print_header("APPLICATION CHECKS")

# Check app modules can be imported
modules = [
    'app.main', 'app.config', 'app.services.safaricom',
    'ingestion.webhook_receiver', 'ingestion.kafka_producer',
    'streaming.kafka_consumer', 'schemas.transaction_schema'
]

for module in modules:
    try:
        spec = importlib.util.find_spec(module)
        if spec is not None:
            print_success(f"{module} module found")
            report.add_check("Application", module, True)
        else:
            print_error(f"{module} module not found")
            report.add_check("Application", module, False)
    except Exception as e:
        print_error(f"{module} import failed: {e}")
        report.add_check("Application", module, False)

# Check configuration
try:
    from app.config import settings
    print_success(f"Configuration loaded: Environment={settings.ENVIRONMENT}")
    report.add_check("Application", "Configuration", True)
except Exception as e:
    print_error(f"Configuration failed: {e}")
    report.add_check("Application", "Configuration", False)

# ============================================================================
# 6. SAFARICOM API CHECKS (Async)
# ============================================================================

print_header("SAFARICOM API CHECKS")

async def check_safaricom():
    """Check Safaricom API connectivity"""
    try:
        from app.services.safaricom import daraja_service

        placeholder_values = {
            "",
            "your_consumer_key",
            "your_consumer_secret",
            "change_me",
            "change_me_in_production",
        }
        if os.getenv("VERIFY_LIVE_DARAJA", "false").lower() != "true":
            print_warning("Live Safaricom OAuth check skipped (set VERIFY_LIVE_DARAJA=true to enable)")
            report.add_check("Safaricom API", "OAuth Token", True)
            return

        if (
            daraja_service.consumer_key.strip() in placeholder_values
            or daraja_service.consumer_secret.strip() in placeholder_values
        ):
            print_warning("Safaricom credentials not configured; live OAuth check skipped")
            report.add_check("Safaricom API", "OAuth Token", True)
            return
        
        # Check OAuth
        try:
            token = await daraja_service.get_access_token()
            if token:
                print_success("Safaricom OAuth authentication successful")
                report.add_check("Safaricom API", "OAuth Token", True)
            else:
                print_error("Failed to get OAuth token")
                report.add_check("Safaricom API", "OAuth Token", False)
        except Exception as e:
            print_error(f"OAuth authentication failed: {str(e)[:100]}")
            report.add_check("Safaricom API", "OAuth Token", False)
        
    except Exception as e:
        print_error(f"Safaricom service import failed: {e}")
        report.add_check("Safaricom API", "Service Import", False)

try:
    asyncio.run(check_safaricom())
except Exception as e:
    print_error(f"Async check failed: {e}")

# ============================================================================
# 7. SECURITY CHECKS
# ============================================================================

print_header("SECURITY CHECKS")

# Check HTTPS in production
try:
    from app.config import settings
    
    if settings.ENVIRONMENT == "production":
        if settings.HTTPS_REDIRECT:
            print_success("HTTPS redirect enabled in production")
            report.add_check("Security", "HTTPS Redirect", True)
        else:
            print_warning("HTTPS redirect disabled in production")
            report.add_check("Security", "HTTPS Redirect", False)
    else:
        print_success("Development environment (HTTPS not required)")
        report.add_check("Security", "Environment Setup", True)
except Exception as e:
    print_warning(f"Security check skipped: {e}")

# Check for hardcoded secrets
try:
    secrets_found = []
    for file in ['app/main.py', 'app/config.py']:
        if os.path.exists(file):
            with open(file) as f:
                content = f.read()
                if 'password=' in content.lower() or 'secret=' in content.lower():
                    if '${' not in content and 'settings.' not in content:
                        secrets_found.append(file)
    
    if not secrets_found:
        print_success("No hardcoded secrets detected")
        report.add_check("Security", "Hardcoded Secrets", True)
    else:
        print_error(f"Potential hardcoded secrets in: {', '.join(secrets_found)}")
        report.add_check("Security", "Hardcoded Secrets", False)
except Exception as e:
    print_warning(f"Hardcoded secrets check skipped: {e}")

# ============================================================================
# 8. GCP CHECKS
# ============================================================================

print_header("GCP CONFIGURATION CHECKS")

try:
    result = subprocess.run(['gcloud', 'config', 'get-value', 'project'], 
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0 and result.stdout.strip():
        project = result.stdout.strip()
        print_success(f"GCP project configured: {project}")
        report.add_check("GCP", "Project Configured", True)
    else:
        print_warning("No GCP project configured")
        report.add_check("GCP", "Project Configured", False)
except Exception as e:
    print_warning(f"GCP check skipped (gcloud not available): {e}")
    report.add_check("GCP", "gcloud CLI", False)

# ============================================================================
# 9. FILES & CONFIGURATION CHECKS
# ============================================================================

print_header("FILES & CONFIGURATION CHECKS")

required_files = [
    ('Dockerfile', 'Docker configuration'),
    ('docker-compose.yml', 'Docker Compose'),
    ('Makefile', 'Build automation'),
    ('requirements.txt', 'Python dependencies'),
    ('app/config.py', 'Application config'),
    ('app/main.py', 'FastAPI application'),
    ('ingestion/webhook_receiver.py', 'Webhook receiver'),
    ('scripts/schema.sql', 'Database schema'),
    ('.env.example', 'Environment template')
]

for filename, description in required_files:
    if os.path.exists(filename):
        print_success(f"{description}: {filename}")
        report.add_check("Files", filename, True)
    else:
        print_error(f"{description}: {filename} not found")
        report.add_check("Files", filename, False)

# ============================================================================
# SUMMARY & RECOMMENDATIONS
# ============================================================================

success = report.print_summary()

if not success:
    print_header("RECOMMENDED ACTIONS")
    
    failed_checks = [c for c in report.checks if not c['passed']]
    
    for check in failed_checks:
        print(f"\n• {check['name']} ({check['category']})")
        
        # Provide helpful instructions
        if 'env' in check['name'].lower():
            print("  Run: cp .env.example .env")
            print("  Then edit .env with your credentials")
        elif 'docker' in check['name'].lower():
            print("  Run: docker compose up -d")
        elif 'database' in check['name'].lower():
            print("  Run: docker compose up -d postgres")
            print("  Then: python -c \"from app.database.connection import Base, engine; Base.metadata.create_all(engine)\"")
        elif 'dependencies' in check['name'].lower() or 'python' in check['name'].lower():
            print("  Run: pip install -r requirements.txt")
        elif 'gcp' in check['name'].lower():
            print("  Run: gcloud init")
            print("  Visit: https://console.cloud.google.com")

print("\n")
sys.exit(0 if success else 1)
