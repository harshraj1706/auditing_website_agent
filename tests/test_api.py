"""Comprehensive automated tests for Brand AI-Readiness REST API."""

import concurrent.futures
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.audit_service import audit_service, validate_target_url
from api.job_store import JobStatus, JobStore
from api.main import app

client = TestClient(app)

SAMPLE_VALID_REPORT = {
    "site": "example.com",
    "audited_at": "2026-10-28T12:00:00Z",
    "site_type": "saas",
    "summary": {
        "total_findings": 2,
        "critical": 1,
        "high": 1,
        "medium": 0,
        "low": 0,
    },
    "findings": [
        {
            "id": "CRA-01",
            "title": "AI crawler user-agents disallowed in robots.txt",
            "severity": "critical",
            "evidence": "Disallow rules present for AI user-agents",
            "suggested_action": {
                "summary": "Allow AI search and citation crawlers",
                "priority": "P0",
                "how": "Update robots.txt",
            },
        },
        {
            "id": "FC-ENT-01",
            "title": "Organization schema missing from homepage",
            "severity": "high",
            "evidence": "0 JSON-LD entity nodes discovered",
            "suggested_action": {
                "summary": "Add Schema.org Organization markup",
                "priority": "P1",
                "how": "Embed JSON-LD with official brand name and sameAs links",
            },
        },
    ],
}


@pytest.fixture(autouse=True)
def reset_store():
    """Reset in-memory job store between tests."""
    audit_service.job_store.clear()
    yield
    audit_service.job_store.clear()


# ==============================================================================
# Health Check Tests
# ==============================================================================

def test_health_endpoint():
    """GET /api/health returns 200 and confirms engine readiness."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["engine_ready"] is True
    assert "details" in data
    assert data["details"]["marketplace_json"] is True
    assert data["details"]["run_audit_script"] is True
    assert data["details"]["modules_importable"] is True


# ==============================================================================
# Security & URL Validation Tests (SSRF, Malformed URLs, Credentials)
# ==============================================================================

@pytest.mark.parametrize(
    "invalid_url,expected_error",
    [
        ("", "URL cannot be empty"),
        ("ftp://example.com", "Unsupported URL scheme"),
        ("file:///etc/passwd", "Unsupported URL scheme"),
        ("javascript:alert(1)", "Unsupported URL scheme"),
        ("http://user:pass@example.com", "embedded user credentials are not permitted"),
        ("http://localhost:8080", "Auditing destination 'localhost' is not permitted"),
        ("http://127.0.0.1:8000", "private, loopback, or restricted network space"),
        ("http://0.0.0.0", "private, loopback, or restricted network space"),
        ("http://[::1]", "private, loopback, or restricted network space"),
        ("http://192.168.1.100", "private, loopback, or restricted network space"),
        ("http://10.0.0.1", "private, loopback, or restricted network space"),
        ("http://172.16.0.1", "private, loopback, or restricted network space"),
        ("http://169.254.169.254/latest/meta-data", "Auditing destination '169.254.169.254' is not permitted"),
        ("http://metadata.google.internal", "Auditing destination 'metadata.google.internal' is not permitted"),
    ],
)
def test_url_validation_rejections(invalid_url, expected_error):
    """Direct URL validation rejects unsafe schemes, local networks, and SSRF destinations."""
    with pytest.raises(ValueError) as excinfo:
        validate_target_url(invalid_url)
    assert expected_error in str(excinfo.value)


def test_post_audit_rejects_unsafe_url():
    """POST /api/audits returns HTTP 400 when an SSRF or invalid destination is passed."""
    response = client.post("/api/audits", json={"url": "http://127.0.0.1:8000"})
    assert response.status_code == 400
    assert "private, loopback, or restricted" in response.json()["detail"]

    response = client.post("/api/audits", json={"url": "ftp://files.example.com"})
    assert response.status_code == 400
    assert "Unsupported URL scheme" in response.json()["detail"]


# ==============================================================================
# Audit Lifecycle & Endpoints Tests (Queued -> Running -> Completed / Failed)
# ==============================================================================

def test_successful_audit_flow_mocked():
    """Submit audit, poll status through completion, and retrieve full report."""
    with patch.object(audit_service, "_run_engine_with_timeout", return_value=SAMPLE_VALID_REPORT):
        post_resp = client.post("/api/audits", json={"url": "https://example.com"})
        assert post_resp.status_code == 202
        body = post_resp.json()
        audit_id = body["audit_id"]
        assert body["status"] == "queued"
        assert body["url"] == "https://example.com/"

        # Allow worker thread to pick up and complete
        for _ in range(50):
            status_resp = client.get(f"/api/audits/{audit_id}")
            assert status_resp.status_code == 200
            current_status = status_resp.json()["status"]
            if current_status == "completed":
                break
            time.sleep(0.05)

        assert current_status == "completed"
        status_data = status_resp.json()
        assert status_data["completed_at"] is not None
        assert status_data["error"] is None

        # Retrieve report
        report_resp = client.get(f"/api/audits/{audit_id}/report")
        assert report_resp.status_code == 200
        report = report_resp.json()
        assert report["site"] == "example.com"
        assert report["summary"]["total_findings"] == 2
        assert len(report["findings"]) == 2
        assert report["findings"][0]["id"] == "CRA-01"


def test_get_report_while_running_returns_409():
    """GET /api/audits/{id}/report returns HTTP 409 Conflict if audit is still running."""
    job = audit_service.job_store.create_job("test-running-id", "https://example.com")
    audit_service.job_store.mark_running("test-running-id")

    resp = client.get("/api/audits/test-running-id/report")
    assert resp.status_code == 409
    assert "currently running" in resp.json()["detail"]


def test_unknown_audit_id_returns_404():
    """Non-existent audit IDs return HTTP 404 for both status and report endpoints."""
    resp = client.get("/api/audits/nonexistent-12345")
    assert resp.status_code == 404
    assert "was not found" in resp.json()["detail"]

    report_resp = client.get("/api/audits/nonexistent-12345/report")
    assert report_resp.status_code == 404
    assert "was not found" in report_resp.json()["detail"]


def test_audit_failure_handling():
    """Engine errors transition job to failed and report returns HTTP 422."""
    with patch.object(audit_service, "_run_engine_with_timeout", side_effect=RuntimeError("DNS failure on origin")):
        post_resp = client.post("/api/audits", json={"url": "https://example.com"})
        assert post_resp.status_code == 202
        audit_id = post_resp.json()["audit_id"]

        # Wait for worker thread to process error
        for _ in range(50):
            status_resp = client.get(f"/api/audits/{audit_id}")
            if status_resp.json()["status"] == "failed":
                break
            time.sleep(0.05)

        status_data = status_resp.json()
        assert status_data["status"] == "failed"
        assert "DNS failure on origin" in status_data["error"]

        # Report retrieval on failed audit
        report_resp = client.get(f"/api/audits/{audit_id}/report")
        assert report_resp.status_code == 422
        assert "failed" in report_resp.json()["detail"]


def test_audit_timeout_handling():
    """Long-running crawls that exceed timeout trigger a clean failure."""
    with patch.object(audit_service, "_run_engine_with_timeout", side_effect=concurrent.futures.TimeoutError):
        post_resp = client.post("/api/audits", json={"url": "https://example.com"})
        audit_id = post_resp.json()["audit_id"]

        for _ in range(50):
            status_resp = client.get(f"/api/audits/{audit_id}")
            if status_resp.json()["status"] == "failed":
                break
            time.sleep(0.05)

        assert status_resp.json()["status"] == "failed"
        assert "timed out" in status_resp.json()["error"]


def test_malformed_report_rejection():
    """Engine returning an invalid report structure is marked failed."""
    with patch.object(
        audit_service,
        "_run_engine_with_timeout",
        side_effect=ValueError("Engine returned malformed report structure."),
    ):
        post_resp = client.post("/api/audits", json={"url": "https://example.com"})
        assert post_resp.status_code == 202
        audit_id = post_resp.json()["audit_id"]

        for _ in range(50):
            status_resp = client.get(f"/api/audits/{audit_id}")
            if status_resp.json()["status"] == "failed":
                break
            time.sleep(0.05)

        status_data = status_resp.json()
        assert status_data["status"] == "failed"
        assert "malformed report" in status_data["error"]


def test_job_store_concurrency_and_lifecycle():
    """JobStore state transitions and semaphore boundaries function correctly."""
    store = JobStore(max_concurrent=1)
    job = store.create_job("job-1", "https://example.com")
    assert job.status == JobStatus.QUEUED

    # Mark running
    assert store.mark_running("job-1") is True
    assert job.status == JobStatus.RUNNING
    assert job.started_at is not None

    # Mark completed
    store.mark_completed("job-1", {"site": "example.com"})
    assert job.status == JobStatus.COMPLETED
    assert job.completed_at is not None
    assert job.report == {"site": "example.com"}

    # Second job failed
    job2 = store.create_job("job-2", "https://example.com")
    store.mark_failed("job-2", "Connection refused")
    assert job2.status == JobStatus.FAILED
    assert job2.error == "Connection refused"
