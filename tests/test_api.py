import json


def test_health_reports_model_and_database(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ONLINE"
    assert res.json()["model_loaded"] is True


def test_ingest_classifies_healthy_reading(client, healthy_payload):
    res = client.post("/api/v1/telemetry/ingest", json=healthy_payload)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "NORMAL" and body["is_healthy"] is True
    assert body["anomaly_score"] > 0
    assert "X-Process-Time-Ms" in res.headers


def test_ingest_flags_critical_reading(client, critical_payload):
    body = client.post("/api/v1/telemetry/ingest", json=critical_payload).json()
    assert body["status"] == "ANOMALY_DETECTED" and body["is_healthy"] is False
    assert body["anomaly_score"] < 0


def test_ingest_flags_subtle_multivariate_degradation(client):
    """Ninguna métrica supera un umbral fijo, pero la combinación es anómala."""
    payload = {"server_id": "SRV-TEST-02", "cpu_utilization_pct": 15.0, "package_temp_c": 70.0,
               "dram_usage_gb": 32.0, "pcie_error_count": 2}
    assert client.post("/api/v1/telemetry/ingest", json=payload).json()["status"] == "ANOMALY_DETECTED"


def test_ingest_rejects_out_of_range_values(client, healthy_payload):
    for field, value in [("cpu_utilization_pct", 150), ("package_temp_c", -5), ("pcie_error_count", -1)]:
        res = client.post("/api/v1/telemetry/ingest", json={**healthy_payload, field: value})
        assert res.status_code == 422, field


def test_ingest_keeps_agent_timestamp_and_rack(client, healthy_payload):
    payload = {**healthy_payload, "rack_id": "RACK-ZAP-02", "recorded_at": "2026-10-01T12:00:00+00:00"}
    body = client.post("/api/v1/telemetry/ingest", json=payload).json()
    assert body["evaluated_at"].startswith("2026-10-01T12:00:00")
    summary = client.get("/api/v1/fleet/summary").json()
    assert summary[0]["rack_id"] == "RACK-ZAP-02"


def test_history_returns_latest_records(client, healthy_payload, critical_payload):
    client.post("/api/v1/telemetry/ingest", json=healthy_payload)
    client.post("/api/v1/telemetry/ingest", json=critical_payload)
    res = client.get("/api/v1/servers/SRV-TEST-01/history", params={"limit": 1})
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_history_unknown_server_and_limit_bounds(client):
    assert client.get("/api/v1/servers/NOPE/history").status_code == 404
    assert client.get("/api/v1/servers/NOPE/history", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/servers/NOPE/history", params={"limit": 100000}).status_code == 422


def test_fleet_summary_aggregates_per_server(client, healthy_payload, critical_payload):
    client.post("/api/v1/telemetry/ingest", json=healthy_payload)
    client.post("/api/v1/telemetry/ingest", json=critical_payload)
    row = client.get("/api/v1/fleet/summary").json()[0]
    assert row["total_readings"] == 2
    assert row["anomaly_incidents"] == 1
    assert row["uptime_pct"] == 50.0


def test_datalake_export_does_not_duplicate_records(client, healthy_payload):
    for _ in range(3):
        client.post("/api/v1/telemetry/ingest", json=healthy_payload)

    first = client.post("/api/v1/cloud/export-datalake", params={"limit": 2}).json()
    second = client.post("/api/v1/cloud/export-datalake").json()
    third = client.post("/api/v1/cloud/export-datalake").json()

    assert first["exported_records"] == 2 and second["exported_records"] == 1
    assert third["status"] == "SKIPPED"
    ids = []
    for result in (first, second):
        assert "year=" in result["lake_partition"]
        with open(result["file_path"], encoding="utf-8") as f:
            ids += [r["id"] for r in json.load(f)]
    assert sorted(ids) == [1, 2, 3]
