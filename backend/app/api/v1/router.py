"""API v1 router — aggregates all endpoint modules."""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health, auth, cameras, zones, incidents, evidence,
    demo, events, audit, sync, metrics,
    anpr, frs, qrt,
)

api = APIRouter()

# Core
api.include_router(health.router, prefix="/health", tags=["health"])
api.add_api_route("/status", health.system_status, methods=["GET"], tags=["health"])
api.include_router(auth.router, prefix="/auth", tags=["auth"])

# Entities
api.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
api.include_router(zones.router, prefix="/zones", tags=["zones"])
api.include_router(events.router, prefix="/events", tags=["events"])
api.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
api.include_router(evidence.router, prefix="/evidence", tags=["evidence"])

# C4ISR Specialized Modules
api.include_router(anpr.router, prefix="/anpr", tags=["anpr"])
api.include_router(frs.router, prefix="/frs", tags=["frs"])
api.include_router(qrt.router, prefix="/qrt", tags=["qrt"])

# Operations
api.include_router(audit.router, prefix="/audit", tags=["audit"])
api.include_router(sync.router, prefix="/sync", tags=["sync"])
api.include_router(metrics.router, prefix="/metrics", tags=["metrics"])

# Demo
api.include_router(demo.router, prefix="/demo", tags=["demo"])
