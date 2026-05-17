"""
Advanced Analytics Engine for M-Pesa Data
Includes customer segmentation, behavior analysis, and predictive analytics
"""

import pandas as pd
import numpy as np
from datetime import datetime
import psycopg2
import logging
from typing import Dict, Any
from dotenv import load_dotenv
import os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import json

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AdvancedAnalyticsEngine:
    """Advanced analytics for M-Pesa transactions"""

    def __init__(self):
        """Initialize analytics engine"""
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5433)),
            "database": os.getenv("DB_NAME", "mpesa_analytics"),
            "user": os.getenv("DB_USER", "data_engineer"),
            "password": os.getenv("DB_PASSWORD", "change_me"),
        }
        self.conn = None
        self._connect()

    def _connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to analytics database")
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def get_transactions(self, days: int = 30) -> pd.DataFrame:
        """Fetch transactions for analysis"""
        query = (
            """
        SELECT
            transaction_id, phone_number, amount, transaction_time,
            business_shortcode, region, reference, payment_method
        FROM mpesa_transactions_raw
        WHERE transaction_time >= NOW() - INTERVAL '%d days'
        ORDER BY transaction_time DESC
        """
            % days
        )

        return pd.read_sql_query(query, self.conn)

    def customer_segmentation(self, n_clusters: int = 5) -> Dict[str, Any]:
        """Segment customers based on behavior"""
        logger.info("Running customer segmentation...")

        # Get customer metrics
        query = """
        SELECT
            phone_number,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount,
            MAX(amount) as max_amount,
            MIN(amount) as min_amount,
            STDDEV(amount) as std_amount,
            DATE_TRUNC('day', transaction_time)::date as last_transaction_date
        FROM mpesa_transactions_raw
        WHERE transaction_time >= NOW() - INTERVAL '90 days'
        GROUP BY phone_number, last_transaction_date
        ORDER BY total_amount DESC
        LIMIT 10000
        """

        df = pd.read_sql_query(query, self.conn)

        if df.empty:
            logger.warning("No transactions found for segmentation")
            return {}

        # Fill NaN values
        df = df.fillna(0)

        # Feature engineering
        df["avg_transaction_value"] = df["total_amount"] / df["transaction_count"]
        df["transaction_frequency"] = df["transaction_count"] / 90  # per day
        df["volatility"] = df["std_amount"] / (
            df["avg_amount"] + 1
        )  # Avoid division by zero
        df["customer_value_score"] = (
            (df["total_amount"] / df["total_amount"].max()) * 0.5
            + (df["transaction_count"] / df["transaction_count"].max()) * 0.3
            + (df["avg_amount"] / df["avg_amount"].max()) * 0.2
        )

        # Prepare features for clustering
        features = df[
            ["transaction_count", "total_amount", "avg_amount", "volatility"]
        ].copy()

        # Normalize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)

        # K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df["segment"] = kmeans.fit_predict(features_scaled)

        # Map segment names
        segment_names = {
            0: "High Value",
            1: "Regular",
            2: "Occasional",
            3: "New",
            4: "Inactive",
        }
        df["segment_name"] = df["segment"].map(segment_names)

        # Calculate segment statistics
        segment_stats = (
            df.groupby("segment_name")
            .agg(
                {
                    "phone_number": "count",
                    "transaction_count": "mean",
                    "total_amount": ["mean", "median", "std"],
                    "avg_amount": "mean",
                    "customer_value_score": "mean",
                }
            )
            .round(2)
        )

        logger.info(f"Segmented {len(df)} customers into {n_clusters} segments")

        return {
            "segments": df[
                ["phone_number", "segment_name", "customer_value_score"]
            ].to_dict("records"),
            "statistics": segment_stats.to_dict(),
            "segment_distribution": df["segment_name"].value_counts().to_dict(),
        }

    def behavior_analysis(self) -> Dict[str, Any]:
        """Analyze customer transaction behavior"""
        logger.info("Analyzing transaction behavior...")

        query = """
        SELECT
            phone_number,
            DATE_TRUNC('hour', transaction_time) as transaction_hour,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount
        FROM mpesa_transactions_raw
        WHERE transaction_time >= NOW() - INTERVAL '7 days'
        GROUP BY phone_number, transaction_hour
        ORDER BY transaction_hour DESC
        """

        df = pd.read_sql_query(query, self.conn)

        if df.empty:
            return {}

        # Extract time features
        df["hour_of_day"] = df["transaction_hour"].dt.hour
        df["day_of_week"] = df["transaction_hour"].dt.dayofweek

        # Peak hours analysis
        peak_hours = df.groupby("hour_of_day")["transaction_count"].sum().nlargest(3)

        # Daily pattern
        daily_pattern = (
            df.groupby("day_of_week")
            .agg(
                {
                    "transaction_count": "sum",
                    "total_amount": "sum",
                    "phone_number": "nunique",
                }
            )
            .round(2)
        )

        return {
            "peak_hours": peak_hours.to_dict(),
            "daily_pattern": daily_pattern.to_dict(),
            "avg_transaction_per_hour": df["transaction_count"].mean().round(2),
            "peak_volume_hour": int(peak_hours.idxmax()),
        }

    def anomaly_detection(self, threshold: float = 2.5) -> Dict[str, Any]:
        """Detect unusual transaction patterns"""
        logger.info("Detecting anomalies...")

        df = self.get_transactions(days=30)

        if df.empty:
            return {}

        # Calculate statistics per phone number
        customer_stats = (
            df.groupby("phone_number")
            .agg({"amount": ["mean", "std", "count"]})
            .round(2)
        )

        customer_stats.columns = ["mean_amount", "std_amount", "transaction_count"]
        customer_stats = customer_stats.reset_index()

        # Merge back to original dataframe
        df = df.merge(customer_stats, on="phone_number")

        # Calculate z-score
        df["amount_zscore"] = np.abs(
            (df["amount"] - df["mean_amount"]) / (df["std_amount"] + 1)
        )

        # Find anomalies
        anomalies = df[df["amount_zscore"] > threshold].copy()
        anomalies["anomaly_type"] = anomalies["amount_zscore"].apply(
            lambda x: "Unusually High" if x > threshold else "Unusually Low"
        )

        logger.info(f"Detected {len(anomalies)} anomalies")

        return {
            "total_anomalies": len(anomalies),
            "anomaly_percentage": (len(anomalies) / len(df) * 100).round(2),
            "anomalies": anomalies[
                ["transaction_id", "phone_number", "amount", "amount_zscore"]
            ]
            .head(100)
            .to_dict("records"),
            "anomaly_summary": {
                "High": len(anomalies[anomalies["amount"] > anomalies["mean_amount"]]),
                "Low": len(anomalies[anomalies["amount"] < anomalies["mean_amount"]]),
            },
        }

    def transaction_forecasting(self) -> Dict[str, Any]:
        """Forecast future transaction volumes"""
        logger.info("Forecasting transaction volumes...")

        query = """
        SELECT
            DATE_TRUNC('day', transaction_time)::date as transaction_date,
            COUNT(*) as transaction_count,
            SUM(amount) as daily_volume
        FROM mpesa_transactions_raw
        WHERE transaction_time >= NOW() - INTERVAL '90 days'
        GROUP BY transaction_date
        ORDER BY transaction_date
        """

        df = pd.read_sql_query(query, self.conn)

        if len(df) < 7:
            return {}

        # Simple moving average forecast
        df["ma_7"] = df["transaction_count"].rolling(window=7).mean()
        df["ma_14"] = df["transaction_count"].rolling(window=14).mean()

        # Trend calculation
        recent_trend = df.tail(7)["transaction_count"].mean()
        previous_trend = df.iloc[-14:-7]["transaction_count"].mean()
        trend_direction = "up" if recent_trend > previous_trend else "down"

        # Next day forecast (simple average)
        next_day_forecast = df.tail(7)["transaction_count"].mean()

        return {
            "current_trend": trend_direction,
            "next_day_forecast": int(next_day_forecast),
            "recent_average": int(recent_trend),
            "forecast_confidence": "Medium",
            "moving_averages": {
                "7_day": df.tail(1)["ma_7"].values[0],
                "14_day": df.tail(1)["ma_14"].values[0],
            },
        }

    def regional_analysis(self) -> Dict[str, Any]:
        """Analyze transactions by region"""
        logger.info("Running regional analysis...")

        query = """
        SELECT
            region,
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount,
            COUNT(DISTINCT phone_number) as unique_customers
        FROM mpesa_transactions_raw
        WHERE transaction_time >= NOW() - INTERVAL '30 days'
            AND region IS NOT NULL
        GROUP BY region
        ORDER BY total_amount DESC
        """

        df = pd.read_sql_query(query, self.conn)

        if df.empty:
            return {}

        # Calculate percentages
        df["transaction_percentage"] = (
            df["transaction_count"] / df["transaction_count"].sum() * 100
        ).round(2)
        df["volume_percentage"] = (
            df["total_amount"] / df["total_amount"].sum() * 100
        ).round(2)

        return {
            "regions": df.to_dict("records"),
            "top_regions": df.nlargest(5, "total_amount")[
                ["region", "transaction_count", "total_amount"]
            ].to_dict("records"),
            "regional_variance": df["avg_amount"].std().round(2),
            "top_region": df.iloc[0]["region"] if not df.empty else None,
        }

    def generate_analytics_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        logger.info("Generating analytics report...")

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "customer_segmentation": self.customer_segmentation(),
            "behavior_analysis": self.behavior_analysis(),
            "anomaly_detection": self.anomaly_detection(),
            "forecasting": self.transaction_forecasting(),
            "regional_analysis": self.regional_analysis(),
        }

        logger.info("Analytics report generated successfully")
        return report

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    """Main execution"""
    try:
        engine = AdvancedAnalyticsEngine()
        report = engine.generate_analytics_report()

        # Print report
        print(json.dumps(report, indent=2, default=str))

        engine.close()
    except Exception as e:
        logger.error(f"Analytics error: {e}")


if __name__ == "__main__":
    main()
