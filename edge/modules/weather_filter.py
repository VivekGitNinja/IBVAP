"""
Adverse Weather De-Hazing & Fog Stripping Module
=================================================
Pierces through dense mountain fog, heavy haze, monsoon mist, and sand/dust storms
common along border frontiers (e.g. Eastern borders, Himalayas, Rann of Kutch).

Technique:
- Dark Channel Prior (DCP) atmospheric transmission estimation
- CLAHE (Contrast Limited Adaptive Histogram Equalization) in LAB color space
- Adaptive Fog Density Metric determination
"""

from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np


class AdverseWeatherFilter:
    """Real-time optical de-hazing and fog contrast restoration engine."""

    def __init__(self, patch_size: int = 7, omega: float = 0.85, t_min: float = 0.15):
        self.patch_size = patch_size
        self.omega = omega
        self.t_min = t_min
        self.clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

    def compute_dark_channel(self, image: np.ndarray) -> np.ndarray:
        """Compute the dark channel of an RGB image using min pooling."""
        min_channel = np.min(image, axis=2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (self.patch_size, self.patch_size))
        dark_channel = cv2.erode(min_channel, kernel)
        return dark_channel

    def estimate_atmospheric_light(self, image: np.ndarray, dark_channel: np.ndarray) -> np.ndarray:
        """Estimate the atmospheric light vector A from the brightest dark channel pixels."""
        h, w = dark_channel.shape
        num_pixels = h * w
        num_brightest = max(int(num_pixels * 0.001), 10)

        flat_dark = dark_channel.reshape(-1)
        flat_img = image.reshape(-1, 3)

        indices = np.argpartition(flat_dark, -num_brightest)[-num_brightest:]
        brightest_pixels = flat_img[indices]

        # Atmospheric light is the max intensity among these candidates
        atmospheric_light = np.max(brightest_pixels, axis=0)
        return atmospheric_light.astype(np.float32)

    def dehaze(self, frame: np.ndarray) -> np.ndarray:
        """Perform Dark Channel Prior atmospheric transmission de-fogging."""
        img = frame.astype(np.float32) / 255.0
        dark = self.compute_dark_channel(img)
        A = self.estimate_atmospheric_light(img, dark)

        # Transmission map estimation
        norm_img = img / (A + 1e-6)
        norm_dark = self.compute_dark_channel(norm_img)
        transmission = 1.0 - (self.omega * norm_dark)
        transmission = np.clip(transmission, self.t_min, 1.0)

        # Recover scene radiance: J = (I - A) / max(t, t0) + A
        t_3d = np.repeat(transmission[:, :, np.newaxis], 3, axis=2)
        radiance = (img - A) / t_3d + A
        radiance = np.clip(radiance * 255.0, 0, 255).astype(np.uint8)

        # Enhance local contrast using CLAHE on L-channel
        lab = cv2.cvtColor(radiance, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_enhanced = self.clahe.apply(l)
        enhanced_lab = cv2.merge((l_enhanced, a, b))
        output = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        return output

    def process(self, frame: np.ndarray, mode: str = "auto") -> Tuple[np.ndarray, Dict[str, Any]]:
        """Assess fog density and apply optical de-hazing if required.

        Args:
            frame: Input BGR frame.
            mode: "auto" (detects fog before processing), "force" (always dehaze), "off".

        Returns:
            (enhanced_frame, telemetry_dict)
        """
        if mode == "off":
            return frame, {"applied": False, "fog_density": 0.0, "mode": "off"}

        # Measure fog index via mean value of dark channel on downscaled frame
        small = cv2.resize(frame, (320, 180))
        dark_small = self.compute_dark_channel(small.astype(np.float32) / 255.0)
        fog_density = float(np.mean(dark_small))

        should_apply = mode == "force" or (mode == "auto" and fog_density > 0.25)

        if should_apply:
            result = self.dehaze(frame)
            return result, {
                "applied": True,
                "fog_density": round(fog_density, 3),
                "method": "dark_channel_prior + clahe",
                "mode": mode,
            }

        return frame, {
            "applied": False,
            "fog_density": round(fog_density, 3),
            "method": "none (clear atmospheric conditions)",
            "mode": mode,
        }


# Singleton instance
weather_filter = AdverseWeatherFilter()
