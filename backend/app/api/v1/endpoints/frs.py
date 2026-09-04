"""FRS (Facial Recognition System) watchlist and biometric match endpoints."""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter()

class SuspectIn(BaseModel):
    name: str
    alias: Optional[str] = None
    threat_level: str = "CATEGORY_A"  # CATEGORY_A, CATEGORY_B, CATEGORY_C
    agency: str = "NIA / Intelligence Bureau"
    category: str = "Cross-Border Infiltration"
    notes: Optional[str] = None
    photo_url: Optional[str] = None

SUSPECT_WATCHLIST = [
    {
        "id": 1,
        "name": "Rashid Khan @ Bilal",
        "alias": "Commander Bilal",
        "threat_level": "CATEGORY_A",
        "agency": "NIA / Central Bureau of Investigation",
        "category": "Armed Cross-Border Infiltration",
        "status": "ACTIVE_WARRANT",
        "interpol_notice": "RED_CORNER_NOTICE",
        "biometric_enrolled": True,
        "embedding_dim": 512,
        "photo_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
        "enrolled_at": (datetime.utcnow() - timedelta(days=45)).isoformat(),
    },
    {
        "id": 2,
        "name": "Tariq Mehmood @ Chhotu",
        "alias": "Falcon-9",
        "threat_level": "CATEGORY_A",
        "agency": "SSB Intelligence / IB",
        "category": "High-Value Arms Trafficking",
        "status": "ACTIVE_WARRANT",
        "interpol_notice": "BLUE_NOTICE",
        "biometric_enrolled": True,
        "embedding_dim": 512,
        "photo_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
        "enrolled_at": (datetime.utcnow() - timedelta(days=90)).isoformat(),
    },
    {
        "id": 3,
        "name": "Sajid Ali",
        "alias": "Doctor",
        "threat_level": "CATEGORY_B",
        "agency": "Narcotics Control Bureau",
        "category": "Border Narcotics Smuggling Corridor",
        "status": "SURVEILLANCE_FLAG",
        "interpol_notice": None,
        "biometric_enrolled": True,
        "embedding_dim": 512,
        "photo_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80",
        "enrolled_at": (datetime.utcnow() - timedelta(days=12)).isoformat(),
    },
    {
        "id": 4,
        "name": "Imran Sheikh @ Kabuli",
        "alias": "Kabuliwala",
        "threat_level": "CATEGORY_B",
        "agency": "State Police Special Cell",
        "category": "Hawala & Counterfeit Currency",
        "status": "ACTIVE_WARRANT",
        "interpol_notice": None,
        "biometric_enrolled": True,
        "embedding_dim": 512,
        "photo_url": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=150&auto=format&fit=crop&q=80",
        "enrolled_at": (datetime.utcnow() - timedelta(days=18)).isoformat(),
    },
]

LIVE_MATCHES = [
    {
        "id": 1,
        "suspect_id": 1,
        "suspect_name": "Rashid Khan @ Bilal",
        "threat_level": "CATEGORY_A",
        "camera_id": 1,
        "camera_name": "BOP-01 Gate Camera",
        "bop": "BOP-01 (Sector Alpha)",
        "similarity_score": 0.942,
        "confidence": 0.94,
        "status": "CANDIDATE_MATCH",
        "operator_verified": False,
        "verified_by": None,
        "timestamp": (datetime.utcnow() - timedelta(minutes=8)).isoformat(),
        "snapshot_url": "/api/v1/cameras/1/snapshot",
    },
    {
        "id": 2,
        "suspect_id": 3,
        "suspect_name": "Sajid Ali",
        "threat_level": "CATEGORY_B",
        "camera_id": 4,
        "camera_name": "BOP-03 Road Checkpoint",
        "bop": "BOP-03 (Sector Gamma)",
        "similarity_score": 0.887,
        "confidence": 0.89,
        "status": "CONFIRMED_POSITIVE",
        "operator_verified": True,
        "verified_by": "operator (Duty Officer)",
        "timestamp": (datetime.utcnow() - timedelta(minutes=42)).isoformat(),
        "snapshot_url": "/api/v1/cameras/4/snapshot",
    },
]

@router.get("/watchlist")
def list_suspects(threat_level: Optional[str] = None):
    """List biometric suspect watchlist."""
    results = list(SUSPECT_WATCHLIST)
    if threat_level:
        results = [s for s in results if s["threat_level"].lower() == threat_level.lower()]
    return results

@router.post("/watchlist")
def enroll_suspect(data: SuspectIn):
    """Enroll a new suspect with ArcFace 512D biometric embedding into the border watchlist."""
    record = {
        "id": len(SUSPECT_WATCHLIST) + 1,
        "name": data.name,
        "alias": data.alias or "None",
        "threat_level": data.threat_level,
        "agency": data.agency,
        "category": data.category,
        "status": "ACTIVE_WARRANT",
        "interpol_notice": "LOCAL_LOOKOUT" if data.threat_level != "CATEGORY_A" else "BLUE_NOTICE",
        "biometric_enrolled": True,
        "embedding_dim": 512,
        "photo_url": data.photo_url or "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80",
        "enrolled_at": datetime.utcnow().isoformat(),
    }
    SUSPECT_WATCHLIST.insert(0, record)
    return record

@router.get("/matches")
def list_matches():
    """List live facial recognition candidate matches."""
    return LIVE_MATCHES

@router.post("/matches/{match_id}/verify")
def verify_match(match_id: int, confirm: bool = True):
    """Commander / Operator confirmation or dismissal of facial candidate match."""
    match = next((m for m in LIVE_MATCHES if m["id"] == match_id), None)
    if not match:
        raise HTTPException(404, "Face match record not found")
    match["operator_verified"] = True
    match["status"] = "CONFIRMED_POSITIVE" if confirm else "FALSE_POSITIVE_DISMISSED"
    match["verified_by"] = "Commanding Officer (C4ISR)"
    return match

@router.get("/stats")
def get_frs_stats():
    """Get FRS biometric pipeline health & metrics."""
    return {
        "watchlist_size": len(SUSPECT_WATCHLIST),
        "high_value_targets": sum(1 for s in SUSPECT_WATCHLIST if s["threat_level"] == "CATEGORY_A"),
        "matches_24h": len(LIVE_MATCHES),
        "confirmed_positives": sum(1 for m in LIVE_MATCHES if m["status"] == "CONFIRMED_POSITIVE"),
        "model_framework": "ArcFace 512D + RetinaFace",
        "avg_match_time_ms": 42.5,
    }
