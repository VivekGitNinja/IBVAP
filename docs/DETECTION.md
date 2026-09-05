# IBVAP Detection Architecture & Confidence Integrity
## Technical Reference — SIH 2026 / SSB MHA (PS-26187)

---

## 1. Detection Hierarchy

IBVAP employs a hierarchical detection strategy designed for resilient edge operations along remote borders:

1. **Primary Edge Model (YOLO26n / YOLO11n):** Direct neural network inference using native ONNX/PyTorch models. Native model confidence is extracted directly from softmax/sigmoid outputs.
2. **Optical Character Recognition (ANPR):** Multi-tier OCR engine (PaddleOCR / EasyOCR / Haar fallback) executing on vehicle crops.
3. **Facial Intelligence (FRS):** OpenCV YuNet detector paired with SFace 128-dimensional deep feature embeddings.
4. **Heuristic Motion Fallback:** OpenCV MOG2 background subtractor with connected components analysis.

---

## 2. Motion-Fallback Confidence Synthesis

When GPU/NPU neural acceleration is unavailable or model weights are unmounted, the platform falls back to CPU background subtraction:

`confidence = min(0.95, max(0.55, area/2000)) — synthesized for the heuristic fallback; YOLO path uses native model confidence; false-positive control is via zone thresholds, cooldown, and persistence gating.`

### False-Positive Control & Noise Gating
- **Contour Area Gating (`motion_min_area = 600`):** Rejects sensor noise, thermal shimmer, foliage vibration, and compression artifacts smaller than 600 pixels.
- **Temporal Persistence Gating (`motion_persistence_frames = 3`):** Transient single-frame or two-frame lighting fluctuations are suppressed. An object must persist across >= 3 consecutive frames with centroid continuity before a `Detection` event is emitted.
- **Confidence Floor (`motion_conf_floor = 0.55`):** Lower bound on synthesized confidence to distinguish genuine moving bodies from ambiguous background shifts.
- **Incident Escalation Control:** Incident triggers require zone boundary intersection or dwell time satisfaction with a configured severity threshold, ensuring zero false alarms on static scenes.

---

*Document maintained by the IBVAP CV Engineering Team — SIH 2026*
