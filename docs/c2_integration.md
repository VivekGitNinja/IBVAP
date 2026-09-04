# IBVAP Command & Control (C2) Webhook Integration
## Technical Reference — SIH 2026 / SSB MHA (PS-26187)

---

## 1. Overview

The Intelligent Border Video Analytics Platform (IBVAP) integrates with higher-echelon Command & Control (C2 / C4ISR) systems via outbound, tamper-evident HTTP webhooks. Whenever a perimeter security incident is escalated to `OPEN` status (e.g., virtual fence breach, direction violation, loitering, crowd gathering, or watchlist facial match), IBVAP dispatches a cryptographically sealed alert.

---

## 2. Configuration

C2 integration is configured via environment variables or `backend/app/core/config.py`:

| Parameter | Environment Variable | Default | Description |
|-----------|----------------------|---------|-------------|
| `c2_webhook_url` | `C2_WEBHOOK_URL` | `""` (empty) | Destination C2 receiver endpoint URL. If empty, webhook dispatch is disabled. |
| `c2_webhook_secret` | `C2_WEBHOOK_SECRET` | `"c2-tactical-secret-key"` | Pre-shared HMAC-SHA256 secret key for signing alerts. |

When `c2_webhook_url` is left empty, webhook dispatch cleanly no-ops with zero network overhead.

---

## 3. Dispatch Protocol & Headers

Webhooks are transmitted via HTTP `POST` requests with JSON payloads and the following security headers:

| Header | Description | Example |
|--------|-------------|---------|
| `Content-Type` | MIME type | `application/json` |
| `User-Agent` | Platform identifier | `IBVAP-C4ISR-Dispatcher/2.0` |
| `X-IBVAP-Signature` | HMAC-SHA256 signature of the raw JSON body | `sha256=5aff9dd82163b21...` |
| `X-IBVAP-Timestamp` | Dispatch UNIX epoch timestamp (seconds) | `1772714400` |

---

## 4. JSON Payload Schema

Alert payloads adhere to the standard tactical defense event schema:

```json
{
  "event_id": "INC-JOB27-FRS-S1-A1B2",
  "timestamp": "2026-09-04T18:30:00.000000Z",
  "source": "IBVAP-TACTICAL-EDGE",
  "category": "PERIMETER_SECURITY_VIOLATION",
  "threat_assessment": {
    "severity": "CRITICAL",
    "threat_score": 95.0,
    "confidence": 0.945
  },
  "target": {
    "title": "Watchlist Match Alert: Suspect Alpha (94.5% Match)",
    "zone_name": "Perimeter Line Bravo",
    "camera_id": 1,
    "track_ids": ["TRK-1"]
  },
  "evidence_seal": {
    "evidence_id": 104,
    "evidence_type": "snapshot",
    "sha256": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "statute": "Bharatiya Sakshya Adhiniyam, 2023 — Section 63"
  }
}
```

### Schema Field Definitions

- **`event_id`** (`string`): Unique incident identifier.
- **`timestamp`** (`string`): UTC ISO-8601 incident timestamp.
- **`source`** (`string`): Platform identity (`IBVAP-TACTICAL-EDGE`).
- **`category`** (`string`): Event classification code (`PERIMETER_SECURITY_VIOLATION`).
- **`threat_assessment`** (`object`):
  - **`severity`** (`string`): `CRITICAL` | `HIGH` | `MEDIUM` | `LOW`.
  - **`threat_score`** (`float`): Composite threat rating (0.0 to 100.0).
  - **`confidence`** (`float`): AI model detection confidence (0.0 to 1.0).
- **`target`** (`object`):
  - **`title`** (`string`): Incident summary title.
  - **`zone_name`** (`string`): Name of the breached virtual zone or sector.
  - **`camera_id`** (`integer` or `null`): Source camera index.
  - **`track_ids`** (`array` of `string`): Multi-object tracking IDs associated with the breach.
- **`evidence_seal`** (`object`):
  - **`evidence_id`** (`integer` or `null`): Database record index.
  - **`evidence_type`** (`string`): `snapshot` or `clip`.
  - **`sha256`** (`string`): 64-character hexadecimal SHA-256 cryptographic digest of the raw evidence file.
  - **`statute`** (`string`): Legal evidentiary certificate authority (`Bharatiya Sakshya Adhiniyam, 2023 — Section 63`).

---

## 5. HMAC-SHA256 Signature Verification

Receiving systems verify payload integrity and authenticity by computing the HMAC-SHA256 over the exact UTF-8 payload bytes using the shared secret.

### Python Verification Example

```python
import hashlib
import hmac

def verify_c2_webhook(raw_body_bytes: bytes, signature_header: str, secret: str) -> bool:
    \"\"\"Verifies incoming X-IBVAP-Signature header matches computed HMAC.\"\"\"
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    
    expected_hash = hmac.new(
        secret.encode("utf-8"),
        raw_body_bytes,
        hashlib.sha256
    ).hexdigest()
    
    expected_signature = f"sha256={expected_hash}"
    return hmac.compare_digest(signature_header.strip(), expected_signature)
```

---

## 6. Resilience & Non-Blocking Guarantee

1. **Non-Blocking Daemon Execution**: Webhook dispatch is offloaded to detached background daemon threads (`background=True`), ensuring computer vision frame processing and video analysis are **never blocked or throttled by external network latency**.
2. **Exponential Backoff Retries**: If the receiving C2 endpoint is temporarily unresponsive or returns a non-2xx status, IBVAP retries up to **3 times** with exponential backoff (`0.5s`, `1.0s`, `2.0s`).
3. **Failure Isolation**: Network errors, timeouts, or invalid destination URLs are logged as warnings and gracefully discarded without disrupting platform operations.

---

*Document maintained by IBVAP Tactical Communications — SIH 2026 | PS-26187*
