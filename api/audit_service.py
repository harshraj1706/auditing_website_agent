"""Adapter service connecting FastAPI routes to the existing Brand AI-Readiness Audit Engine."""

from __future__ import annotations

import concurrent.futures
import ipaddress
import json
import logging
import os
import socket
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

# Ensure engine orchestrator scripts can be imported cleanly without modifying engine files
REPO_ROOT = Path(__file__).resolve().parent.parent
ORCHESTRATOR_SCRIPTS = REPO_ROOT / "skills" / "audit-orchestrator" / "scripts"
if str(ORCHESTRATOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_SCRIPTS))

from api.job_store import AuditJob, JobStatus, JobStore

logger = logging.getLogger("audit_api")

# Configuration defaults
DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("AUDIT_TIMEOUT_SECONDS", "240"))
MAX_CONCURRENT_AUDITS = int(os.environ.get("MAX_CONCURRENT_AUDITS", "2"))

# Blocked hostnames / cloud metadata names
DISALLOWED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254",
}


def validate_target_url(url_string: str) -> str:
    """Validate user-provided URL against formatting errors, unsafe schemes, and SSRF destinations.

    Returns the normalized URL string if valid, or raises ValueError.
    """
    if not url_string or not isinstance(url_string, str):
        raise ValueError("URL cannot be empty.")

    clean_url = url_string.strip()

    # Detect scheme if present
    initial_parse = urlparse(clean_url)
    if initial_parse.scheme and initial_parse.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"Unsupported URL scheme '{initial_parse.scheme}'. Only http and https are allowed."
        )

    if not initial_parse.scheme:
        clean_url = "https://" + clean_url

    parsed = urlparse(clean_url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed."
        )

    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded user credentials are not permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must include a valid hostname.")

    hostname_lower = hostname.lower().strip("[]")

    if hostname_lower in DISALLOWED_HOSTNAMES or hostname_lower.endswith(".localhost"):
        raise ValueError(f"Auditing destination '{hostname}' is not permitted.")

    # Direct IP literal check
    try:
        ip_obj = ipaddress.ip_address(hostname_lower)
        _verify_ip_safety(ip_obj)
    except ValueError as e:
        # Not an IP literal; perform DNS resolution check
        if "does not appear to be an IPv4 or IPv6 address" in str(e):
            _resolve_and_verify_hostname(hostname_lower)
        else:
            raise

    # Return normalized URL with intact path / query
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme}://{parsed.netloc}{path}{query}"


def _verify_ip_safety(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    """Enforce SSRF boundaries against loopback, private, link-local, and reserved IP spaces."""
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise ValueError(
            f"Destination IP '{ip}' is in a private, loopback, or restricted network space and cannot be audited."
        )


def _resolve_and_verify_hostname(hostname: str) -> None:
    """Resolve DNS for hostname and confirm all target IPs are safe public addresses."""
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve hostname '{hostname}': {e.strerror}")

    resolved_any = False
    for family, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            _verify_ip_safety(ip_obj)
            resolved_any = True
        except ValueError as err:
            raise ValueError(f"Resolved destination address for '{hostname}' is restricted: {err}")

    if not resolved_any:
        raise ValueError(f"Could not determine public IP address for hostname '{hostname}'.")


def check_engine_ready() -> Tuple[bool, Dict[str, Any]]:
    """Verify that all core engine files, scripts, and report schemas are in place."""
    details: Dict[str, Any] = {}

    marketplace_path = REPO_ROOT / "marketplace.json"
    schema_path = REPO_ROOT / "assets" / "report.schema.json"
    run_audit_path = ORCHESTRATOR_SCRIPTS / "run_audit.py"
    crawl_path = ORCHESTRATOR_SCRIPTS / "crawl_site.py"
    compose_path = ORCHESTRATOR_SCRIPTS / "compose_report.py"

    details["marketplace_json"] = marketplace_path.is_file()
    details["report_schema_json"] = schema_path.is_file()
    details["run_audit_script"] = run_audit_path.is_file()
    details["crawl_script"] = crawl_path.is_file()
    details["compose_script"] = compose_path.is_file()

    # Try importing engine modules
    try:
        import compose_report
        import crawl_site
        details["modules_importable"] = True
    except Exception as exc:
        details["modules_importable"] = False
        details["import_error"] = str(exc)

    is_ready = all(
        [
            details["marketplace_json"],
            details["report_schema_json"],
            details["run_audit_script"],
            details["crawl_script"],
            details["compose_script"],
            details.get("modules_importable", False),
        ]
    )
    return is_ready, details


class AuditService:
    """Coordinates audit requests, worker thread execution, timeouts, and job state."""

    def __init__(self, job_store: Optional[JobStore] = None):
        self.job_store = job_store or JobStore(max_concurrent=MAX_CONCURRENT_AUDITS)
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.job_store.max_concurrent * 2,
            thread_name_prefix="audit_worker",
        )

    def submit_audit(self, raw_url: str) -> AuditJob:
        """Validate destination, register job, and enqueue execution asynchronously."""
        validated_url = validate_target_url(raw_url)
        audit_id = uuid.uuid4().hex
        job = self.job_store.create_job(audit_id, validated_url)

        # Launch background runner
        self.executor.submit(self._execute_job, audit_id, validated_url)
        return job

    def _execute_job(self, audit_id: str, url: str) -> None:
        """Worker task executed in thread pool."""
        # Acquire concurrency semaphore to avoid saturating dev machine or network
        acquired = self.job_store.concurrency_semaphore.acquire(timeout=DEFAULT_TIMEOUT_SECONDS)
        if not acquired:
            self.job_store.mark_failed(
                audit_id, "Audit could not be started: maximum concurrent audit limit reached."
            )
            return

        try:
            self.job_store.mark_running(audit_id)
            report = self._run_engine_with_timeout(url, timeout=DEFAULT_TIMEOUT_SECONDS)
            self.job_store.mark_completed(audit_id, report)
        except concurrent.futures.TimeoutError:
            self.job_store.mark_failed(
                audit_id, f"Audit timed out after {DEFAULT_TIMEOUT_SECONDS} seconds."
            )
        except Exception as e:
            logger.exception("Audit job %s failed with exception", audit_id)
            self.job_store.mark_failed(audit_id, f"Audit execution failed: {type(e).__name__}: {str(e)}")
        finally:
            self.job_store.concurrency_semaphore.release()

    def _run_engine_with_timeout(self, url: str, timeout: int) -> Dict[str, Any]:
        """Invoke existing crawl() and compose() under a strict execution timeout."""
        from compose_report import compose
        from crawl_site import crawl

        worker_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        def _do_crawl_and_compose() -> Dict[str, Any]:
            snap = crawl(url)
            report = compose(snap)
            # Verify output conformance
            if not isinstance(report, dict) or "findings" not in report or "summary" not in report:
                raise ValueError("Engine returned malformed report structure.")
            return report

        future = worker_pool.submit(_do_crawl_and_compose)
        try:
            return future.result(timeout=timeout)
        finally:
            worker_pool.shutdown(wait=False, cancel_futures=True)


# Default shared service instance
audit_service = AuditService()
