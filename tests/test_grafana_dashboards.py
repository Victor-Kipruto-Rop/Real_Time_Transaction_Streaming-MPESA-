import json
from pathlib import Path

from dashboards.grafana_dashboards import (
    DATASOURCE_UID,
    GrafanaDashboardBuilder,
    save_provisioning,
    validate_dashboard,
)


def test_dashboard_generator_creates_use_case_dashboards(tmp_path: Path):
    output_dir = tmp_path / "dashboards"
    paths = GrafanaDashboardBuilder.save_dashboards(output_dir)

    assert len(paths) == 5
    assert {path.name for path in paths} == {
        "customer_intelligence.json",
        "data_quality.json",
        "executive_command_center.json",
        "fraud_risk.json",
        "live_operations.json",
    }


def test_dashboards_are_provisioning_ready(tmp_path: Path):
    paths = GrafanaDashboardBuilder.save_dashboards(tmp_path)

    for path in paths:
        definition = json.loads(path.read_text())
        validate_dashboard(definition)

        assert "dashboard" not in definition
        assert definition["schemaVersion"] >= 39
        assert definition["style"] == "dark"
        assert definition["panels"]

        for panel in definition["panels"]:
            assert panel["datasource"]["uid"] == DATASOURCE_UID
            assert panel["targets"]
            assert panel["targets"][0]["rawSql"]
            assert panel["targets"][0]["datasource"]["uid"] == DATASOURCE_UID


def test_provisioning_files_include_postgres_datasource(tmp_path: Path):
    paths = save_provisioning(tmp_path / "provisioning")
    rendered = "\n".join(path.read_text() for path in paths)

    assert "uid: mpesa-postgres" in rendered
    assert "type: postgres" in rendered
    assert "path: /var/lib/grafana/dashboards" in rendered
    assert "folder: M-Pesa Real-Time Streaming" in rendered
