"""
Advanced Fraud Detection ML Pipeline
Uses multiple ML algorithms for real-time fraud detection
"""

import pandas as pd
import numpy as np
from datetime import datetime
import psycopg2
import logging
from typing import Dict, Tuple, Any
from dotenv import load_dotenv
import os
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import (
    IsolationForest,
    RandomForestClassifier,
    GradientBoostingClassifier,
)
from sklearn.model_selection import train_test_split
import pickle
import json
from pathlib import Path

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FraudDetectionEngine:
    """Advanced fraud detection using ML"""

    def __init__(self, model_dir: str = "models"):
        """Initialize fraud detection engine"""
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5433)),
            "database": os.getenv("DB_NAME", "mpesa_analytics"),
            "user": os.getenv("DB_USER", "data_engineer"),
            "password": os.getenv("DB_PASSWORD", "change_me"),
        }

        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)

        self.conn = None
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(contamination=0.01, random_state=42)
        self.random_forest = None
        self.gradient_boosting = None

        self._connect()
        self._load_models()

    def _connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("Connected to fraud detection database")
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _load_models(self):
        """Load trained models if they exist"""
        try:
            if (self.model_dir / "isolation_forest.pkl").exists():
                with open(self.model_dir / "isolation_forest.pkl", "rb") as f:
                    self.isolation_forest = pickle.load(f)
                logger.info("Loaded Isolation Forest model")

            if (self.model_dir / "random_forest.pkl").exists():
                with open(self.model_dir / "random_forest.pkl", "rb") as f:
                    self.random_forest = pickle.load(f)
                logger.info("Loaded Random Forest model")

            if (self.model_dir / "gradient_boosting.pkl").exists():
                with open(self.model_dir / "gradient_boosting.pkl", "rb") as f:
                    self.gradient_boosting = pickle.load(f)
                logger.info("Loaded Gradient Boosting model")
        except Exception as e:
            logger.warning(f"Could not load models: {e}")

    def extract_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Extract fraud detection features"""
        df = df.copy()

        # Basic statistics
        df["amount_log"] = np.log1p(df["amount"])
        df["is_round_amount"] = (df["amount"] % 1 == 0).astype(int)
        df["is_very_high_amount"] = (df["amount"] > df["amount"].quantile(0.95)).astype(
            int
        )
        df["is_very_low_amount"] = (df["amount"] < df["amount"].quantile(0.05)).astype(
            int
        )

        # Time-based features
        df["transaction_time"] = pd.to_datetime(df["transaction_time"])
        df["hour_of_day"] = df["transaction_time"].dt.hour
        df["day_of_week"] = df["transaction_time"].dt.dayofweek
        df["is_night_transaction"] = (
            (df["hour_of_day"] >= 22) | (df["hour_of_day"] < 6)
        ).astype(int)
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

        # Phone number features
        df["phone_prefix"] = df["phone_number"].str[:4]
        df["phone_length"] = df["phone_number"].str.len()

        # Customer behavior features (per phone)
        customer_stats = (
            df.groupby("phone_number")
            .agg(
                {
                    "amount": ["mean", "std", "min", "max", "count"],
                    "transaction_time": "nunique",
                }
            )
            .reset_index()
        )

        customer_stats.columns = [
            "phone_number",
            "customer_avg_amount",
            "customer_std_amount",
            "customer_min_amount",
            "customer_max_amount",
            "customer_transaction_count",
            "unique_times",
        ]

        df = df.merge(customer_stats, on="phone_number", how="left")

        # Deviation features
        df["amount_deviation"] = np.abs(df["amount"] - df["customer_avg_amount"]) / (
            df["customer_std_amount"] + 1
        )
        df["amount_deviation"] = df["amount_deviation"].fillna(0)

        # Merchant features
        merchant_stats = (
            df.groupby("business_shortcode")
            .agg({"amount": ["mean", "count"], "phone_number": "nunique"})
            .reset_index()
        )

        merchant_stats.columns = [
            "business_shortcode",
            "merchant_avg_amount",
            "merchant_transaction_count",
            "merchant_unique_customers",
        ]

        df = df.merge(merchant_stats, on="business_shortcode", how="left")

        # Regional features
        df["region_risk_factor"] = (
            df["region"]
            .map(
                {
                    "Nairobi": 0.3,
                    "Central": 0.2,
                    "Coast": 0.25,
                    "Western": 0.15,
                    "Eastern": 0.2,
                    "Rift Valley": 0.18,
                    "Nyanza": 0.17,
                    "Unknown": 0.5,
                }
            )
            .fillna(0.3)
        )

        # Select feature columns
        feature_cols = [
            "amount_log",
            "is_round_amount",
            "is_very_high_amount",
            "is_very_low_amount",
            "hour_of_day",
            "day_of_week",
            "is_night_transaction",
            "is_weekend",
            "phone_length",
            "customer_avg_amount",
            "customer_transaction_count",
            "amount_deviation",
            "merchant_avg_amount",
            "merchant_transaction_count",
            "region_risk_factor",
        ]

        # Handle missing values
        for col in feature_cols:
            if col not in df.columns:
                df[col] = 0
            df[col] = df[col].fillna(df[col].mean())

        features = df[feature_cols]
        features = features.fillna(0)

        return df, features

    def train_models(self, days: int = 30):
        """Train fraud detection models"""
        logger.info("Training fraud detection models...")

        query = (
            """
        SELECT
            transaction_id, phone_number, amount, transaction_time,
            business_shortcode, region, payment_method
        FROM mpesa_transactions_raw
        WHERE transaction_time >= NOW() - INTERVAL '%d days'
        """
            % days
        )

        df = pd.read_sql_query(query, self.conn)

        if df.empty:
            logger.warning("No transactions found for training")
            return

        # Extract features
        df, features = self.extract_features(df)

        # Train Isolation Forest (unsupervised)
        logger.info("Training Isolation Forest...")
        self.isolation_forest.fit(features)
        df["isolation_forest_score"] = self.isolation_forest.score_samples(features)
        df["isolation_forest_pred"] = self.isolation_forest.predict(features)

        # Convert isolation forest output (-1 anomaly, 1 normal) to binary fraud labels.
        y = (df["isolation_forest_pred"] == -1).astype(int)

        # Add manual fraud indicators (if available)
        df["is_fraud"] = 0

        # Train Random Forest (supervised)
        if y.sum() > 10:  # Need at least 10 positive samples
            logger.info("Training Random Forest...")
            X_train, X_test, y_train, y_test = train_test_split(
                features, y, test_size=0.2, random_state=42
            )

            self.random_forest = RandomForestClassifier(
                n_estimators=100, random_state=42, n_jobs=-1
            )
            self.random_forest.fit(X_train, y_train)

            train_score = self.random_forest.score(X_train, y_train)
            test_score = self.random_forest.score(X_test, y_test)
            logger.info(
                f"Random Forest - Train: {train_score:.4f}, Test: {test_score:.4f}"
            )

        # Train Gradient Boosting
        if y.sum() > 10:
            logger.info("Training Gradient Boosting...")
            X_train, X_test, y_train, y_test = train_test_split(
                features, y, test_size=0.2, random_state=42
            )

            self.gradient_boosting = GradientBoostingClassifier(
                n_estimators=100, random_state=42
            )
            self.gradient_boosting.fit(X_train, y_train)

            train_score = self.gradient_boosting.score(X_train, y_train)
            test_score = self.gradient_boosting.score(X_test, y_test)
            logger.info(
                f"Gradient Boosting - Train: {train_score:.4f}, Test: {test_score:.4f}"
            )

        # Save models
        self._save_models()

        logger.info("Model training completed")

    def _save_models(self):
        """Save trained models"""
        try:
            with open(self.model_dir / "isolation_forest.pkl", "wb") as f:
                pickle.dump(self.isolation_forest, f)

            if self.random_forest:
                with open(self.model_dir / "random_forest.pkl", "wb") as f:
                    pickle.dump(self.random_forest, f)

            if self.gradient_boosting:
                with open(self.model_dir / "gradient_boosting.pkl", "wb") as f:
                    pickle.dump(self.gradient_boosting, f)

            logger.info("Models saved successfully")
        except Exception as e:
            logger.error(f"Error saving models: {e}")

    def predict_fraud(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Predict fraud probability for a transaction"""

        # Create dataframe with single transaction
        df = pd.DataFrame([transaction])

        try:
            # Extract features
            df, features = self.extract_features(df)

            # Get predictions from all models
            predictions = {
                "timestamp": datetime.utcnow().isoformat(),
                "transaction_id": transaction.get("transaction_id"),
                "phone_number": transaction.get("phone_number"),
                "amount": transaction.get("amount"),
                "models": {},
            }

            # Isolation Forest
            iso_pred = self.isolation_forest.predict(features)[0]
            iso_score = self.isolation_forest.score_samples(features)[0]
            predictions["models"]["isolation_forest"] = {
                "prediction": "fraud" if iso_pred == -1 else "normal",
                "score": float(iso_score),
                "confidence": float(np.abs(iso_score)),
            }

            # Random Forest
            if self.random_forest:
                rf_pred = self.random_forest.predict(features)[0]
                rf_proba = self.random_forest.predict_proba(features)[0]
                predictions["models"]["random_forest"] = {
                    "prediction": "fraud" if rf_pred == 1 else "normal",
                    "confidence": float(rf_proba[1]),
                    "probability": float(rf_proba[1]),
                }

            # Gradient Boosting
            if self.gradient_boosting:
                gb_pred = self.gradient_boosting.predict(features)[0]
                gb_proba = self.gradient_boosting.predict_proba(features)[0]
                predictions["models"]["gradient_boosting"] = {
                    "prediction": "fraud" if gb_pred == 1 else "normal",
                    "confidence": float(gb_proba[1]),
                    "probability": float(gb_proba[1]),
                }

            # Ensemble decision (voting)
            fraud_votes = sum(
                1
                for m in predictions["models"].values()
                if m.get("prediction") == "fraud"
            )
            total_votes = len(predictions["models"])

            predictions["ensemble"] = {
                "fraud_risk": "high" if fraud_votes > total_votes / 2 else "low",
                "fraud_probability": float(fraud_votes / total_votes),
                "consensus_votes": fraud_votes,
            }

            # Risk level
            if fraud_votes > total_votes / 2:
                predictions["risk_level"] = "HIGH"
            elif fraud_votes > 0:
                predictions["risk_level"] = "MEDIUM"
            else:
                predictions["risk_level"] = "LOW"

            return predictions

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                "error": str(e),
                "transaction_id": transaction.get("transaction_id"),
                "risk_level": "UNKNOWN",
            }

    def batch_fraud_detection(self, days: int = 7) -> Dict[str, Any]:
        """Run fraud detection on recent transactions"""
        logger.info("Running batch fraud detection...")

        query = (
            """
        SELECT
            transaction_id, phone_number, amount, transaction_time,
            business_shortcode, region, payment_method
        FROM mpesa_transactions_raw
        WHERE transaction_time >= NOW() - INTERVAL '%d days'
        LIMIT 10000
        """
            % days
        )

        df = pd.read_sql_query(query, self.conn)

        if df.empty:
            return {}

        # Extract features
        df, features = self.extract_features(df)

        # Get predictions
        predictions = self.isolation_forest.predict(features)
        scores = self.isolation_forest.score_samples(features)

        df["fraud_prediction"] = predictions
        df["fraud_score"] = scores
        df["is_suspicious"] = (predictions == -1).astype(int)

        # Summary statistics
        total_transactions = len(df)
        suspicious_count = df["is_suspicious"].sum()
        suspicious_percentage = (suspicious_count / total_transactions * 100).round(2)

        # Find high-risk customers
        high_risk_customers = (
            df[df["is_suspicious"] == 1]
            .groupby("phone_number")
            .agg({"transaction_id": "count", "amount": "sum", "fraud_score": "mean"})
            .rename(columns={"transaction_id": "suspicious_count"})
            .reset_index()
        )

        high_risk_customers = high_risk_customers.nlargest(10, "suspicious_count")

        return {
            "total_transactions": total_transactions,
            "suspicious_transactions": int(suspicious_count),
            "suspicious_percentage": suspicious_percentage,
            "high_risk_customers": high_risk_customers[
                ["phone_number", "suspicious_count", "amount"]
            ].to_dict("records"),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    """Main execution"""
    try:
        engine = FraudDetectionEngine()

        # Train models
        engine.train_models(days=30)

        # Run batch detection
        results = engine.batch_fraud_detection(days=7)
        print(json.dumps(results, indent=2, default=str))

        engine.close()
    except Exception as e:
        logger.error(f"Fraud detection error: {e}")


if __name__ == "__main__":
    main()
