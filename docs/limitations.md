# Limitations

## Honest Limitations

This is a prototype for SIH 2026. The following limitations are documented honestly:

### Perception Layer
- **Motion detection only (default)**: The base install uses background subtraction for detection. This detects moving blobs, not semantic objects. It cannot distinguish persons from vehicles from animals.
- **No deep learning models shipped**: Model weights are not included. YOLO/ONNX detectors can be plugged in but require separate download.
- **No face recognition**: Face detection shows bounding boxes only. No face database, no identity matching.
- **No ANPR**: No number plate recognition is implemented. Only the adapter interface exists.

### Tracking
- **IoU-based**: Simple overlap tracking. Does not handle occlusion well.
- **Single camera**: Tracking is per-camera. Cross-camera identity is not tracked.

### Scoring
- **Rule-based**: The scoring engine uses weighted signal fusion, not deep learning.
- **Configurable but not adaptive**: Weights are fixed unless manually changed.
- **No training data**: No ML model is trained on border surveillance data.

### Evidence
- **Manifest only**: Evidence is JSON manifests with SHA-256 hashes.
- **No video clips**: Video clip capture is not implemented.
- **No blockchain**: Hash chain is in-database, not a distributed ledger.

### Infrastructure
- **No TLS**: Development server only. Production requires reverse proxy.
- **No rate limiting**: Not implemented in demo mode.
- **No horizontal scaling demo**: Architecture supports it, but not demonstrated.
- **No real CCTV integration**: Demo uses synthetic data.

### Data
- **Demo data only**: All coordinates, camera names, and scenarios are synthetic.
- **No real border data**: No actual SSB operational data is used.
- **No AI-generated fake images**: Demo uses programmatic test data.

### Frontend
- **No map library**: Map placeholder exists but Leaflet/MapLibre not integrated.
- **No real video streaming**: Camera views show status, not live video.
- **No responsive mobile**: Optimized for desktop command center displays.

## What Would Be Needed for Production
1. Real object detection models (YOLOv8, etc.)
2. RTSP stream integration
3. GPU inference pipeline
4. PostgreSQL with proper indexing
5. Redis event bus
6. TLS/reverse proxy
7. Rate limiting
8. Real camera ONVIF integration
9. Map library integration
10. Video clip evidence capture
