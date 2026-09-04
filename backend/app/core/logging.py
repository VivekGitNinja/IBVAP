"""
IBVAP — Structured JSON Logging & Distributed Tracing
Provides RFC-compliant structured JSON logging and asynchronous ContextVar-backed trace propagation.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

# Context variable to hold trace ID across async coroutines
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """Retrieve the current coroutine's distributed trace ID."""
    return trace_id_ctx.get()


def set_trace_id(trace_id: str) -> None:
    """Assign a distributed trace ID to the current execution context."""
    trace_id_ctx.set(trace_id)


class StructuredJSONFormatter(logging.Formatter):
    """
    High-performance JSON Formatter for production observability (Prometheus/Loki/ELK).
    Emits single-line JSON with standard timestamp, level, logger, trace_id, and arbitrary extra fields.
    """

    def __init__(self, fmt_keys: Optional[dict[str, str]] = None):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    def format(self, record: logging.LogRecord) -> str:
        # Resolve trace ID from context variable or explicit record attribute
        tid = getattr(record, "trace_id", None) or get_trace_id()

        message = record.getMessage()
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "trace_id": tid or "system",
        }

        # Include caller file and line in debug/warning/error
        if record.levelno >= logging.WARNING or record.levelno <= logging.DEBUG:
            log_data["caller"] = f"{record.filename}:{record.lineno}"

        # Capture exception traceback if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Merge any custom fields passed via extra={'key': 'value'}
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message", "trace_id"
        }
        for key, val in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                try:
                    # Ensure value is JSON-serializable
                    json.dumps(val)
                    log_data[key] = val
                except (TypeError, OverflowError):
                    log_data[key] = str(val)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", json_format: bool = True) -> logging.Logger:
    """
    Initialize root and application loggers with structured output.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Clean existing handlers
    for handler in list(root.handlers):
        root.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    if json_format:
        stream_handler.setFormatter(StructuredJSONFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )

    root.addHandler(stream_handler)

    # Align uvicorn access/error loggers
    for uvi_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvi_logger = logging.getLogger(uvi_logger_name)
        uvi_logger.handlers = [stream_handler]
        uvi_logger.propagate = False

    return logging.getLogger("ibvap")


def get_logger(name: str = "ibvap") -> logging.Logger:
    """Return an instrumented logger instance."""
    return logging.getLogger(name)
