from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_monitoring_config_uses_real_alert_targets_not_placeholder_values():
    alertmanager = (ROOT / "monitoring" / "alertmanager.yml").read_text(encoding="utf-8")
    docker_compose = (ROOT / "monitoring" / "docker-compose.monitoring.yml").read_text(encoding="utf-8")

    assert "YOUR/SLACK/WEBHOOK" not in alertmanager
    assert "your-email-password" not in alertmanager
    assert "set_me_via_env" not in docker_compose
    assert "SLACK_WEBHOOK_URL" in docker_compose
    assert "ALERT_EMAIL_RECIPIENTS" in docker_compose
