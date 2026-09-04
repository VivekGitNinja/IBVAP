"""
IBVAP — Observability & Telemetry Verification Suite
Tests distributed tracing (X-Trace-ID), Prometheus metrics exposition (/metrics),
and structured JSON logging contracts.
"""

import json
import logging
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.core.logging import (
    StructuredJSONFormatter,
    get_trace_id,
    set_trace_id,
)
from backend.app.core.metrics import (
    generate_metrics_text,
    record_detection,
    record_http_request,
    set_active_ws_count,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_distributed_trace_id_generation(client):
    """Test that incoming requests without X-Trace-ID get a generated trace ID."""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Trace-ID" in response.headers
    trace_id = response.headers["X-Trace-ID"]
    assert trace_id.startswith("ibvap-")
    assert len(trace_id) >= 10
    assert "X-Process-Time-Ms" in response.headers
    assert float(response.headers["X-Process-Time-Ms"]) >= 0.0


def test_distributed_trace_id_propagation(client):
    """Test that incoming client trace IDs are respected and propagated."""
    custom_trace = "trace-recon-alpha-998877"
    response = client.get("/", headers={"X-Trace-ID": custom_trace})
    assert response.status_code == 200
    assert response.headers["X-Trace-ID"] == custom_trace


def test_prometheus_metrics_endpoint(client):
    """Verify /metrics returns 200 with standard Prometheus exposition format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain; version=0.0.4" in response.headers["content-type"]
    
    body = response.text
    assert "# HELP ibvap_system_info" in body
    assert "# TYPE ibvap_system_info gauge" in body
    assert "ibvap_system_info{" in body
    assert "version=\"2.0.0\"" in body
    assert "ibvap_uptime_seconds" in body
    assert "ibvap_http_requests_total" in body


def test_prometheus_metrics_recording():
    """Verify metrics counters, gauges, and histograms record values correctly."""
    record_http_request("POST", "/api/v1/cameras/42", 201, 0.045)
    record_detection("BREACH", "BOP-01")
    set_active_ws_count(5)

    metrics_text = generate_metrics_text()
    assert 'ibvap_http_requests_total{method="POST",path="/api/v1/cameras/:id",status="201"}' in metrics_text
    assert 'ibvap_detections_total{camera_id="BOP-01",type="BREACH"}' in metrics_text
    assert "ibvap_active_websocket_connections 5.0" in metrics_text
    assert 'ibvap_http_request_duration_seconds_bucket{le="0.05",method="POST",path="/api/v1/cameras/:id"} 1' in metrics_text
    assert 'ibvap_http_request_duration_seconds_count{method="POST",path="/api/v1/cameras/:id"} 1' in metrics_text


def test_structured_json_formatter():
    """Verify structured logger formats records into RFC-compliant JSON with trace ID."""
    formatter = StructuredJSONFormatter()
    set_trace_id("trace-test-unit-42")

    record = logging.LogRecord(
        name="ibvap.audit",
        level=logging.INFO,
        pathname="audit.py",
        lineno=101,
        msg="Tactical perimeter check initiated",
        args=(),
        exc_info=None,
    )
    record.bop = "BOP-NORTH"
    record.threat_level = "ELEVATED"

    output = formatter.format(record)
    data = json.loads(output)

    assert data["level"] == "INFO"
    assert data["logger"] == "ibvap.audit"
    assert data["message"] == "Tactical perimeter check initiated"
    assert data["trace_id"] == "trace-test-unit-42"
    assert data["bop"] == "BOP-NORTH"
    assert data["threat_level"] == "ELEVATED"
    assert "timestamp" in data
