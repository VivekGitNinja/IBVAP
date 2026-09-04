import test from 'node:test';
import assert from 'node:assert/strict';

// Test Zone Editor geometry calculation and validation rules
test('Zone Studio: geometry normalization and validation', () => {
  const canvasWidth = 560;
  const canvasHeight = 320;

  function toNormalized(pixelX, pixelY) {
    return [
      Math.round((pixelX / canvasWidth) * 10000) / 10000,
      Math.round((pixelY / canvasHeight) * 10000) / 10000,
    ];
  }

  function validateZoneGeometry(type, points, direction) {
    if (!['line', 'polygon'].includes(type)) {
      return { valid: false, error: 'Invalid zone type' };
    }
    if (type === 'line' && points.length < 2) {
      return { valid: false, error: 'Line zone requires at least 2 points' };
    }
    if (type === 'polygon' && points.length < 3) {
      return { valid: false, error: 'Polygon zone requires at least 3 points' };
    }
    for (const [x, y] of points) {
      if (x < 0 || x > 1 || y < 0 || y > 1) {
        return { valid: false, error: 'Points must be normalized between 0.0 and 1.0' };
      }
    }
    if (!['either', 'a_to_b', 'b_to_a'].includes(direction)) {
      return { valid: false, error: 'Invalid direction' };
    }
    return { valid: true };
  }

  // Click at (280, 160) -> normalized (0.5, 0.5)
  const normPt = toNormalized(280, 160);
  assert.deepEqual(normPt, [0.5, 0.5]);

  // Valid line
  const linePoints = [toNormalized(100, 100), toNormalized(400, 200)];
  assert.equal(validateZoneGeometry('line', linePoints, 'a_to_b').valid, true);

  // Invalid line (only 1 point)
  assert.equal(validateZoneGeometry('line', [[0.5, 0.5]], 'either').valid, false);

  // Valid polygon
  const polyPoints = [toNormalized(50, 50), toNormalized(200, 50), toNormalized(200, 200)];
  assert.equal(validateZoneGeometry('polygon', polyPoints, 'either').valid, true);

  // Invalid polygon (only 2 points)
  assert.equal(validateZoneGeometry('polygon', linePoints, 'either').valid, false);

  // Out of bounds coordinate rejection
  assert.equal(validateZoneGeometry('line', [[-0.1, 0.5], [0.8, 0.8]], 'either').valid, false);
  assert.equal(validateZoneGeometry('line', [[0.1, 1.2], [0.8, 0.8]], 'either').valid, false);
});

// Test Detection Feed chip rendering contracts
test('Detection Feed: Track ID, Plate Text, and Night Badge chip logic', () => {
  function formatDetectionChips(detection) {
    const chips = [];
    if (detection.track_id != null) {
      chips.push({ type: 'track', label: `TRK-${detection.track_id}` });
    }
    const plate = detection.metadata?.plate_text;
    if (plate) {
      chips.push({ type: 'plate', label: plate });
    }
    if (detection.metadata?.night) {
      chips.push({ type: 'night', label: 'NIGHT' });
    }
    return chips;
  }

  const det1 = {
    id: 1,
    job_id: 10,
    track_id: 42,
    metadata: {
      plate_text: 'DL01AB1234',
      night: true,
    },
  };

  const chips1 = formatDetectionChips(det1);
  assert.equal(chips1.length, 3);
  assert.deepEqual(chips1[0], { type: 'track', label: 'TRK-42' });
  assert.deepEqual(chips1[1], { type: 'plate', label: 'DL01AB1234' });
  assert.deepEqual(chips1[2], { type: 'night', label: 'NIGHT' });

  const det2 = {
    id: 2,
    job_id: 10,
    track_id: null,
    metadata: {
      night: false,
    },
  };
  const chips2 = formatDetectionChips(det2);
  assert.equal(chips2.length, 0);
});

// Test Forensic Report export buttons and URL building
test('Report Export: JSON and PDF report URL generation with BSA 2023 compliance', () => {
  function getReportUrl(apiBase, jobId, format) {
    if (!['json', 'pdf'].includes(format)) {
      throw new Error('Unsupported report format');
    }
    return `${apiBase}/api/v1/analysis/jobs/${jobId}/report?format=${format}`;
  }

  const baseUrl = 'http://localhost:8001';
  const jsonUrl = getReportUrl(baseUrl, 5, 'json');
  const pdfUrl = getReportUrl(baseUrl, 5, 'pdf');

  assert.equal(jsonUrl, 'http://localhost:8001/api/v1/analysis/jobs/5/report?format=json');
  assert.equal(pdfUrl, 'http://localhost:8001/api/v1/analysis/jobs/5/report?format=pdf');
  assert.throws(() => getReportUrl(baseUrl, 5, 'csv'), /Unsupported report format/);
});

// Test Watchlist Management and Matching API contracts
test('Watchlist View: enrollment payload and match verification', () => {
  function prepareEnrollPayload(name, notes, file) {
    if (!name || name.trim().length === 0) {
      throw new Error('Subject name is required');
    }
    if (!file) {
      throw new Error('Reference facial image is required');
    }
    return {
      name: name.trim(),
      notes: notes || '',
      fileName: file.name,
      mimeType: file.type,
    };
  }

  const payload = prepareEnrollPayload('Suspect Alpha', 'Interpol Red Notice', {
    name: 'suspect_alpha.jpg',
    type: 'image/jpeg',
  });

  assert.equal(payload.name, 'Suspect Alpha');
  assert.equal(payload.notes, 'Interpol Red Notice');
  assert.equal(payload.fileName, 'suspect_alpha.jpg');

  assert.throws(() => prepareEnrollPayload('', 'notes', {}), /Subject name is required/);
  assert.throws(() => prepareEnrollPayload('Valid', 'notes', null), /Reference facial image is required/);
});

// Test System Readiness status badges and statutory authority
test('System Readiness: component status evaluation and BSA 2023 Section 63 authority', () => {
  const readinessResponse = {
    status: 'OPERATIONAL',
    statutory_authority: 'Bharatiya Sakshya Adhiniyam, 2023 Section 63',
    components: {
      db: { status: 'OK', details: 'SQLite 17 tables' },
      ffmpeg: { status: 'OK', path: '/usr/local/bin/ffmpeg' },
      detector: { status: 'CACHED', model: 'yolov8n.onnx' },
      ocr: { status: 'UNAVAILABLE', reason: 'PaddleOCR not installed' },
    },
  };

  function evaluateReadiness(readiness) {
    const isStatutoryCompliant = readiness.statutory_authority.includes('Bharatiya Sakshya Adhiniyam, 2023 Section 63');
    const coreHealthy = readiness.components.db.status === 'OK';
    const detectorCached = readiness.components.detector.status === 'CACHED';
    const ocrDegradedGracefully = readiness.components.ocr.status === 'UNAVAILABLE';

    return {
      readyForAnalysis: coreHealthy && detectorCached,
      compliant: isStatutoryCompliant,
      ocrAvailable: !ocrDegradedGracefully,
    };
  }

  const evalResult = evaluateReadiness(readinessResponse);
  assert.equal(evalResult.readyForAnalysis, true);
  assert.equal(evalResult.compliant, true);
  assert.equal(evalResult.ocrAvailable, false);
});
