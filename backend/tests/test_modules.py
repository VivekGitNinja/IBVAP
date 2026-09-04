"""Tests for edge modules — face recognition, ByteTrack, motion, correlation, ANPR."""

import numpy as np
import pytest
from datetime import datetime, timedelta


# ── FIX 1: Face Recognition ──────────────────────────────────────────

class TestFaceRecognition:
    """Tests for face_recognition module."""

    def test_import(self):
        """Module imports without error."""
        from edge.modules.face_recognition import get_face_engine, FaceRecognitionModule, FaceDetectorAdapter
        assert FaceDetectorAdapter is not None
        assert FaceRecognitionModule is not None

    def test_detector_adapter_has_is_available(self):
        """FaceDetectorAdapter exposes is_available property."""
        from edge.modules.face_recognition import FaceDetectorAdapter
        adapter = FaceDetectorAdapter()
        assert hasattr(adapter, 'is_available')
        assert isinstance(adapter.is_available, bool)

    def test_detector_adapter_method(self):
        """FaceDetectorAdapter has a valid method string."""
        from edge.modules.face_recognition import FaceDetectorAdapter
        adapter = FaceDetectorAdapter()
        assert adapter.method in ('insightface', 'insightface_sc', 'opencv_dnn', 'haar_cascade', 'none')

    def test_module_has_fallback_mode(self):
        """FaceRecognitionModule has _fallback_mode attribute."""
        from edge.modules.face_recognition import FaceRecognitionModule
        module = FaceRecognitionModule()
        assert hasattr(module, '_fallback_mode')
        assert isinstance(module._fallback_mode, bool)

    def test_process_frame_returns_list(self):
        """process_frame returns List[FaceMatch]."""
        from edge.modules.face_recognition import get_face_engine
        engine = get_face_engine()
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        results = engine.process_frame(frame, frame_id=1, camera_id='test')
        assert isinstance(results, list)

    def test_singleton(self):
        """get_face_engine returns same instance."""
        from edge.modules.face_recognition import get_face_engine
        e1 = get_face_engine()
        e2 = get_face_engine()
        assert e1 is e2


# ── FIX 2: ByteTrack ─────────────────────────────────────────────────

class TestByteTrack:
    """Tests for ByteTracker."""

    def test_import_from_package(self):
        """ByteTracker importable from edge.tracking."""
        from edge.tracking import ByteTracker
        assert ByteTracker is not None

    def test_import_from_module(self):
        """ByteTracker importable from edge.tracking.bytetrack."""
        from edge.tracking.bytetrack import ByteTracker
        assert ByteTracker is not None

    def test_init(self):
        """ByteTracker initializes without error."""
        from edge.tracking import ByteTracker
        tracker = ByteTracker()
        assert hasattr(tracker, 'update')
        assert hasattr(tracker, 'get_stats')

    def test_track_persists_ids(self):
        """Track IDs persist across frames."""
        from edge.tracking import ByteTracker
        tracker = ByteTracker()
        all_ids = set()
        for frame_id in range(20):
            x = 100 + frame_id * 20
            detections = [{'bbox': [x, 200, x+80, 260], 'class_name': 'car', 'confidence': 0.9}]
            tracks = tracker.update(detections)
            for t in tracks:
                all_ids.add(t['track_id'])
        # Should have 1 persistent track, not 20 different IDs
        assert len(all_ids) <= 3, f"Too many unique IDs: {all_ids}"

    def test_get_stats(self):
        """get_stats returns dict with expected keys."""
        from edge.tracking import ByteTracker
        tracker = ByteTracker()
        stats = tracker.get_stats()
        assert isinstance(stats, dict)
        assert 'total_tracks' in stats
        assert 'active_tracks' in stats


# ── FIX 3: Motion Detector ───────────────────────────────────────────

class TestMotionDetector:
    """Tests for MotionDetector."""

    def test_import(self):
        """Module imports without error."""
        from edge.detection.motion import MotionDetector
        assert MotionDetector is not None

    def test_is_available(self):
        """MotionDetector.is_available returns True."""
        from edge.detection.motion import MotionDetector
        md = MotionDetector()
        assert md.is_available is True

    def test_name(self):
        """MotionDetector has a name property."""
        from edge.detection.motion import MotionDetector
        md = MotionDetector()
        assert 'MotionDetector' in md.name

    def test_detect_returns_list(self):
        """detect returns list of Detection objects."""
        from edge.detection.motion import MotionDetector
        md = MotionDetector()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:200, 100:200] = 255
        detections = md.detect(frame)
        assert isinstance(detections, list)

    def test_factory_creates_motion(self):
        """Factory can create motion detector."""
        from edge.detection.factory import create_detector
        md = create_detector('motion')
        assert md.is_available
        assert 'MotionDetector' in md.name


# ── FIX 4: Correlation Engine ────────────────────────────────────────

class TestCorrelation:
    """Tests for correlation engine."""

    def test_should_correlate_within_window(self):
        """Events within time window are correlated."""
        from backend.app.services.correlation import should_correlate
        t1 = datetime.utcnow()
        t2 = t1 + timedelta(seconds=60)
        assert should_correlate(t1, t2) is True

    def test_should_correlate_outside_window(self):
        """Events outside time window are not correlated."""
        from backend.app.services.correlation import should_correlate
        t1 = datetime.utcnow()
        t2 = t1 + timedelta(seconds=600)
        assert should_correlate(t1, t2) is False

    def test_compute_distance_meters(self):
        """Haversine distance computes correctly (no NameError)."""
        from backend.app.services.correlation import compute_distance_meters
        dist = compute_distance_meters(28.6139, 77.2090, 28.6145, 77.2100)
        assert isinstance(dist, float)
        assert dist > 0
        assert dist < 1000  # Should be ~118m

    def test_cameras_spatially_correlated(self):
        """Nearby cameras are spatially correlated."""
        from backend.app.services.correlation import cameras_spatially_correlated
        assert cameras_spatially_correlated(28.6139, 77.2090, 28.6145, 77.2100) is True

    def test_build_correlation_key(self):
        """Correlation key contains expected separators."""
        from backend.app.services.correlation import build_correlation_key
        key = build_correlation_key('intrusion', 'person', 'zone_a')
        assert ':' in key
        assert 'intrusion' in key


# ── FIX 5: ANPR ──────────────────────────────────────────────────────

class TestANPR:
    """Tests for ANPR pipeline."""

    def test_import(self):
        """Module imports without error."""
        from edge.detection.anpr import ANPRPipeline
        assert ANPRPipeline is not None

    def test_pipeline_always_available(self):
        """ANPR pipeline is always available (has fallback)."""
        from edge.detection.anpr import ANPRPipeline
        anpr = ANPRPipeline()
        assert anpr.is_available is True

    def test_process_frame_no_vehicles(self):
        """process_frame with no vehicles returns empty list."""
        from edge.detection.anpr import ANPRPipeline
        anpr = ANPRPipeline()
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        results = anpr.process_frame(frame, [])
        assert isinstance(results, list)
        assert len(results) == 0

    def test_process_frame_with_vehicle(self):
        """process_frame with vehicle returns PlateResult list."""
        from edge.detection.anpr import ANPRPipeline
        anpr = ANPRPipeline()
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        vehicles = [{'bbox': [100, 100, 300, 250], 'class_name': 'car', 'confidence': 0.9}]
        results = anpr.process_frame(frame, vehicles)
        assert isinstance(results, list)
        # Results may be empty if no plate detected, which is correct

    def test_get_stats(self):
        """get_stats returns expected keys."""
        from edge.detection.anpr import ANPRPipeline
        anpr = ANPRPipeline()
        stats = anpr.get_stats()
        assert 'frames_processed' in stats
        assert 'plates_detected' in stats


# ── Scoring Engine ────────────────────────────────────────────────────

class TestScoring:
    """Tests for threat scoring engine."""

    def test_low_score(self):
        """Low signals produce LOW severity."""
        from backend.app.services.scoring import compute_threat_score
        result = compute_threat_score({'confidence': 0.3})
        assert result.severity == 'LOW'
        assert result.score < 40

    def test_high_score(self):
        """High signals produce HIGH/CRITICAL severity."""
        from backend.app.services.scoring import compute_threat_score
        signals = {
            'confidence': 0.9, 'zone_severity': 1.0, 'boundary_crossing': 1.0,
            'loitering': 0.9, 'night': 0.8, 'behavior_anomaly': 0.8,
        }
        result = compute_threat_score(signals)
        assert result.score >= 65
        assert result.severity in ('HIGH', 'CRITICAL')

    def test_reasons_explain_score(self):
        """Each reason corresponds to a signal contribution."""
        from backend.app.services.scoring import compute_threat_score
        signals = {'confidence': 0.8, 'zone_severity': 0.9}
        result = compute_threat_score(signals)
        assert len(result.reasons) >= 2
        for reason in result.reasons:
            assert '+(' in reason or '+' in reason


# ── Evidence Engine ───────────────────────────────────────────────────

class TestEvidence:
    """Tests for evidence sealing and verification."""

    def test_seal_and_verify(self):
        """Evidence can be sealed and verified."""
        from backend.app.services.evidence import seal_evidence, verify_manifest
        path, hash_val, data = seal_evidence('TEST-001', {'test': True})
        assert verify_manifest(path, hash_val) is True

    def test_tampered_evidence_fails(self):
        """Tampered evidence fails verification."""
        from backend.app.services.evidence import seal_evidence, verify_manifest
        path, hash_val, data = seal_evidence('TEST-002', {'test': True})
        assert verify_manifest(path, 'wrong_hash') is False

    def test_chain_verification(self):
        """Evidence chain verification works."""
        from backend.app.services.evidence import verify_evidence_chain
        records = [
            {'sha256': 'abc', 'previous_hash': '', 'created_at': '2026-01-01T00:00:00'},
            {'sha256': 'def', 'previous_hash': 'abc', 'created_at': '2026-01-01T00:01:00'},
        ]
        result = verify_evidence_chain(records)
        assert result['chain_valid'] is True
        assert result['records_count'] == 2
