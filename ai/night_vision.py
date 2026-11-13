"""
Adaptive Low-Light & Night Vision Enhancement Engine
Enables robust facial detection and recognition in night-time, poorly lit,
or shadowed campus entrance environments using CLAHE, Adaptive Gamma Correction,
and edge-preserving bilateral denoising.
"""

import cv2
import numpy as np

class NightVisionEnhancer:
    """Enhances low-light and night-time camera frames for deep face recognition."""

    def __init__(self, clahe_clip_limit: float = 3.0, clahe_tile_grid_size: tuple = (8, 8)):
        self.clahe = cv2.createCLAHE(clipLimit=clahe_clip_limit, tileGridSize=clahe_tile_grid_size)

    def estimate_ambient_brightness(self, frame_bgr: np.ndarray) -> float:
        """Calculate mean luminance (0.0 to 255.0) of the frame."""
        if frame_bgr is None or frame_bgr.size == 0:
            return 0.0
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def is_low_light(self, frame_bgr: np.ndarray, threshold: float = 70.0) -> bool:
        """Check if frame lighting is too low for standard facial detection."""
        return self.estimate_ambient_brightness(frame_bgr) < threshold

    def enhance(self, frame_bgr: np.ndarray, force_night_vision: bool = False) -> tuple:
        """
        Apply adaptive night vision enhancement to the frame.
        Returns:
            enhanced_bgr (np.ndarray): Illumination-normalized frame for face detection & recognition.
            was_enhanced (bool): True if enhancement was applied.
            brightness (float): Ambient brightness level (0 - 255).
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return frame_bgr, False, 0.0

        brightness = self.estimate_ambient_brightness(frame_bgr)

        # Trigger if forced or if ambient light is below threshold (70/255)
        if not force_night_vision and brightness >= 75.0:
            return frame_bgr, False, round(brightness, 1)

        # Step 1: Convert to LAB color space (separate luminance from color chrominance)
        lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Step 2: Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) on L-channel
        l_clahe = self.clahe.apply(l_channel)

        # Step 3: Adaptive Gamma Correction based on measured ambient brightness
        # For darker images (e.g. brightness 20-40), use smaller gamma (0.45-0.6) to boost shadows
        gamma = max(0.40, min(0.85, np.log(max(10.0, brightness) / 255.0) / np.log(0.45)))
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
        l_boosted = cv2.LUT(l_clahe, table)

        # Step 4: Re-merge LAB channels and convert back to BGR
        enhanced_lab = cv2.merge((l_boosted, a_channel, b_channel))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # Step 5: Fast edge-preserving filter to suppress low-light sensor grain
        enhanced_bgr = cv2.bilateralFilter(enhanced_bgr, d=5, sigmaColor=35, sigmaSpace=35)

        return enhanced_bgr, True, round(brightness, 1)

    def generate_night_vision_hud_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Creates a tactical night-vision green-phosphor visual overlay for UI display
        resembling institutional security night-vision surveillance monitors.
        """
        enhanced_bgr, _, _ = self.enhance(frame_bgr, force_night_vision=True)
        gray = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2GRAY)

        # Map grayscale to night-vision green phosphor palette (B=20..80, G=120..255, R=20..80)
        h, w = gray.shape
        nv_frame = np.zeros((h, w, 3), dtype=np.uint8)
        nv_frame[:, :, 0] = np.clip(gray * 0.25, 0, 80).astype(np.uint8)   # Low blue
        nv_frame[:, :, 1] = np.clip(gray * 1.15 + 25, 0, 255).astype(np.uint8) # High green
        nv_frame[:, :, 2] = np.clip(gray * 0.30, 0, 90).astype(np.uint8)   # Low red

        return nv_frame
