"""Command & Control (C2) Outbound Webhook Integration Service.

Dispatches cryptographic incident alerts to external command centers (SSB/MHA C4ISR),
signed via HMAC-SHA256 with 3-attempt exponential backoff.
"""

from __future__ import annotations
import hmac
import hashlib
import json
import logging
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import urllib.request
import urllib.error

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def compute_c2_signature(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for C2 payload."""
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def verify_c2_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Verify incoming X-IBVAP-Signature header matches computed HMAC."""
    if not signature_header:
        return False
    expected = compute_c2_signature(payload_bytes, secret)
    return hmac.compare_digest(signature_header.strip(), expected.strip())


def format_c2_payload(
    incident: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Structure incident into standardized C4ISR tactical dispatch payload."""
    now_utc = datetime.now(timezone.utc).isoformat()
    ev_digest = evidence.get("sha256") if evidence else None
    
    return {
        "event_id": incident.get("incident_code", f"INC-{int(time.time())}"),
        "timestamp": now_utc,
        "source": "IBVAP-TACTICAL-EDGE",
        "category": "PERIMETER_SECURITY_VIOLATION",
        "threat_assessment": {
            "severity": incident.get("severity", "MEDIUM"),
            "threat_score": float(incident.get("threat_score", 50.0)),
            "confidence": float(incident.get("confidence", 0.85)),
        },
        "target": {
            "title": incident.get("title", "Security Alert"),
            "zone_name": incident.get("zone_name", "Perimeter"),
            "camera_id": incident.get("camera_id"),
            "track_ids": incident.get("track_ids", []),
        },
        "evidence_seal": {
            "evidence_id": evidence.get("id") if evidence else None,
            "evidence_type": evidence.get("evidence_type") if evidence else "snapshot",
            "sha256": ev_digest or "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
            "statute": "Bharatiya Sakshya Adhiniyam, 2023 — Section 63",
        },
    }


def send_webhook_http(
    url: str,
    payload: Dict[str, Any],
    secret: str,
    timeout: float = 3.0,
    max_retries: int = 3,
) -> bool:
    """Send JSON payload over HTTP POST with HMAC-SHA256 signature and retries."""
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    sig = compute_c2_signature(payload_bytes, secret)
    timestamp = str(int(time.time()))

    req = urllib.request.Request(
        url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "IBVAP-C4ISR-Dispatcher/2.0",
            "X-IBVAP-Signature": sig,
            "X-IBVAP-Timestamp": timestamp,
        },
        method="POST",
    )

    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    logger.info(f"C2 Webhook dispatched successfully to {url} (Attempt {attempt})")
                    return True
                else:
                    logger.warning(f"C2 Webhook server returned HTTP {resp.status} on attempt {attempt}")
        except urllib.error.HTTPError as e:
            logger.warning(f"C2 Webhook HTTP Error {e.code} on attempt {attempt}: {e.reason}")
        except Exception as e:
            logger.warning(f"C2 Webhook dispatch error on attempt {attempt}: {e}")

        if attempt < max_retries:
            backoff = 0.5 * (2 ** (attempt - 1))
            time.sleep(backoff)

    return False


def dispatch_incident_webhook(
    incident: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None,
    url: Optional[str] = None,
    secret: Optional[str] = None,
    background: bool = True,
) -> bool:
    """Dispatch an incident webhook. If background=True, dispatches in a daemon thread."""
    target_url = url or settings.c2_webhook_url
    target_secret = secret or settings.c2_webhook_secret

    if not target_url:
        # C2 Webhook not configured — clean skip
        return False

    payload = format_c2_payload(incident, evidence)

    if background:
        t = threading.Thread(
            target=send_webhook_http,
            args=(target_url, payload, target_secret),
            daemon=True,
        )
        t.start()
        return True
    else:
        return send_webhook_http(target_url, payload, target_secret)
