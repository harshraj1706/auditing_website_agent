"""Pydantic schemas for the Brand AI-Readiness Audit Engine REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditRequest(BaseModel):
    """Payload for submitting a new website audit."""

    url: str = Field(
        ...,
        description="Public website URL to audit (HTTP or HTTPS)",
        examples=["https://stripe.com"],
    )


class AuditAcceptedResponse(BaseModel):
    """Response returned when an audit job is accepted for asynchronous processing."""

    audit_id: str = Field(..., description="Unique identifier for the audit job")
    status: str = Field("queued", description="Initial job status (queued)")
    url: str = Field(..., description="Target URL being audited")
    created_at: datetime = Field(..., description="UTC timestamp when the job was accepted")
    message: str = Field(
        "Audit job accepted and queued for execution.",
        description="Human-readable status confirmation",
    )


class AuditStatusResponse(BaseModel):
    """Status details for an existing audit job."""

    audit_id: str = Field(..., description="Unique identifier for the audit job")
    status: str = Field(
        ...,
        description="Current state of the audit job: queued, running, completed, or failed",
    )
    url: str = Field(..., description="Target URL being audited")
    created_at: datetime = Field(..., description="Timestamp when the audit was submitted")
    started_at: Optional[datetime] = Field(
        None, description="Timestamp when crawling and analysis began"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Timestamp when the audit completed or failed"
    )
    error: Optional[str] = Field(
        None, description="Safe error explanation if the audit failed"
    )


class HealthResponse(BaseModel):
    """System health and engine readiness response."""

    status: str = Field("ok", description="Overall API service health")
    engine_ready: bool = Field(
        ..., description="True if orchestrator files, schema, and Python modules are accessible"
    )
    version: str = Field("1.0.0", description="API version")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Diagnostic details on orchestrator and workspace integrity"
    )


class ErrorResponse(BaseModel):
    """Structured API error response."""

    detail: str = Field(..., description="Description of the error condition")
    code: Optional[str] = Field(None, description="Specific error category or machine-readable code")
