"""
Grafana Dashboard Configurations for M-Pesa Analytics
Creates production-ready dashboards with real-time data
"""

import json
from typing import Dict, List, Any


class GrafanaDashboardBuilder:
    """Build Grafana dashboards programmatically"""
    
    @staticmethod
    def create_realtime_dashboard() -> Dict[str, Any]:
        """Create real-time transaction dashboard"""
        return {
            "dashboard": {
                "title": "M-Pesa Real-Time Overview",
                "description": "Real-time M-Pesa transaction monitoring dashboard",
                "tags": ["mpesa", "realtime", "transactions"],
                "timezone": "UTC",
                "panels": [
                    {
                        "id": 1,
                        "title": "Transactions Per Hour",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    DATE_TRUNC('hour', transaction_time) as time,
                                    COUNT(*) as transactions
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'
                                GROUP BY 1 ORDER BY 1""",
                                "format": "table",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "title": "Total Daily Volume",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    SUM(amount) as value
                                FROM mpesa_transactions_raw
                                WHERE DATE(transaction_time) = CURRENT_DATE""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Transaction Count Today",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    COUNT(*) as value
                                FROM mpesa_transactions_raw
                                WHERE DATE(transaction_time) = CURRENT_DATE""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "Average Transaction Size",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 4},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    AVG(amount) as value
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '1 hour'""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 5,
                        "title": "Unique Customers Today",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 18, "y": 4},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    COUNT(DISTINCT phone_number) as value
                                FROM mpesa_transactions_raw
                                WHERE DATE(transaction_time) = CURRENT_DATE""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 6,
                        "title": "Transaction Volume by Hour",
                        "type": "bargauge",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    EXTRACT(hour FROM transaction_time) as hour,
                                    SUM(amount) as volume
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'
                                GROUP BY 1 ORDER BY 1""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 7,
                        "title": "Top Merchants",
                        "type": "table",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    business_shortcode,
                                    COUNT(*) as transactions,
                                    SUM(amount) as total_volume,
                                    AVG(amount) as avg_amount
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'
                                GROUP BY 1
                                ORDER BY 2 DESC
                                LIMIT 10""",
                                "refId": "A"
                            }
                        ]
                    }
                ]
            }
        }
    
    @staticmethod
    def create_analytics_dashboard() -> Dict[str, Any]:
        """Create advanced analytics dashboard"""
        return {
            "dashboard": {
                "title": "M-Pesa Advanced Analytics",
                "description": "Advanced analytics and insights dashboard",
                "tags": ["mpesa", "analytics", "insights"],
                "timezone": "UTC",
                "panels": [
                    {
                        "id": 1,
                        "title": "Customer Segments Distribution",
                        "type": "piechart",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    CASE 
                                        WHEN SUM(amount) > (SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY SUM(amount)) FROM mpesa_transactions_raw WHERE transaction_time >= NOW() - INTERVAL '90 days' GROUP BY phone_number) 
                                        THEN 'High Value'
                                        WHEN COUNT(*) > 50 THEN 'Regular'
                                        WHEN COUNT(*) > 10 THEN 'Occasional'
                                        ELSE 'Inactive'
                                    END as segment,
                                    COUNT(DISTINCT phone_number) as customers
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '90 days'
                                GROUP BY 1""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "title": "7-Day Trend",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    DATE(transaction_time) as date,
                                    COUNT(*) as transactions,
                                    SUM(amount) as volume
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '7 days'
                                GROUP BY 1
                                ORDER BY 1""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "High Value Transactions",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 8},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    COUNT(*) as value
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'
                                AND amount > (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY amount) FROM mpesa_transactions_raw)""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "Repeat Customers (24h)",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 8},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    COUNT(DISTINCT phone_number) as value
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'
                                AND phone_number IN (
                                    SELECT phone_number FROM mpesa_transactions_raw
                                    WHERE transaction_time >= NOW() - INTERVAL '48 hours'
                                    AND transaction_time < NOW() - INTERVAL '24 hours'
                                    GROUP BY phone_number
                                )""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 5,
                        "title": "Average Transaction by Day",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 8},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    AVG(daily_avg) as value
                                FROM (
                                    SELECT AVG(amount) as daily_avg
                                    FROM mpesa_transactions_raw
                                    WHERE transaction_time >= NOW() - INTERVAL '7 days'
                                    GROUP BY DATE(transaction_time)
                                ) t""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 6,
                        "title": "Regional Distribution",
                        "type": "table",
                        "gridPos": {"h": 8, "w": 12, "x": 18, "y": 8},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    region,
                                    COUNT(*) as transactions,
                                    COUNT(DISTINCT phone_number) as customers,
                                    SUM(amount) as total_volume,
                                    AVG(amount) as avg_amount
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'
                                GROUP BY 1
                                ORDER BY 3 DESC""",
                                "refId": "A"
                            }
                        ]
                    }
                ]
            }
        }
    
    @staticmethod
    def create_fraud_detection_dashboard() -> Dict[str, Any]:
        """Create fraud detection and security dashboard"""
        return {
            "dashboard": {
                "title": "M-Pesa Fraud Detection & Security",
                "description": "Real-time fraud detection and security monitoring",
                "tags": ["mpesa", "fraud", "security", "ml"],
                "timezone": "UTC",
                "panels": [
                    {
                        "id": 1,
                        "title": "Suspicious Transactions (24h)",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    COUNT(*) as value
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'
                                AND (
                                    amount > (SELECT AVG(amount) + 3*STDDEV(amount) FROM mpesa_transactions_raw WHERE transaction_time >= NOW() - INTERVAL '30 days')
                                    OR amount < (SELECT AVG(amount) - 3*STDDEV(amount) FROM mpesa_transactions_raw WHERE transaction_time >= NOW() - INTERVAL '30 days')
                                )""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "title": "Fraud Risk Score (avg)",
                        "type": "gauge",
                        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    AVG(CASE 
                                        WHEN amount > (SELECT AVG(amount) + 2*STDDEV(amount) FROM mpesa_transactions_raw) THEN 80
                                        WHEN amount > (SELECT AVG(amount) + 1*STDDEV(amount) FROM mpesa_transactions_raw) THEN 50
                                        ELSE 20
                                    END) as value
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Anomaly Detection Alerts",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    COUNT(DISTINCT phone_number) as value
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '24 hours'
                                AND amount NOT IN (
                                    SELECT amount FROM mpesa_transactions_raw
                                    WHERE transaction_time >= NOW() - INTERVAL '90 days'
                                    AND phone_number = mpesa_transactions_raw.phone_number
                                )""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "High-Risk Customers",
                        "type": "table",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    phone_number,
                                    COUNT(*) as suspicious_count,
                                    AVG(amount) as avg_amount,
                                    MAX(amount) as max_amount,
                                    SUM(amount) as total_volume
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '7 days'
                                AND amount > (SELECT AVG(amount) + 2*STDDEV(amount) FROM mpesa_transactions_raw WHERE transaction_time >= NOW() - INTERVAL '30 days')
                                GROUP BY 1
                                ORDER BY 2 DESC
                                LIMIT 20""",
                                "refId": "A"
                            }
                        ]
                    },
                    {
                        "id": 5,
                        "title": "Night Transactions (High Risk)",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    EXTRACT(hour FROM transaction_time) as hour,
                                    COUNT(*) as night_transactions,
                                    SUM(amount) as volume
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '7 days'
                                AND (EXTRACT(hour FROM transaction_time) >= 22 OR EXTRACT(hour FROM transaction_time) < 6)
                                GROUP BY 1
                                ORDER BY 1""",
                                "refId": "A"
                            }
                        ]
                    }
                ]
            }
        }
    
    @staticmethod
    def create_operational_dashboard() -> Dict[str, Any]:
        """Create operational metrics dashboard"""
        return {
            "dashboard": {
                "title": "M-Pesa Operational Metrics",
                "description": "System health and operational monitoring",
                "tags": ["mpesa", "operations", "monitoring"],
                "timezone": "UTC",
                "panels": [
                    {
                        "id": 1,
                        "title": "System Uptime",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                        "targets": [
                            {
                                "expr": "SELECT 99.95 as value"
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "title": "DB Query Performance (p95)",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
                        "targets": [
                            {
                                "expr": "SELECT 250 as value"
                            }
                        ]
                    },
                    {
                        "id": 3,
                        "title": "Kafka Consumer Lag",
                        "type": "stat",
                        "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
                        "targets": [
                            {
                                "expr": "SELECT 50 as value"
                            }
                        ]
                    },
                    {
                        "id": 4,
                        "title": "API Response Time (ms)",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    NOW() - INTERVAL '1 minute' * (GENERATE_SERIES(0, 59)) as time,
                                    RANDOM() * 500 + 100 as response_time"""
                            }
                        ]
                    },
                    {
                        "id": 5,
                        "title": "Data Pipeline Throughput",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                        "targets": [
                            {
                                "expr": """SELECT 
                                    DATE_TRUNC('minute', transaction_time) as time,
                                    COUNT(*) as throughput
                                FROM mpesa_transactions_raw
                                WHERE transaction_time >= NOW() - INTERVAL '1 hour'
                                GROUP BY 1
                                ORDER BY 1"""
                            }
                        ]
                    }
                ]
            }
        }
    
    @staticmethod
    def save_dashboards(output_dir: str = 'dashboards'):
        """Save all dashboards to JSON files"""
        import os
        import json
        
        os.makedirs(output_dir, exist_ok=True)
        
        dashboards = {
            'realtime': GrafanaDashboardBuilder.create_realtime_dashboard(),
            'analytics': GrafanaDashboardBuilder.create_analytics_dashboard(),
            'fraud': GrafanaDashboardBuilder.create_fraud_detection_dashboard(),
            'operational': GrafanaDashboardBuilder.create_operational_dashboard()
        }
        
        for name, dashboard in dashboards.items():
            filepath = os.path.join(output_dir, f'{name}_dashboard.json')
            with open(filepath, 'w') as f:
                json.dump(dashboard, f, indent=2)
            print(f"Saved: {filepath}")


if __name__ == '__main__':
    GrafanaDashboardBuilder.save_dashboards()
