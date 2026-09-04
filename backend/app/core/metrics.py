"""
IBVAP — Prometheus Metrics Engine & OpenMetrics Collector
Standard-library, thread-safe Prometheus metrics implementation providing
full compliance with Prometheus Exposition Format 0.0.4.
"""

import os
import threading
import time
from typing import Any, Dict, List, Tuple

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

_process = psutil.Process(os.getpid()) if _HAS_PSUTIL else None
_startup_time = time.time()


def _format_labels(labels: Dict[str, str]) -> str:
    """Format dictionary of labels into Prometheus string {k1="v1",k2="v2"}."""
    if not labels:
        return ""
    items = [f'{k}="{v}"' for k, v in sorted(labels.items())]
    return "{" + ",".join(items) + "}"


class Counter:
    """Monotonically increasing Prometheus counter."""

    def __init__(self, name: str, description: str, label_names: List[str]):
        self.name = name
        self.description = description
        self.label_names = sorted(label_names)
        self._values: Dict[Tuple[Tuple[str, str], ...], float] = {}
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        if amount < 0:
            raise ValueError("Counters can only be incremented by non-negative amounts.")
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def collect(self) -> str:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            if not self._values and not self.label_names:
                lines.append(f"{self.name} 0.0")
            for key, val in sorted(self._values.items()):
                lbl_str = _format_labels(dict(key))
                lines.append(f"{self.name}{lbl_str} {val}")
        return "\n".join(lines)


class Gauge:
    """Prometheus gauge representing a value that can arbitrarily go up and down."""

    def __init__(self, name: str, description: str, label_names: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = sorted(label_names) if label_names else []
        self._values: Dict[Tuple[Tuple[str, str], ...], float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, **labels: str) -> None:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            self._values[key] = float(value)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def dec(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) - amount

    def collect(self) -> str:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            if not self._values and not self.label_names:
                lines.append(f"{self.name} 0.0")
            for key, val in sorted(self._values.items()):
                lbl_str = _format_labels(dict(key))
                lines.append(f"{self.name}{lbl_str} {val}")
        return "\n".join(lines)


class Histogram:
    """Prometheus histogram for latency distributions."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self, name: str, description: str, label_names: List[str], buckets: Tuple[float, ...] = None):
        self.name = name
        self.description = description
        self.label_names = sorted(label_names)
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._buckets_data: Dict[Tuple[Tuple[str, str], ...], Dict[float, int]] = {}
        self._sum_data: Dict[Tuple[Tuple[str, str], ...], float] = {}
        self._count_data: Dict[Tuple[Tuple[str, str], ...], int] = {}
        self._lock = threading.Lock()

    def observe(self, amount: float, **labels: str) -> None:
        key = tuple(sorted((k, str(v)) for k, v in labels.items()))
        with self._lock:
            if key not in self._buckets_data:
                self._buckets_data[key] = {b: 0 for b in self.buckets}
                self._sum_data[key] = 0.0
                self._count_data[key] = 0

            self._sum_data[key] += amount
            self._count_data[key] += 1
            for b in self.buckets:
                if amount <= b:
                    self._buckets_data[key][b] += 1

    def collect(self) -> str:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            for key in sorted(self._buckets_data.keys()):
                base_labels = dict(key)
                running_count = 0
                for b in self.buckets:
                    running_count = self._buckets_data[key][b]
                    lbl = {**base_labels, "le": str(b)}
                    lines.append(f"{self.name}_bucket{_format_labels(lbl)} {running_count}")
                # +Inf bucket equals total count
                total_cnt = self._count_data[key]
                lines.append(f"{self.name}_bucket{_format_labels({**base_labels, 'le': '+Inf'})} {total_cnt}")
                lines.append(f"{self.name}_sum{_format_labels(base_labels)} {self._sum_data[key]}")
                lines.append(f"{self.name}_count{_format_labels(base_labels)} {total_cnt}")
        return "\n".join(lines)


# ── Global Metric Registry ──────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    name="ibvap_http_requests_total",
    description="Total count of incoming HTTP requests processed by IBVAP.",
    label_names=["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    name="ibvap_http_request_duration_seconds",
    description="Latency histogram of HTTP requests in seconds.",
    label_names=["method", "path"],
)

ACTIVE_WS_CONNECTIONS = Gauge(
    name="ibvap_active_websocket_connections",
    description="Number of active real-time client WebSocket connections.",
    label_names=[],
)

DETECTIONS_TOTAL = Counter(
    name="ibvap_detections_total",
    description="Total number of AI border detections recorded.",
    label_names=["type", "camera_id"],
)

UPTIME_SECONDS = Gauge(
    name="ibvap_uptime_seconds",
    description="Total seconds IBVAP backend service has been operational.",
    label_names=[],
)

PROCESS_CPU_PERCENT = Gauge(
    name="ibvap_process_cpu_percent",
    description="Process CPU utilization percentage.",
    label_names=[],
)

PROCESS_MEMORY_BYTES = Gauge(
    name="ibvap_process_memory_bytes",
    description="Process Resident Set Size (RSS) memory in bytes.",
    label_names=[],
)

SYSTEM_INFO = Gauge(
    name="ibvap_system_info",
    description="IBVAP system release and build metadata.",
    label_names=["version", "platform", "environment"],
)
# Pre-initialize system info
SYSTEM_INFO.set(1.0, version="2.0.0", platform="IBVAP-Tactical", environment="production")


def record_http_request(method: str, path: str, status: int, duration_seconds: float) -> None:
    """Record an HTTP request in the Prometheus metrics collectors."""
    # Sanitize dynamic path segments (e.g. IDs) to avoid cardinality explosion
    clean_path = path
    segments = path.split("/")
    sanitized_segments = []
    for seg in segments:
        if seg.isdigit():
            sanitized_segments.append(":id")
        elif len(seg) > 20: # e.g. hashes/UUIDs
            sanitized_segments.append(":param")
        else:
            sanitized_segments.append(seg)
    clean_path = "/".join(sanitized_segments)

    HTTP_REQUESTS_TOTAL.inc(1.0, method=method, path=clean_path, status=str(status))
    HTTP_REQUEST_DURATION_SECONDS.observe(duration_seconds, method=method, path=clean_path)


def record_detection(det_type: str, camera_id: Any = "") -> None:
    """Record an AI detection event."""
    DETECTIONS_TOTAL.inc(1.0, type=str(det_type), camera_id=str(camera_id))


def set_active_ws_count(count: int) -> None:
    """Update active WebSocket connections gauge."""
    ACTIVE_WS_CONNECTIONS.set(float(count))


def generate_metrics_text() -> str:
    """
    Collect and serialize all registered Prometheus metrics into
    valid Prometheus/OpenMetrics text format (version 0.0.4).
    """
    # Sample real-time dynamic gauges
    UPTIME_SECONDS.set(time.time() - _startup_time)
    if _process:
        try:
            mem = _process.memory_info().rss
            PROCESS_MEMORY_BYTES.set(float(mem))
            cpu = _process.cpu_percent(interval=None)
            PROCESS_CPU_PERCENT.set(float(cpu))
        except Exception:
            pass

    collectors = [
        SYSTEM_INFO,
        UPTIME_SECONDS,
        PROCESS_CPU_PERCENT,
        PROCESS_MEMORY_BYTES,
        ACTIVE_WS_CONNECTIONS,
        HTTP_REQUESTS_TOTAL,
        HTTP_REQUEST_DURATION_SECONDS,
        DETECTIONS_TOTAL,
    ]

    parts = [c.collect() for c in collectors]
    # Filter out empty entries and terminate with newline
    return "\n\n".join(p for p in parts if p.strip()) + "\n"
