"""Tests for the explainable threat scoring engine."""

from backend.app.services.scoring import (
    compute_threat_score, get_severity_for_score,
    DEFAULT_WEIGHTS, SEVERITY_THRESHOLDS,
)


def test_zero_signals_gives_low():
    """No signals should produce LOW severity."""
    result = compute_threat_score({})
    assert result.score == 0.0
    assert result.severity == "LOW"
    assert result.confidence == 0.0


def test_max_signals_gives_critical():
    """All signals at max should produce CRITICAL."""
    signals = {k: 1.0 for k in DEFAULT_WEIGHTS}
    result = compute_threat_score(signals)
    assert result.score >= 85
    assert result.severity == "CRITICAL"
    assert result.confidence > 0


def test_zone_severity_high_impact():
    """Zone severity is the highest-weighted signal."""
    signals_only_zone = {"zone_severity": 1.0}
    signals_only_behavior = {"behavior_anomaly": 1.0}
    r1 = compute_threat_score(signals_only_zone)
    r2 = compute_threat_score(signals_only_behavior)
    assert r1.score > r2.score


def test_reasons_populated():
    """Non-zero signals should produce reason strings."""
    signals = {"confidence": 0.8, "night": 1.0, "loitering": 0.5}
    result = compute_threat_score(signals)
    assert len(result.reasons) >= 2


def test_severity_thresholds():
    """Score-to-severity mapping should match thresholds."""
    assert get_severity_for_score(90) == "CRITICAL"
    assert get_severity_for_score(70) == "HIGH"
    assert get_severity_for_score(50) == "MEDIUM"
    assert get_severity_for_score(10) == "LOW"


def test_ai_assessment_structure():
    """AI assessment should contain required fields."""
    signals = {"confidence": 0.9, "zone_severity": 1.0}
    ctx = {"object_type": "person", "zone_name": "Restricted Zone", "behavior": "loitering"}
    result = compute_threat_score(signals, context=ctx)
    assert "detected" in result.ai_assessment
    assert "confidence" in result.ai_assessment
    assert "context" in result.ai_assessment
    assert "behavior" in result.ai_assessment
    assert "human_action" in result.ai_assessment


def test_recommended_action_scales_with_severity():
    """Critical incidents should have more urgent recommendations."""
    low = compute_threat_score({"confidence": 0.1})
    high = compute_threat_score({
        "confidence": 1.0, "zone_severity": 1.0, "boundary_crossing": 1.0,
        "loitering": 1.0, "night": 1.0, "behavior_anomaly": 1.0,
    })
    assert "IMMEDIATE" in high.recommended_action or "Verify" in high.recommended_action
    assert "monitoring" in low.recommended_action.lower() or "Monitor" in low.recommended_action
