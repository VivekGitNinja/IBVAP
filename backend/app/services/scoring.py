"""
Explainable Threat Scoring Engine 2.0

Produces a transparent threat assessment with:
- Score (0-100)
- Severity (LOW/MEDIUM/HIGH/CRITICAL)
- Confidence (0-1)
- Reason list with contributions
- Supporting signals
- Uncertainty assessment
- Recommended action

Every score is explainable — no black-box decisions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# Severity thresholds
SEVERITY_THRESHOLDS = [
    (85, "CRITICAL"),
    (65, "HIGH"),
    (40, "MEDIUM"),
    (0, "LOW"),
]

# Configurable signal weights
DEFAULT_WEIGHTS = {
    "confidence": 12,
    "zone_severity": 25,
    "boundary_crossing": 18,
    "loitering": 12,
    "night": 8,
    "vehicle_context": 5,
    "behavior_anomaly": 10,
    "repeated_activity": 5,
    "camera_health_degraded": 2,
    "cross_camera_corroboration": 3,
}

# Signal descriptions for UI
SIGNAL_DESCRIPTIONS = {
    "confidence": "Detection confidence",
    "zone_severity": "Zone severity level",
    "boundary_crossing": "Virtual fence boundary crossing",
    "loitering": "Prolonged presence in zone",
    "night": "Night-time context",
    "vehicle_context": "Vehicle detected",
    "behavior_anomaly": "Unusual behavior pattern",
    "repeated_activity": "Repeated boundary crossing",
    "camera_health_degraded": "Camera health degraded",
    "cross_camera_corroboration": "Cross-camera event correlation",
}


@dataclass
class ThreatAssessment:
    """Complete threat assessment output."""
    score: float = 0.0
    severity: str = "LOW"
    confidence: float = 0.0
    reasons: list[str] = field(default_factory=list)
    signal_contributions: dict[str, float] = field(default_factory=dict)
    supporting_signals: dict[str, Any] = field(default_factory=dict)
    uncertainty: str = ""
    recommended_action: str = "Continue monitoring."
    ai_assessment: dict[str, Any] = field(default_factory=dict)


def compute_threat_score(
    signals: dict[str, float],
    weights: dict[str, float] | None = None,
    context: dict[str, Any] | None = None,
) -> ThreatAssessment:
    """Compute an explainable threat score from multiple signals.

    Args:
        signals: Signal values (0-1 scale) keyed by signal name.
        weights: Optional weight overrides. Falls back to DEFAULT_WEIGHTS.
        context: Optional context dict with extra info (e.g. camera, zone, track).

    Returns:
        ThreatAssessment with full explanation.
    """
    w = weights or DEFAULT_WEIGHTS.copy()
    ctx = context or {}

    # Compute weighted contributions
    contributions: dict[str, float] = {}
    reasons: list[str] = []
    raw_score = 0.0

    for signal_name, weight in w.items():
        value = max(0.0, min(1.0, float(signals.get(signal_name, 0.0))))
        contrib = value * weight
        contributions[signal_name] = round(contrib, 2)
        raw_score += contrib
        if value > 0.1:
            desc = SIGNAL_DESCRIPTIONS.get(signal_name, signal_name)
            reasons.append(f"{desc}: +{round(contrib, 1)}")

    # Clamp score
    score = round(max(0.0, min(100.0, raw_score)), 2)

    # Determine severity
    severity = "LOW"
    for threshold, sev in SEVERITY_THRESHOLDS:
        if score >= threshold:
            severity = sev
            break

    # Compute confidence
    conf_signals = ["confidence"]
    conf_values = [signals.get(k, 0.0) for k in conf_signals if k in signals]
    confidence = round(sum(conf_values) / max(len(conf_values), 1), 2)

    # Sort reasons by contribution (descending)
    reasons.sort(
        key=lambda r: float(r.rsplit(": ", 1)[-1].lstrip("+")) if ": +" in r else 0,
        reverse=True,
    )

    # Assess uncertainty
    uncertainty_factors = []
    if confidence < 0.5:
        uncertainty_factors.append("Detection confidence is moderate/low")
    if signals.get("confidence", 0) < 0.7:
        uncertainty_factors.append("Object classification confidence below 0.7")
    uncertainty = "; ".join(uncertainty_factors) if uncertainty_factors else "Low uncertainty"

    # Generate recommended action
    if severity == "CRITICAL":
        recommended_action = "IMMEDIATE: Verify incident on live feed. Consider escalation."
    elif severity == "HIGH":
        recommended_action = "Verify incident on live feed. Monitor for escalation."
    elif severity == "MEDIUM":
        recommended_action = "Monitor situation. Verify if conditions persist."
    else:
        recommended_action = "Continue monitoring. No immediate action required."

    # Build AI assessment for explainability
    ai_assessment = {
        "detected": ctx.get("object_type", "moving object"),
        "confidence": confidence,
        "context": ctx.get("zone_name", "monitored area"),
        "behavior": ctx.get("behavior", "normal movement"),
        "threat_contributions": contributions,
        "uncertainty": uncertainty,
        "human_action": recommended_action,
        "signals_raw": signals,
        "weights_used": w,
    }

    return ThreatAssessment(
        score=score,
        severity=severity,
        confidence=confidence,
        reasons=reasons,
        signal_contributions=contributions,
        supporting_signals=signals,
        uncertainty=uncertainty,
        recommended_action=recommended_action,
        ai_assessment=ai_assessment,
    )


def get_severity_for_score(score: float) -> str:
    """Map a raw score to severity string."""
    for threshold, sev in SEVERITY_THRESHOLDS:
        if score >= threshold:
            return sev
    return "LOW"
