"""FastAPI application providing a clean REST API for the Brand AI-Readiness Engine."""

from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.audit_service import audit_service, check_engine_ready
from api.job_store import JobStatus
from api.schemas import (
    AuditAcceptedResponse,
    AuditRequest,
    AuditStatusResponse,
    ErrorResponse,
    HealthResponse,
)

# Parse configurable CORS origins (comma-separated or wildcard)
cors_env = os.environ.get("CORS_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]

app = FastAPI(
    title="Brand AI-Readiness Audit Engine API",
    version="1.0.0",
    description=(
        "REST API exposing the autonomous Brand AI-Readiness Audit Engine. "
        "Allows clients to asynchronously submit public website URLs, track crawl & "
        "analysis status, and retrieve evidence-backed AI citability reports."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Check API health and audit engine readiness",
    tags=["System"],
)
def get_health() -> HealthResponse:
    """Return the operational health of the REST API and verify that engine components are ready."""
    is_ready, details = check_engine_ready()
    return HealthResponse(
        status="ok" if is_ready else "degraded",
        engine_ready=is_ready,
        version="1.0.0",
        details=details,
    )


@app.post(
    "/api/audits",
    response_model=AuditAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a website URL for an asynchronous audit",
    tags=["Audits"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL or disallowed destination"},
    },
)
def create_audit(payload: AuditRequest) -> AuditAcceptedResponse:
    """Submit a target website URL for audit.

    The URL is validated against SSRF boundaries (private IPs, loopback, cloud metadata)
    and an asynchronous audit job is enqueued. Returns an audit ID and HTTP 202 Accepted.
    """
    try:
        job = audit_service.submit_audit(payload.url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit audit job: {str(e)}",
        )

    return AuditAcceptedResponse(
        audit_id=job.audit_id,
        status=JobStatus.QUEUED.value,
        url=job.url,
        created_at=job.created_at,
        message="Audit job accepted and queued for execution.",
    )


@app.get(
    "/api/audits/{audit_id}",
    response_model=AuditStatusResponse,
    summary="Get status of an audit job",
    tags=["Audits"],
    responses={
        404: {"model": ErrorResponse, "description": "Audit ID not found"},
    },
)
def get_audit_status(audit_id: str) -> AuditStatusResponse:
    """Check the real-time status (queued, running, completed, failed) of an audit job."""
    job = audit_service.job_store.get_job(audit_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit job '{audit_id}' was not found.",
        )

    return AuditStatusResponse(
        audit_id=job.audit_id,
        status=job.status.value,
        url=job.url,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@app.get(
    "/api/audits/{audit_id}/report",
    summary="Retrieve completed audit JSON report",
    tags=["Audits"],
    responses={
        200: {"description": "Genuine JSON report matching assets/report.schema.json"},
        404: {"model": ErrorResponse, "description": "Audit ID not found"},
        409: {"model": ErrorResponse, "description": "Audit still in progress"},
        422: {"model": ErrorResponse, "description": "Audit execution failed"},
    },
)
def get_audit_report(audit_id: str) -> JSONResponse:
    """Retrieve the generated Brand AI-Readiness JSON report once the audit has completed."""
    job = audit_service.job_store.get_job(audit_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit job '{audit_id}' was not found.",
        )

    if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Audit '{audit_id}' is currently {job.status.value}. "
                "Please query /api/audits/{audit_id} until completed."
            ),
        )

    if job.status == JobStatus.FAILED:
        raise HTTPException(
            status_code=422,
            detail=f"Audit '{audit_id}' failed: {job.error}",
        )

    if not job.report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report data for audit '{audit_id}' is missing.",
        )

    return JSONResponse(content=job.report)
