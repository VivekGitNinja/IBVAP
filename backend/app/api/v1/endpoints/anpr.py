"""ANPR (Automatic Number Plate Recognition) checkpost endpoints."""

from datetime import datetime, timedelta
import random
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.db.session import get_db

router = APIRouter()

class PlateIn(BaseModel):
    plate_number: str
    vehicle_type: str = "LMV"
    bop: str = "BOP-01"
    confidence: float = 0.92
    status: str = "CLEARED"
    notes: Optional[str] = None

class WatchlistPlateIn(BaseModel):
    plate_number: str
    reason: str
    agency: str = "Intelligence Bureau / State Police"
    threat_level: str = "HIGH"
    vehicle_model: Optional[str] = None

# Initial vehicle watchlist (stolen / flagged vehicles)
WATCHLIST_DB = [
    {
        "id": 1,
        "plate_number": "JK 02 C 5678",
        "reason": "Reported Stolen — Suspected Cross-Border Infiltration Vector",
        "agency": "NIA / J&K Police",
        "threat_level": "CRITICAL",
        "vehicle_model": "Mahindra Scorpio (White)",
        "added_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
    },
    {
        "id": 2,
        "plate_number": "UP 16 AK 4432",
        "reason": "Wanted in Contraband / Hawala Smuggling Case",
        "agency": "Narcotics Control Bureau",
        "threat_level": "HIGH",
        "vehicle_model": "Toyota Innova (Silver)",
        "added_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
    },
    {
        "id": 3,
        "plate_number": "PB 10 Z 9901",
        "reason": "Surveillance Flag — Suspicious Border Reconnaissance",
        "agency": "SSB Intelligence Unit",
        "threat_level": "MEDIUM",
        "vehicle_model": "Tata Xenon Pickup",
        "added_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
    },
]

# Simulated live scanned plates database
SCANNED_PLATES = [
    {
        "id": 1,
        "plate_number": "JK 02 C 5678",
        "vehicle_type": "SUV / LMV",
        "vehicle_model": "Mahindra Scorpio",
        "bop": "BOP-01 Road Checkpost",
        "confidence": 0.94,
        "status": "STOLEN_FLAGGED",
        "state_origin": "Jammu & Kashmir",
        "speed_kmh": 42,
        "lane": "Inbound Gate 2",
        "barrier_status": "INTERCEPT_ENGAGED",
        "timestamp": (datetime.utcnow() - timedelta(minutes=4)).isoformat(),
        "crop_url": "/api/v1/cameras/4/snapshot",
    },
    {
        "id": 2,
        "plate_number": "DL 01 AB 1234",
        "vehicle_type": "Civilian Sedan",
        "vehicle_model": "Maruti Dzire",
        "bop": "BOP-01 Gate",
        "confidence": 0.97,
        "status": "CLEARED",
        "state_origin": "Delhi NCT",
        "speed_kmh": 28,
        "lane": "Inbound Gate 1",
        "barrier_status": "OPEN",
        "timestamp": (datetime.utcnow() - timedelta(minutes=14)).isoformat(),
        "crop_url": "/api/v1/cameras/1/snapshot",
    },
    {
        "id": 3,
        "plate_number": "ARMY 21B 00921",
        "vehicle_type": "Military Convoy",
        "vehicle_model": "Ashok Leyland Stallion",
        "bop": "BOP-02 Watchtower Post",
        "confidence": 0.99,
        "status": "MILITARY_PRIORITY",
        "state_origin": "Indian Armed Forces",
        "speed_kmh": 35,
        "lane": "Military Transit Corridor",
        "barrier_status": "AUTOMATIC_PASS",
        "timestamp": (datetime.utcnow() - timedelta(minutes=25)).isoformat(),
        "crop_url": "/api/v1/cameras/3/snapshot",
    },
    {
        "id": 4,
        "plate_number": "HR 26 DQ 9921",
        "vehicle_type": "Heavy Commercial (HMV)",
        "vehicle_model": "Tata Prima Truck",
        "bop": "BOP-03 Freight Checkpoint",
        "confidence": 0.88,
        "status": "CUSTOMS_HOLD",
        "state_origin": "Haryana",
        "speed_kmh": 18,
        "lane": "Commercial Cargo Lane",
        "barrier_status": "INSPECTION_HOLD",
        "timestamp": (datetime.utcnow() - timedelta(minutes=38)).isoformat(),
        "crop_url": "/api/v1/cameras/4/snapshot",
    },
    {
        "id": 5,
        "plate_number": "UP 16 AK 4432",
        "vehicle_type": "MUV / Passenger",
        "vehicle_model": "Toyota Innova",
        "bop": "BOP-03 Freight Checkpoint",
        "confidence": 0.91,
        "status": "SUSPICIOUS_MATCH",
        "state_origin": "Uttar Pradesh",
        "speed_kmh": 58,
        "lane": "Outbound Highway",
        "barrier_status": "INTERCEPT_TRIGGERED",
        "timestamp": (datetime.utcnow() - timedelta(minutes=52)).isoformat(),
        "crop_url": "/api/v1/cameras/4/snapshot",
    },
]

BARRIER_STATE = {"status": "ARMED", "barrier_raised": False, "mode": "AUTO_INTERCEPT"}

@router.get("/plates")
def list_scanned_plates(status: Optional[str] = None, bop: Optional[str] = None, search: Optional[str] = None):
    """List scanned vehicle license plates with OCR metadata."""
    results = list(SCANNED_PLATES)
    if status:
        results = [p for p in results if p["status"].lower() == status.lower()]
    if bop:
        results = [p for p in results if bop.lower() in p["bop"].lower()]
    if search:
        s = search.lower()
        results = [p for p in results if s in p["plate_number"].lower() or s in p.get("vehicle_model", "").lower()]
    return results

@router.post("/scan")
def scan_plate(data: PlateIn):
    """Record an ANPR scan and check against the stolen vehicle watchlist."""
    plate_clean = data.plate_number.strip().upper()
    
    # Check against watchlist
    is_flagged = any(w["plate_number"].upper() == plate_clean for w in WATCHLIST_DB)
    computed_status = "STOLEN_FLAGGED" if is_flagged else data.status

    record = {
        "id": len(SCANNED_PLATES) + 1,
        "plate_number": plate_clean,
        "vehicle_type": data.vehicle_type,
        "vehicle_model": "Standard Civilian Vehicle",
        "bop": data.bop,
        "confidence": data.confidence,
        "status": computed_status,
        "state_origin": plate_clean[:2] if len(plate_clean) >= 2 else "IND",
        "speed_kmh": random.randint(20, 65),
        "lane": "Inbound Gate 1",
        "barrier_status": "INTERCEPT_ENGAGED" if is_flagged else "CLEARED",
        "timestamp": datetime.utcnow().isoformat(),
        "crop_url": "/api/v1/cameras/4/snapshot",
    }
    SCANNED_PLATES.insert(0, record)
    return record

@router.get("/watchlist")
def get_anpr_watchlist():
    """Get active blacklisted/stolen vehicle watchlist."""
    return WATCHLIST_DB

@router.post("/watchlist")
def add_to_watchlist(data: WatchlistPlateIn):
    """Add a license plate to the border intelligence watchlist."""
    record = {
        "id": len(WATCHLIST_DB) + 1,
        "plate_number": data.plate_number.strip().upper(),
        "reason": data.reason,
        "agency": data.agency,
        "threat_level": data.threat_level,
        "vehicle_model": data.vehicle_model or "Unknown Model",
        "added_at": datetime.utcnow().isoformat(),
    }
    WATCHLIST_DB.insert(0, record)
    return record

@router.post("/barrier/toggle")
def toggle_barrier():
    """Remotely engage or release checkpost vehicle intercept barrier."""
    BARRIER_STATE["barrier_raised"] = not BARRIER_STATE["barrier_raised"]
    BARRIER_STATE["status"] = "BARRIER_OPEN" if BARRIER_STATE["barrier_raised"] else "BARRIER_ENGAGED"
    return BARRIER_STATE

@router.get("/stats")
def get_anpr_stats():
    """Get checkpost ANPR telemetry."""
    total = len(SCANNED_PLATES)
    flagged = sum(1 for p in SCANNED_PLATES if "flag" in p["status"].lower() or "stolen" in p["status"].lower())
    avg_conf = sum(p["confidence"] for p in SCANNED_PLATES) / max(total, 1)
    return {
        "total_vehicles_24h": total,
        "flagged_intercepts": flagged,
        "cleared_vehicles": total - flagged,
        "avg_ocr_confidence": round(avg_conf * 100, 1),
        "barrier_state": BARRIER_STATE,
    }
