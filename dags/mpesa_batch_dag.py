"""Airflow DAG for hourly dbt data transformation refresh.

Schedules dbt run and tests for M-Pesa data marts on an hourly basis.
Ensures data warehouse stays up-to-date with latest transactional data.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="mpesa_batch_dbt_refresh",
    default_args=default_args,
    description="Hourly dbt refresh and tests for M-Pesa marts",
    start_date=datetime(2026, 1, 1),
    schedule="0 * * * *",
    catchup=False,
    max_active_runs=1,
) as dag:
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="dbt run --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="dbt test --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt",
    )

    dbt_run >> dbt_test
