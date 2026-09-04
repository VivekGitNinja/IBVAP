# Model Licenses

## YOLO11n (Primary Detection Model)

- **Model**: YOLO11n (nano)
- **Source**: [Ultralytics](https://github.com/ultralytics/ultralytics)
- **License**: AGPL-3.0 (academic/non-commercial use) / Enterprise (commercial)
- **Size**: 10.2 MB (ONNX), 5.4 MB (PyTorch)
- **Parameters**: 2.6M
- **Input**: 640x640 RGB image
- **Output**: 80 COCO classes
- **CPU Performance**: ~56ms per frame (ONNX Runtime)
- **Purpose**: Real-time object detection for border surveillance

### Citation
```bibtex
@software{yolo11_ultralytics,
  author = {Glenn Jocher and Jing Qiu},
  title = {Ultralytics YOLO11},
  version = {11.0.0},
  year = {2024},
  url = {https://github.com/ultralytics/ultralytics},
  orcid = {0000-0001-5950-6979, 0000-0003-3783-7069},
  license = {AGPL-3.0}
}
```

### Usage Notes
- For SIH 2026 prototype: AGPL-3.0 allows academic use
- For commercial deployment: Ultralytics Enterprise license required
- Model weights downloaded automatically on first use
- No manual download required

## Fallback: Motion Detection

- **Type**: Background subtraction (MOG2)
- **License**: OpenCV (Apache 2.0)
- **Purpose**: CPU fallback when YOLO model unavailable
- **Note**: Detects motion blobs, NOT semantic objects — honestly labeled

## Future Models (Not Yet Integrated)

- **YOLO26** (Sept 2025): 43% faster CPU, better small-object accuracy
- **YOLOv8-SEG**: Instance segmentation support
- **Face Detection**: Not implemented (adapter interface exists)
- **ANPR/OCR**: Not implemented (adapter interface exists)

## Model Download

Models are downloaded automatically by Ultralytics on first use.
No manual download required for the prototype.

For manual download:
```bash
# YOLO11n PyTorch
wget https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt

# Export to ONNX
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt').export(format='onnx')"
```
