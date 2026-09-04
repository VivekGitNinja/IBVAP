"""
Night-Time Image Enhancement Module
====================================

Enhances low-light images for better detection accuracy.

Pipeline:
1. Check if frame needs enhancement (brightness analysis)
2. Apply Zero-DCE++ if available (4KB ONNX model, real-time on CPU)
3. Fallback to CLAHE + gamma correction
4. Return enhanced frame + metadata

Zero-DCE++:
- Paper: "Zero-Reference Deep Curve Estimation for Low-Light Image Enhancement" (CVPR 2021)
- Model: ~4KB ONNX, runs in <5ms on CPU
- Source: https://github.com/Li-Chongyi/Zero-DCE

CLAHE fallback:
- OpenCV built-in, no dependencies
- Contrast Limited Adaptive Histogram Equalization
- Combined with gamma correction for natural look

Toggle:
- Set enhance_frame=True/False per camera
- Auto-detect night conditions based on brightness
"""

import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import cv2

logger = logging.getLogger(__name__)


@dataclass
class EnhancementResult:
    """Result of night enhancement processing."""
    enhanced_frame: np.ndarray   # Enhanced image
    was_enhanced: bool           # Whether enhancement was applied
    method: str                  # "zero_dce++", "clahe_gamma", "none"
    brightness_before: float     # Average brightness 0-255
    brightness_after: float      # Average brightness after enhancement
    processing_time_ms: float    # Processing time in milliseconds
    night_detected: bool         # Whether night conditions were detected


class NightEnhancer:
    """
    Night-time image enhancement with Zero-DCE++ and CLAHE fallback.
    
    Usage:
        enhancer = NightEnhancer()
        result = enhancer.enhance(frame)
        if result.was_enhanced:
            detections = detector.detect(result.enhanced_frame)
    """
    
    def __init__(
        self,
        auto_detect_night: bool = True,
        brightness_threshold: float = 60.0,
        force_enhance: bool = False,
    ):
        """
        Args:
            auto_detect_night: Automatically detect low-light conditions
            brightness_threshold: Average brightness below this triggers enhancement
            force_enhance: Always enhance, even in bright conditions
        """
        self._auto_detect = auto_detect_night
        self._brightness_threshold = brightness_threshold
        self._force_enhance = force_enhance
        self._zero_dce_model = None
        self._zero_dce_available = False
        
        self._init_zero_dce()
    
    def _init_zero_dce(self) -> None:
        """Try to load Zero-DCE++ ONNX model."""
        try:
            import onnxruntime as ort
            
            # Try common paths for Zero-DCE++ model
            import os
            model_paths = [
                "models/zero_dcepp.onnx",
                "edge/models/zero_dcepp.onnx",
                os.path.expanduser("~/.ibvap/models/zero_dcepp.onnx"),
            ]
            
            for path in model_paths:
                if os.path.exists(path):
                    self._zero_dce_model = ort.InferenceSession(path)
                    self._zero_dce_available = True
                    logger.info(f"NightEnhance: Zero-DCE++ loaded from {path}")
                    return
            
            logger.info("NightEnhance: Zero-DCE++ model not found, using CLAHE fallback")
            
        except ImportError:
            logger.info("NightEnhance: onnxruntime not available, using CLAHE fallback")
        except Exception as e:
            logger.warning(f"NightEnhance: Zero-DCE++ init failed ({e}), using CLAHE")
    
    def enhance(self, frame: np.ndarray) -> EnhancementResult:
        """
        Enhance a frame for better low-light detection.
        
        Args:
            frame: BGR image (H x W x 3)
            
        Returns:
            EnhancementResult with enhanced frame and metadata
        """
        start_time = time.time()
        
        # Measure brightness
        brightness = self._measure_brightness(frame)
        
        # Should we enhance?
        needs_enhancement = (
            self._force_enhance or
            (self._auto_detect and brightness < self._brightness_threshold)
        )
        
        if not needs_enhancement:
            return EnhancementResult(
                enhanced_frame=frame,
                was_enhanced=False,
                method="none",
                brightness_before=brightness,
                brightness_after=brightness,
                processing_time_ms=(time.time() - start_time) * 1000,
                night_detected=False,
            )
        
        # Apply enhancement
        if self._zero_dce_available:
            enhanced = self._apply_zero_dce(frame)
            method = "zero_dce++"
        else:
            enhanced = self._apply_clahe_gamma(frame)
            method = "clahe_gamma"
        
        brightness_after = self._measure_brightness(enhanced)
        elapsed_ms = (time.time() - start_time) * 1000
        
        return EnhancementResult(
            enhanced_frame=enhanced,
            was_enhanced=True,
            method=method,
            brightness_before=brightness,
            brightness_after=brightness_after,
            processing_time_ms=elapsed_ms,
            night_detected=True,
        )
    
    def _measure_brightness(self, frame: np.ndarray) -> float:
        """Measure average brightness of a frame (0-255)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))
    
    def _apply_zero_dce(self, frame: np.ndarray) -> np.ndarray:
        """Apply Zero-DCE++ enhancement."""
        try:
            import onnxruntime as ort
            
            # Preprocess: resize to 512x512, normalize to [0, 1]
            h, w = frame.shape[:2]
            resized = cv2.resize(frame, (512, 512))
            normalized = resized.astype(np.float32) / 255.0
            
            # NCHW format
            input_tensor = normalized.transpose(2, 0, 1)[np.newaxis, ...]
            
            # Run inference
            input_name = self._zero_dce_model.get_inputs()[0].name
            output = self._zero_dce_model.run(None, {input_name: input_tensor})[0]
            
            # Post-process: apply learned curves
            enhanced = np.clip(
                normalized + output[0].transpose(1, 2, 0) * 0.5,
                0, 1
            )
            
            # Resize back to original size
            enhanced_bgr = (enhanced * 255).astype(np.uint8)
            enhanced_bgr = cv2.resize(enhanced_bgr, (w, h))
            
            return enhanced_bgr
            
        except Exception as e:
            logger.warning(f"NightEnhance: Zero-DCE++ failed ({e}), falling back to CLAHE")
            return self._apply_clahe_gamma(frame)
    
    def _apply_clahe_gamma(self, frame: np.ndarray) -> np.ndarray:
        """Apply CLAHE + gamma correction enhancement."""
        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(
            clipLimit=3.0,
            tileGridSize=(8, 8)
        )
        enhanced_l = clahe.apply(l_channel)
        
        # Merge back
        enhanced_lab = cv2.merge([enhanced_l, a_channel, b_channel])
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        
        # Apply gamma correction (brighten dark areas)
        gamma = 1.5  # >1 brightens
        look_up_table = np.array([
            ((i / 255.0) ** (1.0 / gamma)) * 255
            for i in range(256)
        ]).astype("uint8")
        enhanced_bgr = cv2.LUT(enhanced_bgr, look_up_table)
        
        return enhanced_bgr
    
    def get_stats(self) -> Dict:
        """Get enhancer statistics."""
        return {
            "zero_dce_available": self._zero_dce_available,
            "auto_detect": self._auto_detect,
            "brightness_threshold": self._brightness_threshold,
            "force_enhance": self._force_enhance,
        }


# Module-level singleton
_night_enhancer: Optional[NightEnhancer] = None


def get_night_enhancer(**kwargs) -> NightEnhancer:
    """Get or create the singleton night enhancer."""
    global _night_enhancer
    if _night_enhancer is None:
        _night_enhancer = NightEnhancer(**kwargs)
    return _night_enhancer
