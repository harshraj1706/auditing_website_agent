"""In-process, thread-safe asynchronous job store for development and local audits.

Note:
Jobs are kept in memory and are discarded when the API server restarts. This is
intended for local development and single-instance API serving. Persistent storage
(e.g., PostgreSQL/Supabase) can be integrated in later phases if required.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditJob:
    """Represents the lifecycle and state of a single website audit execution."""

    def __init__(self, audit_id: str, url: str):
        self.audit_id = audit_id
        self.url = url
        self.status = JobStatus.QUEUED
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.report: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "status": self.status.value,
            "url": self.url,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


class JobStore:
    """Thread-safe in-memory store for audit jobs with concurrency throttling."""

    def __init__(self, max_concurrent: int | None = None):
        if max_concurrent is None:
            max_concurrent = int(os.environ.get("MAX_CONCURRENT_AUDITS", "2"))
        self._max_concurrent = max(1, max_concurrent)
        self._jobs: Dict[str, AuditJob] = {}
        self._lock = threading.Lock()
        self.concurrency_semaphore = threading.Semaphore(self._max_concurrent)

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    def create_job(self, audit_id: str, url: str) -> AuditJob:
        """Create and register a new audit job in queued state."""
        with self._lock:
            job = AuditJob(audit_id, url)
            self._jobs[audit_id] = job
            return job

    def get_job(self, audit_id: str) -> Optional[AuditJob]:
        """Retrieve a job by audit_id."""
        with self._lock:
            return self._jobs.get(audit_id)

    def mark_running(self, audit_id: str) -> bool:
        """Transition job from QUEUED to RUNNING. Returns True if transitioned."""
        with self._lock:
            job = self._jobs.get(audit_id)
            if job and job.status == JobStatus.QUEUED:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                return True
            return False

    def mark_completed(self, audit_id: str, report: Dict[str, Any]) -> None:
        """Record successful audit report and transition to COMPLETED."""
        with self._lock:
            job = self._jobs.get(audit_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.report = report

    def mark_failed(self, audit_id: str, error_message: str) -> None:
        """Record error details and transition to FAILED."""
        with self._lock:
            job = self._jobs.get(audit_id)
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                job.error = error_message

    def clear(self) -> None:
        """Utility for test resets."""
        with self._lock:
            self._jobs.clear()
