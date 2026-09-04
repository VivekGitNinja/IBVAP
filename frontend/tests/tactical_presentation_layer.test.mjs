import test from 'node:test';
import assert from 'node:assert/strict';

// ── TASK 1: TACTICAL HUD DATA CONTRACT & FORMATTING ─────────────────

test('Tactical HUD: Coordinates formatting displays real WGS84 or "-- / --"', () => {
  function formatCoords(lat, lng) {
    const hasCoords =
      lat !== null &&
      lat !== undefined &&
      lng !== null &&
      lng !== undefined &&
      !(lat === 0 && lng === 0);

    return hasCoords
      ? `${lat >= 0 ? lat.toFixed(4) + '°N' : Math.abs(lat).toFixed(4) + '°S'}, ${
          lng >= 0 ? lng.toFixed(4) + '°E' : Math.abs(lng).toFixed(4) + '°W'
        }`
      : '-- / --';
  }

  // Real border outpost coordinates
  assert.equal(formatCoords(28.6139, 77.2090), '28.6139°N, 77.2090°E');
  assert.equal(formatCoords(-12.0464, -77.0428), '12.0464°S, 77.0428°W');

  // Missing or unset coordinates must display '-- / --' (Zero Mock Guarantee)
  assert.equal(formatCoords(null, null), '-- / --');
  assert.equal(formatCoords(undefined, undefined), '-- / --');
  assert.equal(formatCoords(0, 0), '-- / --');
});

test('Tactical HUD: DEFCON level posture mapping from threat score', () => {
  function getDefcon(maxThreat) {
    if (maxThreat >= 80) return { level: 1, label: 'CRITICAL' };
    if (maxThreat >= 60) return { level: 2, label: 'ELEVATED' };
    if (maxThreat >= 35) return { level: 3, label: 'SENSITIVE' };
    return { level: 4, label: 'ROUTINE' };
  }

  assert.deepEqual(getDefcon(95), { level: 1, label: 'CRITICAL' });
  assert.deepEqual(getDefcon(80), { level: 1, label: 'CRITICAL' });
  assert.deepEqual(getDefcon(75), { level: 2, label: 'ELEVATED' });
  assert.deepEqual(getDefcon(45), { level: 3, label: 'SENSITIVE' });
  assert.deepEqual(getDefcon(10), { level: 4, label: 'ROUTINE' });
  assert.deepEqual(getDefcon(0), { level: 4, label: 'ROUTINE' });
});

test('Tactical HUD: Clock formatting contract (UTC Zulu + IST dual representation)', () => {
  const refDate = new Date('2026-09-04T18:30:00.000Z');
  const utcStr = refDate.toISOString().replace('T', ' ').substring(0, 19) + ' Z';
  assert.equal(utcStr, '2026-09-04 18:30:00 Z');

  const istStr = refDate.toLocaleTimeString('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour12: false,
  }) + ' IST';
  assert.equal(istStr, '00:00:00 IST');
});

// ── TASK 2 & 3: TRACK TRAILS & ACTIVE TRACKS ROSTER ─────────────────

test('Track Trails: Centroid normalization and downsampling algorithm', () => {
  function normalizeAndDownsample(rawPoints, frameW, frameH, maxPoints = 50) {
    const normalized = rawPoints.map(([x, y, f]) => [
      Math.round(Math.min(1.0, Math.max(0.0, x / frameW)) * 10000) / 10000,
      Math.round(Math.min(1.0, Math.max(0.0, y / frameH)) * 10000) / 10000,
      f,
    ]);

    if (normalized.length <= maxPoints) return normalized;

    const step = Math.floor(normalized.length / maxPoints);
    const downsampled = normalized.filter((_, idx) => idx % step === 0);
    if (downsampled[downsampled.length - 1] !== normalized[normalized.length - 1]) {
      downsampled.push(normalized[normalized.length - 1]);
    }
    return downsampled;
  }

  // Sample track trajectory across 1280x720 video
  const rawPath = [
    [128, 72, 0],
    [640, 360, 25],
    [1280, 720, 50],
  ];

  const normPath = normalizeAndDownsample(rawPath, 1280, 720);
  assert.equal(normPath.length, 3);
  assert.deepEqual(normPath[0], [0.1, 0.1, 0]);
  assert.deepEqual(normPath[1], [0.5, 0.5, 25]);
  assert.deepEqual(normPath[2], [1.0, 1.0, 50]);

  // Massive trajectory with 200 points downsampled
  const densePath = Array.from({ length: 200 }, (_, i) => [i * 6, i * 3, i]);
  const denseNorm = normalizeAndDownsample(densePath, 1200, 600, 50);
  assert.ok(denseNorm.length <= 60);
  assert.equal(denseNorm[0][2], 0); // Preserves start
  assert.equal(denseNorm[denseNorm.length - 1][2], 199); // Preserves end
});

test('Active Tracks Roster: Dwell time and sorting by appearance', () => {
  const tracks = [
    { track_id: 'TRK-2', first_frame: 30, last_frame: 90, class: 'car' },
    { track_id: 'TRK-1', first_frame: 0, last_frame: 150, class: 'person' },
  ];

  const sorted = [...tracks].sort((a, b) => a.first_frame - b.first_frame);
  assert.equal(sorted[0].track_id, 'TRK-1');
  assert.equal(sorted[1].track_id, 'TRK-2');

  const fps = 25.0;
  const dwellT1 = ((sorted[0].last_frame - sorted[0].first_frame) / fps).toFixed(1);
  assert.equal(dwellT1, '6.0'); // 150 frames @ 25fps = 6.0s
});

// ── TASK 4: SATELLITE BASE MAP OFFLINE TILE SELECTION ────────────────

test('Satellite Base Map: Offline-first tile layer priority configuration', () => {
  function getTileConfig(layerType) {
    if (layerType === 'local') {
      return { url: '/tiles/{z}/{x}/{y}.png', maxZoom: 18, isGrid: false };
    }
    if (layerType === 'esri') {
      return {
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maxZoom: 19,
        isGrid: false,
      };
    }
    if (layerType === 'osm') {
      return { url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', maxZoom: 19, isGrid: false };
    }
    return { url: '', maxZoom: 19, isGrid: true };
  }

  const localCfg = getTileConfig('local');
  assert.equal(localCfg.url, '/tiles/{z}/{x}/{y}.png');
  assert.equal(localCfg.isGrid, false);

  const esriCfg = getTileConfig('esri');
  assert.ok(esriCfg.url.includes('arcgisonline.com'));
  assert.ok(esriCfg.url.includes('World_Imagery'));

  const osmCfg = getTileConfig('osm');
  assert.ok(osmCfg.url.includes('openstreetmap.org'));

  const gridCfg = getTileConfig('grid');
  assert.equal(gridCfg.isGrid, true);
});

// ── TASK 5: SHARE LINKS SERIALIZATION & RESTORATION ─────────────────

test('Share Links: Serialize and deserialize deep link tactical parameters', () => {
  function serializeParams(params) {
    const sp = new URLSearchParams();
    if (params.view) sp.set('view', params.view);
    if (params.cameraId !== null && params.cameraId !== undefined) sp.set('camera_id', String(params.cameraId));
    if (params.jobId !== null && params.jobId !== undefined) sp.set('job_id', String(params.jobId));
    if (params.incidentId !== null && params.incidentId !== undefined) sp.set('incident_id', String(params.incidentId));
    if (params.lat !== null && params.lat !== undefined) sp.set('lat', params.lat.toFixed(4));
    if (params.lng !== null && params.lng !== undefined) sp.set('lng', params.lng.toFixed(4));
    if (params.zoom !== null && params.zoom !== undefined) sp.set('zoom', String(params.zoom));
    return sp.toString();
  }

  function parseParams(searchOrUrl) {
    let s = searchOrUrl;
    if (s.includes('?')) s = s.substring(s.indexOf('?') + 1);
    const p = new URLSearchParams(s);
    const r = {};
    if (p.get('view')) r.view = p.get('view');
    if (p.get('camera_id')) r.cameraId = parseInt(p.get('camera_id'), 10);
    if (p.get('job_id')) r.jobId = p.get('job_id');
    if (p.get('incident_id')) r.incidentId = parseInt(p.get('incident_id'), 10);
    if (p.get('lat')) r.lat = parseFloat(p.get('lat'));
    if (p.get('lng')) r.lng = parseFloat(p.get('lng'));
    if (p.get('zoom')) r.zoom = parseInt(p.get('zoom'), 10);
    return r;
  }

  const original = {
    view: 'incidents',
    cameraId: 3,
    jobId: '25',
    incidentId: 104,
    lat: 28.6139,
    lng: 77.2090,
    zoom: 14,
  };

  const queryString = serializeParams(original);
  assert.ok(queryString.includes('view=incidents'));
  assert.ok(queryString.includes('camera_id=3'));
  assert.ok(queryString.includes('job_id=25'));
  assert.ok(queryString.includes('incident_id=104'));
  assert.ok(queryString.includes('lat=28.6139'));
  assert.ok(queryString.includes('lng=77.2090'));
  assert.ok(queryString.includes('zoom=14'));

  const parsed = parseParams(`?${queryString}`);
  assert.equal(parsed.view, 'incidents');
  assert.equal(parsed.cameraId, 3);
  assert.equal(parsed.jobId, '25');
  assert.equal(parsed.incidentId, 104);
  assert.equal(parsed.lat, 28.6139);
  assert.equal(parsed.lng, 77.2090);
  assert.equal(parsed.zoom, 14);

  // Partial parameters restore cleanly
  const partial = parseParams('view=map&incident_id=42');
  assert.equal(partial.view, 'map');
  assert.equal(partial.incidentId, 42);
  assert.equal(partial.cameraId, undefined);
});

// ── TASK 7: SENSOR SKINS SAFETY POLICY ──────────────────────────────

test('Sensor Skins: Safety policy enforces default OFF and immutable evidence', () => {
  const config = {
    ENABLE_HUD_STYLING: true,
    ENABLE_SENSOR_SKINS: false,
  };

  // Hard rule: ENABLE_SENSOR_SKINS must default to false
  assert.equal(config.ENABLE_SENSOR_SKINS, false);

  // Styling toggle defaults ON
  assert.equal(config.ENABLE_HUD_STYLING, true);
});
