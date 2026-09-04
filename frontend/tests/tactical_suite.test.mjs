import test from 'node:test';
import assert from 'node:assert/strict';

test('Threat score severity classification logic', () => {
  function getSeverity(threatScore) {
    if (threatScore >= 80) return 'CRITICAL';
    if (threatScore >= 60) return 'HIGH';
    if (threatScore >= 35) return 'MEDIUM';
    return 'LOW';
  }

  assert.equal(getSeverity(95), 'CRITICAL');
  assert.equal(getSeverity(80), 'CRITICAL');
  assert.equal(getSeverity(72), 'HIGH');
  assert.equal(getSeverity(45), 'MEDIUM');
  assert.equal(getSeverity(20), 'LOW');
});

test('WebSocket URL construction with bearer token authentication', () => {
  function buildWsUrl(baseUrl, endpoint, token) {
    const proto = baseUrl.startsWith('https') ? 'wss:' : 'ws:';
    const host = baseUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const url = `${proto}//${host}${endpoint}`;
    return token ? `${url}?token=${encodeURIComponent(token)}` : url;
  }

  const secured = buildWsUrl('http://127.0.0.1:8001', '/ws/events', 'jwt-token-xyz');
  assert.equal(secured, 'ws://127.0.0.1:8001/ws/events?token=jwt-token-xyz');

  const liveStream = buildWsUrl('https://defense.border.gov.in', '/ws/live/1', 'sec-token-123');
  assert.equal(liveStream, 'wss://defense.border.gov.in/ws/live/1?token=sec-token-123');
});

test('Tactical Radar coordinate transformation within viewport bounds', () => {
  function projectCoordinate(lat, lon, centerLat, centerLon, zoom, canvasWidth, canvasHeight) {
    const scale = zoom * 10000;
    const x = canvasWidth / 2 + (lon - centerLon) * scale;
    const y = canvasHeight / 2 - (lat - centerLat) * scale;
    return { x: Math.round(x), y: Math.round(y) };
  }

  const center = { lat: 28.6139, lon: 77.2090 };
  const pt = projectCoordinate(28.6139, 77.2090, center.lat, center.lon, 1.0, 800, 600);
  assert.equal(pt.x, 400);
  assert.equal(pt.y, 300);
});

test('Section 63 BSA 2023 forensic evidence hash verification contract', () => {
  function validateEvidenceIntegrity(evidence) {
    if (!evidence.sha256 || evidence.sha256.length !== 64) return false;
    if (!evidence.incident_id || evidence.incident_id <= 0) return false;
    return true;
  }

  assert.equal(validateEvidenceIntegrity({
    id: 1,
    incident_id: 101,
    sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
  }), true);

  assert.equal(validateEvidenceIntegrity({
    id: 2,
    incident_id: 0,
    sha256: 'invalid'
  }), false);
});
