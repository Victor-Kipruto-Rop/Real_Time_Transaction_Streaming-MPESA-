"""
Generate provisioned Grafana dashboards for the M-Pesa streaming pipeline.

The dashboards are intentionally backed by Postgres/dbt models, not static
fixtures, so they can be used for local validation and production operations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


DATASOURCE_UID = "mpesa-postgres"
DEFAULT_OUTPUT_DIR = Path("grafana/dashboards")
DEFAULT_PROVISIONING_DIR = Path("grafana/provisioning")


def datasource_ref() -> Dict[str, str]:
    return {"type": "postgres", "uid": DATASOURCE_UID}


def sql_target(raw_sql: str, ref_id: str = "A", fmt: str = "table") -> Dict[str, Any]:
    return {
        "datasource": datasource_ref(),
        "editorMode": "code",
        "format": fmt,
        "rawQuery": True,
        "rawSql": raw_sql.strip(),
        "refId": ref_id,
    }


def grid(x: int, y: int, w: int, h: int) -> Dict[str, int]:
    return {"x": x, "y": y, "w": w, "h": h}


def defaults(unit: str | None = None, decimals: int | None = None) -> Dict[str, Any]:
    custom: Dict[str, Any] = {"hideFrom": {"tooltip": False, "viz": False, "legend": False}}
    field: Dict[str, Any] = {"custom": custom}
    if unit:
        field["unit"] = unit
    if decimals is not None:
        field["decimals"] = decimals
    return field


def panel(
    panel_id: int,
    title: str,
    panel_type: str,
    position: Dict[str, int],
    query: str,
    *,
    description: str = "",
    fmt: str = "table",
    unit: str | None = None,
    decimals: int | None = None,
    options: Dict[str, Any] | None = None,
    overrides: Sequence[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    return {
        "id": panel_id,
        "title": title,
        "description": description,
        "type": panel_type,
        "datasource": datasource_ref(),
        "gridPos": position,
        "fieldConfig": {
            "defaults": defaults(unit=unit, decimals=decimals),
            "overrides": list(overrides or []),
        },
        "options": options or {},
        "targets": [sql_target(query, fmt=fmt)],
    }


def stat_panel(
    panel_id: int,
    title: str,
    position: Dict[str, int],
    query: str,
    *,
    unit: str | None = None,
    decimals: int | None = None,
    description: str = "",
) -> Dict[str, Any]:
    return panel(
        panel_id,
        title,
        "stat",
        position,
        query,
        description=description,
        unit=unit,
        decimals=decimals,
        options={
            "colorMode": "background",
            "graphMode": "area",
            "justifyMode": "auto",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
            "wideLayout": True,
        },
    )


def timeseries_panel(
    panel_id: int,
    title: str,
    position: Dict[str, int],
    query: str,
    *,
    unit: str | None = None,
    decimals: int | None = None,
    description: str = "",
) -> Dict[str, Any]:
    return panel(
        panel_id,
        title,
        "timeseries",
        position,
        query,
        description=description,
        fmt="time_series",
        unit=unit,
        decimals=decimals,
        options={
            "legend": {"calcs": ["lastNotNull", "max"], "displayMode": "table", "placement": "bottom"},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    )


def table_panel(
    panel_id: int,
    title: str,
    position: Dict[str, int],
    query: str,
    *,
    description: str = "",
    unit: str | None = None,
) -> Dict[str, Any]:
    return panel(
        panel_id,
        title,
        "table",
        position,
        query,
        description=description,
        unit=unit,
        options={
            "cellHeight": "sm",
            "footer": {"countRows": False, "fields": "", "reducer": ["sum"], "show": False},
            "showHeader": True,
        },
    )


def bar_panel(
    panel_id: int,
    title: str,
    position: Dict[str, int],
    query: str,
    *,
    unit: str | None = None,
    description: str = "",
) -> Dict[str, Any]:
    return panel(
        panel_id,
        title,
        "barchart",
        position,
        query,
        description=description,
        unit=unit,
        options={
            "barWidth": 0.78,
            "groupWidth": 0.7,
            "legend": {"displayMode": "list", "placement": "bottom"},
            "orientation": "auto",
            "showValue": "auto",
            "tooltip": {"mode": "single", "sort": "none"},
            "xTickLabelRotation": 0,
        },
    )


def pie_panel(
    panel_id: int,
    title: str,
    position: Dict[str, int],
    query: str,
    *,
    description: str = "",
) -> Dict[str, Any]:
    return panel(
        panel_id,
        title,
        "piechart",
        position,
        query,
        description=description,
        options={
            "displayLabels": ["name", "percent"],
            "legend": {"displayMode": "table", "placement": "right", "values": ["value", "percent"]},
            "pieType": "donut",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": True},
            "tooltip": {"mode": "single", "sort": "desc"},
        },
    )


def dashboard(
    uid: str,
    title: str,
    description: str,
    tags: Sequence[str],
    panels: Sequence[Dict[str, Any]],
    *,
    refresh: str = "30s",
    time_from: str = "now-24h",
) -> Dict[str, Any]:
    return {
        "annotations": {"list": []},
        "description": description,
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "liveNow": True,
        "panels": list(panels),
        "refresh": refresh,
        "schemaVersion": 39,
        "style": "dark",
        "tags": list(tags),
        "templating": {
            "list": [
                {
                    "current": {"selected": False, "text": "All", "value": "$__all"},
                    "datasource": datasource_ref(),
                    "definition": (
                        "select distinct coalesce(account_reference, 'Unassigned') "
                        "from public_staging.stg_c2b_transactions order by 1"
                    ),
                    "hide": 0,
                    "includeAll": True,
                    "label": "Account Reference",
                    "multi": True,
                    "name": "account_reference",
                    "options": [],
                    "query": (
                        "select distinct coalesce(account_reference, 'Unassigned') "
                        "from public_staging.stg_c2b_transactions order by 1"
                    ),
                    "refresh": 2,
                    "type": "query",
                }
            ]
        },
        "time": {"from": time_from, "to": "now"},
        "timezone": "browser",
        "title": title,
        "uid": uid,
        "version": 1,
        "weekStart": "monday",
    }


ACCOUNT_FILTER = """
and (
  '$account_reference' = '$__all'
  or coalesce(account_reference, 'Unassigned') in (${account_reference:sqlstring})
)
"""


class GrafanaDashboardBuilder:
    """Build use-case specific Grafana dashboards."""

    @staticmethod
    def executive_dashboard() -> Dict[str, Any]:
        panels = [
            stat_panel(
                1,
                "Total Value Today",
                grid(0, 0, 6, 4),
                f"""
                select coalesce(sum(transaction_amount), 0) as value
                from public_staging.stg_c2b_transactions
                where transaction_date = current_date
                {ACCOUNT_FILTER}
                """,
                unit="currency:KES",
                decimals=0,
            ),
            stat_panel(
                2,
                "Transactions Today",
                grid(6, 0, 6, 4),
                f"""
                select count(*) as value
                from public_staging.stg_c2b_transactions
                where transaction_date = current_date
                {ACCOUNT_FILTER}
                """,
                decimals=0,
            ),
            stat_panel(
                3,
                "Active Customers Today",
                grid(12, 0, 6, 4),
                f"""
                select count(distinct customer_phone_number) as value
                from public_staging.stg_c2b_transactions
                where transaction_date = current_date
                {ACCOUNT_FILTER}
                """,
                decimals=0,
            ),
            stat_panel(
                4,
                "Average Ticket Today",
                grid(18, 0, 6, 4),
                f"""
                select coalesce(avg(transaction_amount), 0) as value
                from public_staging.stg_c2b_transactions
                where transaction_date = current_date
                {ACCOUNT_FILTER}
                """,
                unit="currency:KES",
                decimals=0,
            ),
            timeseries_panel(
                5,
                "Value and Transactions by Hour",
                grid(0, 4, 16, 8),
                f"""
                select
                  hour_bucket as time,
                  sum(total_amount) as value_kes,
                  sum(transaction_count) as transactions
                from public_marts.mart_hourly_volumes h
                left join public_staging.stg_c2b_transactions s
                  on date_trunc('hour', s.transaction_timestamp) = h.hour_bucket
                where $__timeFilter(hour_bucket)
                {ACCOUNT_FILTER}
                group by 1
                order by 1
                """,
                unit="short",
                decimals=0,
            ),
            pie_panel(
                6,
                "Value Mix by Amount Band",
                grid(16, 4, 8, 8),
                f"""
                select amount_category as band, sum(transaction_amount) as value
                from public_staging.stg_c2b_transactions
                where $__timeFilter(transaction_timestamp)
                {ACCOUNT_FILTER}
                group by 1
                order by 2 desc
                """,
            ),
            table_panel(
                7,
                "Top Account References",
                grid(0, 12, 12, 8),
                """
                select
                  coalesce(account_reference, 'Unassigned') as account_reference,
                  sum(transaction_count) as transactions,
                  sum(total_amount) as value_kes,
                  round(avg(total_amount / nullif(transaction_count, 0)), 2) as avg_ticket
                from public_marts.mart_county_heatmap
                where transaction_date >= current_date - interval '7 days'
                group by 1
                order by value_kes desc
                limit 15
                """,
                unit="short",
            ),
            bar_panel(
                8,
                "Daily Value Trend",
                grid(12, 12, 12, 8),
                f"""
                select
                  transaction_date::text as day,
                  sum(total_transaction_value) as value_kes
                from public_marts.mart_daily_transactions
                where transaction_date >= current_date - interval '14 days'
                {ACCOUNT_FILTER}
                group by 1
                order by 1
                """,
                unit="currency:KES",
            ),
        ]
        return dashboard(
            "mpesa-executive-command",
            "M-Pesa Executive Command Center",
            "Board-level value, adoption, and growth indicators for the M-Pesa streaming pipeline.",
            ["mpesa", "executive", "revenue"],
            panels,
            refresh="1m",
            time_from="now-7d",
        )

    @staticmethod
    def live_operations_dashboard() -> Dict[str, Any]:
        panels = [
            stat_panel(
                1,
                "Last 5m Throughput",
                grid(0, 0, 6, 4),
                f"""
                select count(*) as value
                from public_staging.stg_c2b_transactions
                where transaction_timestamp >= now() - interval '5 minutes'
                {ACCOUNT_FILTER}
                """,
                decimals=0,
            ),
            stat_panel(
                2,
                "Pipeline Freshness",
                grid(6, 0, 6, 4),
                """
                select coalesce(extract(epoch from (now() - max(received_at))) / 60, 0) as value
                from public_staging.stg_mpesa_raw
                """,
                unit="m",
                decimals=1,
            ),
            stat_panel(
                3,
                "Duplicate Transaction IDs",
                grid(12, 0, 6, 4),
                """
                select count(*) as value
                from (
                  select transaction_id
                  from public_staging.stg_mpesa_raw
                  where transaction_id is not null
                  group by transaction_id
                  having count(*) > 1
                ) d
                """,
                decimals=0,
            ),
            stat_panel(
                4,
                "Raw Events Loaded",
                grid(18, 0, 6, 4),
                """
                select count(*) as value
                from public_staging.stg_mpesa_raw
                where received_at >= now() - interval '24 hours'
                """,
                decimals=0,
            ),
            timeseries_panel(
                5,
                "Minute-Level Ingestion Rate",
                grid(0, 4, 16, 8),
                """
                select
                  date_trunc('minute', received_at) as time,
                  count(*) as raw_events
                from public_staging.stg_mpesa_raw
                where $__timeFilter(received_at)
                group by 1
                order by 1
                """,
                decimals=0,
            ),
            timeseries_panel(
                6,
                "Confirmed Transaction Value",
                grid(16, 4, 8, 8),
                f"""
                select
                  date_trunc('minute', transaction_timestamp) as time,
                  sum(transaction_amount) as value_kes
                from public_staging.stg_c2b_transactions
                where $__timeFilter(transaction_timestamp)
                {ACCOUNT_FILTER}
                group by 1
                order by 1
                """,
                unit="currency:KES",
                decimals=0,
            ),
            table_panel(
                7,
                "Recent Confirmations",
                grid(0, 12, 24, 8),
                f"""
                select
                  transaction_timestamp,
                  transaction_id,
                  customer_phone_number,
                  account_reference,
                  transaction_amount,
                  amount_category,
                  loaded_at
                from public_staging.stg_c2b_transactions
                where $__timeFilter(transaction_timestamp)
                {ACCOUNT_FILTER}
                order by transaction_timestamp desc
                limit 50
                """,
                unit="short",
            ),
        ]
        return dashboard(
            "mpesa-live-ops",
            "M-Pesa Live Operations",
            "Real-time pipeline throughput, freshness, and latest transaction monitoring.",
            ["mpesa", "operations", "realtime"],
            panels,
            refresh="10s",
            time_from="now-6h",
        )

    @staticmethod
    def fraud_risk_dashboard() -> Dict[str, Any]:
        risk_case = """
        case
          when transaction_amount >= 100000 then 'critical'
          when transaction_hour < 6 or transaction_hour >= 22 then 'elevated'
          when transaction_sequence_per_customer >= 10 then 'velocity'
          else 'normal'
        end
        """
        panels = [
            stat_panel(
                1,
                "Critical Value Events",
                grid(0, 0, 6, 4),
                f"""
                select count(*) as value
                from public_staging.stg_c2b_transactions
                where transaction_timestamp >= now() - interval '24 hours'
                  and transaction_amount >= 100000
                {ACCOUNT_FILTER}
                """,
                decimals=0,
            ),
            stat_panel(
                2,
                "Night Transactions",
                grid(6, 0, 6, 4),
                f"""
                select count(*) as value
                from public_staging.stg_c2b_transactions
                where transaction_timestamp >= now() - interval '24 hours'
                  and (transaction_hour < 6 or transaction_hour >= 22)
                {ACCOUNT_FILTER}
                """,
                decimals=0,
            ),
            stat_panel(
                3,
                "High Velocity Customers",
                grid(12, 0, 6, 4),
                f"""
                select count(*) as value
                from (
                  select customer_phone_number
                  from public_staging.stg_c2b_transactions
                  where transaction_timestamp >= now() - interval '1 hour'
                  {ACCOUNT_FILTER}
                  group by customer_phone_number
                  having count(*) >= 5
                ) v
                """,
                decimals=0,
            ),
            stat_panel(
                4,
                "Risk Exposure",
                grid(18, 0, 6, 4),
                f"""
                select coalesce(sum(transaction_amount), 0) as value
                from public_staging.stg_c2b_transactions
                where transaction_timestamp >= now() - interval '24 hours'
                  and ({risk_case}) <> 'normal'
                {ACCOUNT_FILTER}
                """,
                unit="currency:KES",
                decimals=0,
            ),
            pie_panel(
                5,
                "Risk Event Mix",
                grid(0, 4, 8, 8),
                f"""
                select {risk_case} as risk_bucket, count(*) as events
                from public_staging.stg_c2b_transactions
                where $__timeFilter(transaction_timestamp)
                {ACCOUNT_FILTER}
                group by 1
                order by 2 desc
                """,
            ),
            timeseries_panel(
                6,
                "Risk Events Over Time",
                grid(8, 4, 16, 8),
                f"""
                select
                  date_trunc('hour', transaction_timestamp) as time,
                  count(*) filter (where ({risk_case}) = 'critical') as critical,
                  count(*) filter (where ({risk_case}) = 'elevated') as elevated,
                  count(*) filter (where ({risk_case}) = 'velocity') as velocity
                from public_staging.stg_c2b_transactions
                where $__timeFilter(transaction_timestamp)
                {ACCOUNT_FILTER}
                group by 1
                order by 1
                """,
                decimals=0,
            ),
            table_panel(
                7,
                "Customers Requiring Review",
                grid(0, 12, 24, 8),
                f"""
                select
                  customer_phone_number,
                  count(*) as events,
                  sum(transaction_amount) as value_kes,
                  max(transaction_amount) as largest_transaction,
                  max(transaction_timestamp) as latest_seen,
                  string_agg(distinct ({risk_case}), ', ' order by ({risk_case})) as risk_reasons
                from public_staging.stg_c2b_transactions
                where transaction_timestamp >= now() - interval '7 days'
                  and ({risk_case}) <> 'normal'
                {ACCOUNT_FILTER}
                group by 1
                order by value_kes desc
                limit 50
                """,
            ),
        ]
        return dashboard(
            "mpesa-fraud-risk",
            "M-Pesa Fraud and Risk Monitoring",
            "Fraud analyst view for high-value, unusual-hour, and velocity-based risk events.",
            ["mpesa", "fraud", "risk"],
            panels,
            refresh="30s",
            time_from="now-24h",
        )

    @staticmethod
    def customer_intelligence_dashboard() -> Dict[str, Any]:
        panels = [
            stat_panel(
                1,
                "Customers in Window",
                grid(0, 0, 6, 4),
                f"""
                select count(distinct customer_phone_number) as value
                from public_staging.stg_c2b_transactions
                where $__timeFilter(transaction_timestamp)
                {ACCOUNT_FILTER}
                """,
                decimals=0,
            ),
            stat_panel(
                2,
                "Repeat Customer Rate",
                grid(6, 0, 6, 4),
                f"""
                with customer_counts as (
                  select customer_phone_number, count(*) as txns
                  from public_staging.stg_c2b_transactions
                  where $__timeFilter(transaction_timestamp)
                  {ACCOUNT_FILTER}
                  group by 1
                )
                select coalesce(100.0 * count(*) filter (where txns > 1) / nullif(count(*), 0), 0) as value
                from customer_counts
                """,
                unit="percent",
                decimals=1,
            ),
            stat_panel(
                3,
                "Median Customer Value",
                grid(12, 0, 6, 4),
                f"""
                with customer_value as (
                  select customer_phone_number, sum(transaction_amount) as value_kes
                  from public_staging.stg_c2b_transactions
                  where $__timeFilter(transaction_timestamp)
                  {ACCOUNT_FILTER}
                  group by 1
                )
                select coalesce(percentile_cont(0.5) within group (order by value_kes), 0) as value
                from customer_value
                """,
                unit="currency:KES",
                decimals=0,
            ),
            stat_panel(
                4,
                "Top Customer Share",
                grid(18, 0, 6, 4),
                f"""
                with customer_value as (
                  select customer_phone_number, sum(transaction_amount) as value_kes
                  from public_staging.stg_c2b_transactions
                  where $__timeFilter(transaction_timestamp)
                  {ACCOUNT_FILTER}
                  group by 1
                )
                select coalesce(100.0 * max(value_kes) / nullif(sum(value_kes), 0), 0) as value
                from customer_value
                """,
                unit="percent",
                decimals=1,
            ),
            bar_panel(
                5,
                "Transaction Timing Pattern",
                grid(0, 4, 12, 8),
                f"""
                select
                  case
                    when transaction_hour >= 6 and transaction_hour < 12 then 'Morning'
                    when transaction_hour >= 12 and transaction_hour < 18 then 'Afternoon'
                    else 'Evening/Night'
                  end as period,
                  count(*) as transactions
                from public_staging.stg_c2b_transactions
                where $__timeFilter(transaction_timestamp)
                {ACCOUNT_FILTER}
                group by 1
                order by 2 desc
                """,
            ),
            pie_panel(
                6,
                "Customer Value Bands",
                grid(12, 4, 12, 8),
                f"""
                with customer_value as (
                  select customer_phone_number, sum(transaction_amount) as value_kes
                  from public_staging.stg_c2b_transactions
                  where $__timeFilter(transaction_timestamp)
                  {ACCOUNT_FILTER}
                  group by 1
                )
                select
                  case
                    when value_kes >= 100000 then 'Enterprise'
                    when value_kes >= 25000 then 'High Value'
                    when value_kes >= 5000 then 'Core'
                    else 'Long Tail'
                  end as value_band,
                  count(*) as customers
                from customer_value
                group by 1
                order by 2 desc
                """,
            ),
            table_panel(
                7,
                "Top Customers by Value",
                grid(0, 12, 24, 8),
                f"""
                select
                  customer_phone_number,
                  count(*) as transactions,
                  sum(transaction_amount) as value_kes,
                  round(avg(transaction_amount), 2) as avg_ticket,
                  max(transaction_timestamp) as latest_transaction
                from public_staging.stg_c2b_transactions
                where $__timeFilter(transaction_timestamp)
                {ACCOUNT_FILTER}
                group by 1
                order by value_kes desc
                limit 50
                """,
            ),
        ]
        return dashboard(
            "mpesa-customer-intelligence",
            "M-Pesa Customer and Merchant Intelligence",
            "Customer value, repeat usage, timing, and account-reference intelligence.",
            ["mpesa", "customers", "merchant-intelligence"],
            panels,
            refresh="1m",
            time_from="now-30d",
        )

    @staticmethod
    def data_quality_dashboard() -> Dict[str, Any]:
        panels = [
            stat_panel(
                1,
                "Rows Missing Transaction ID",
                grid(0, 0, 6, 4),
                """
                select count(*) as value
                from public_staging.stg_mpesa_raw
                where transaction_id is null or transaction_id = ''
                """,
                decimals=0,
            ),
            stat_panel(
                2,
                "Rows Missing Phone",
                grid(6, 0, 6, 4),
                """
                select count(*) as value
                from public_staging.stg_mpesa_raw
                where phone_number is null or phone_number = ''
                """,
                decimals=0,
            ),
            stat_panel(
                3,
                "Invalid Amount Rows",
                grid(12, 0, 6, 4),
                """
                select count(*) as value
                from public_staging.stg_mpesa_raw
                where amount is null or amount::numeric < 0
                """,
                decimals=0,
            ),
            stat_panel(
                4,
                "dbt Model Freshness",
                grid(18, 0, 6, 4),
                """
                select coalesce(extract(epoch from (now() - max(created_at))) / 60, 0) as value
                from public_marts.mart_hourly_volumes
                """,
                unit="m",
                decimals=1,
            ),
            timeseries_panel(
                5,
                "Raw vs Staged Event Counts",
                grid(0, 4, 16, 8),
                """
                with raw_counts as (
                  select date_trunc('hour', received_at) as time, count(*) as raw_events
                  from public_staging.stg_mpesa_raw
                  where $__timeFilter(received_at)
                  group by 1
                ),
                staged_counts as (
                  select date_trunc('hour', transaction_timestamp) as time, count(*) as staged_events
                  from public_staging.stg_c2b_transactions
                  where $__timeFilter(transaction_timestamp)
                  group by 1
                )
                select
                  coalesce(r.time, s.time) as time,
                  coalesce(raw_events, 0) as raw_events,
                  coalesce(staged_events, 0) as staged_events
                from raw_counts r
                full outer join staged_counts s using (time)
                order by 1
                """,
                decimals=0,
            ),
            table_panel(
                6,
                "Daily Completeness",
                grid(16, 4, 8, 8),
                """
                select
                  transaction_date,
                  count(*) as staged_transactions,
                  count(*) filter (where customer_phone_number is null) as missing_phone,
                  count(*) filter (where transaction_amount is null) as missing_amount,
                  count(*) filter (where account_reference is null) as missing_reference
                from public_staging.stg_c2b_transactions
                where transaction_date >= current_date - interval '14 days'
                group by 1
                order by 1 desc
                """,
            ),
            table_panel(
                7,
                "Potential Duplicate IDs",
                grid(0, 12, 24, 8),
                """
                select
                  transaction_id,
                  count(*) as duplicate_count,
                  min(received_at) as first_seen,
                  max(received_at) as last_seen
                from public_staging.stg_mpesa_raw
                where transaction_id is not null
                group by 1
                having count(*) > 1
                order by duplicate_count desc, last_seen desc
                limit 50
                """,
            ),
        ]
        return dashboard(
            "mpesa-data-quality",
            "M-Pesa Data Quality and Reliability",
            "Warehouse quality checks, model freshness, and ingestion completeness.",
            ["mpesa", "data-quality", "reliability"],
            panels,
            refresh="1m",
            time_from="now-7d",
        )

    @staticmethod
    def dashboards() -> Dict[str, Dict[str, Any]]:
        return {
            "executive_command_center": GrafanaDashboardBuilder.executive_dashboard(),
            "live_operations": GrafanaDashboardBuilder.live_operations_dashboard(),
            "fraud_risk": GrafanaDashboardBuilder.fraud_risk_dashboard(),
            "customer_intelligence": GrafanaDashboardBuilder.customer_intelligence_dashboard(),
            "data_quality": GrafanaDashboardBuilder.data_quality_dashboard(),
        }

    @staticmethod
    def save_dashboards(output_dir: Path = DEFAULT_OUTPUT_DIR) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        written: List[Path] = []
        for name, definition in GrafanaDashboardBuilder.dashboards().items():
            path = output_dir / f"{name}.json"
            path.write_text(json.dumps(definition, indent=2, sort_keys=True) + "\n")
            written.append(path)
        return written


def datasource_provisioning() -> str:
    return """apiVersion: 1

datasources:
  - name: M-Pesa Postgres
    uid: mpesa-postgres
    type: postgres
    access: proxy
    url: postgres:5432
    database: ${POSTGRES_DB}
    user: ${POSTGRES_USER}
    secureJsonData:
      password: ${POSTGRES_PASSWORD}
    jsonData:
      sslmode: disable
      postgresVersion: 1500
      timescaledb: false
    isDefault: true
    editable: true
"""


def dashboard_provisioning() -> str:
    return """apiVersion: 1

providers:
  - name: M-Pesa Pipeline
    orgId: 1
    folder: M-Pesa Real-Time Streaming
    folderUid: mpesa-streaming
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
"""


def save_provisioning(provisioning_dir: Path = DEFAULT_PROVISIONING_DIR) -> List[Path]:
    datasource_dir = provisioning_dir / "datasources"
    dashboards_dir = provisioning_dir / "dashboards"
    datasource_dir.mkdir(parents=True, exist_ok=True)
    dashboards_dir.mkdir(parents=True, exist_ok=True)

    datasource_path = datasource_dir / "postgres.yml"
    dashboards_path = dashboards_dir / "dashboards.yml"
    datasource_path.write_text(datasource_provisioning())
    dashboards_path.write_text(dashboard_provisioning())
    return [datasource_path, dashboards_path]


def validate_dashboard(definition: Dict[str, Any]) -> None:
    required = {"uid", "title", "panels", "schemaVersion", "templating"}
    missing = required - set(definition)
    if missing:
        raise ValueError(f"Dashboard {definition.get('title', '<unknown>')} missing: {missing}")
    if not definition["panels"]:
        raise ValueError(f"Dashboard {definition['title']} has no panels")
    for item in definition["panels"]:
        if "gridPos" not in item or "targets" not in item:
            raise ValueError(f"Panel {item.get('title', '<unknown>')} is missing grid/targets")
        for target in item["targets"]:
            if target.get("datasource", {}).get("uid") != DATASOURCE_UID:
                raise ValueError(f"Panel {item['title']} is not wired to {DATASOURCE_UID}")
            if not target.get("rawSql"):
                raise ValueError(f"Panel {item['title']} is missing SQL")


def validate_files(paths: Iterable[Path]) -> None:
    for path in paths:
        data = json.loads(path.read_text())
        validate_dashboard(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Grafana dashboards for M-Pesa pipeline")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--provisioning-dir", type=Path, default=DEFAULT_PROVISIONING_DIR)
    parser.add_argument("--check", action="store_true", help="Validate generated dashboard JSON")
    args = parser.parse_args()

    dashboard_paths = GrafanaDashboardBuilder.save_dashboards(args.output_dir)
    provisioning_paths = save_provisioning(args.provisioning_dir)
    validate_files(dashboard_paths)

    if args.check:
        print(f"Validated {len(dashboard_paths)} dashboards")
        return

    for path in dashboard_paths + provisioning_paths:
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
