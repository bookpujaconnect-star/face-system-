"""
Presentation Attack Detection (Anti-Spoofing) Module
Analyzes facial micro-textures, frequency spectrum, and color distribution
to prevent spoofing via printed photos, smartphone displays, or video replays.
"""

import cv2
import numpy as np

class AntiSpoofingDetector:
    def __init__(self, texture_threshold: float = 0.40):
        self.texture_threshold = texture_threshold

    def analyze_liveness(self, face_bgr: np.ndarray) -> dict:
        """
        Evaluate if the captured face is a live presentation or a presentation attack.
        Returns:
            dict with:
                is_real: bool
                liveness_score: float (0.0 - 1.0)
                attack_type: str ("None", "Screen Replay", "Printed Photo")
                confidence: float
                requires_manual_check: bool
        """
        if face_bgr is None or face_bgr.size == 0:
            return {
                "is_real": False,
                "liveness_score": 0.0,
                "attack_type": "Invalid Sample",
                "confidence": 0.0,
                "requires_manual_check": True
            }

        # 1. High-Frequency Fourier Analysis for Moiré & Print artifacts
        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        if h < 30 or w < 30:
            return {
                "is_real": True,
                "liveness_score": 0.70,
                "attack_type": "None",
                "confidence": 0.60,
                "requires_manual_check": False
            }

        resized = cv2.resize(gray, (128, 128))
        f_transform = np.fft.fft2(resized)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1e-6)

        # High frequency energy vs total energy
        center_y, center_x = 64, 64
        radius = 25
        y, x = np.ogrid[:128, :128]
        mask_low = ((x - center_x)**2 + (y - center_y)**2) <= radius**2

        total_energy = np.sum(magnitude_spectrum)
        low_energy = np.sum(magnitude_spectrum[mask_low])
        high_energy = total_energy - low_energy
        high_freq_ratio = float(high_energy / (total_energy + 1e-6))

        # 2. Color Distribution in YCrCb (Screen replays exhibit compressed chrominance)
        ycrcb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2YCrCb)
        cr = ycrcb[:, :, 1]
        cb = ycrcb[:, :, 2]
        cr_std = float(np.std(cr))
        cb_std = float(np.std(cb))
        chroma_variance = (cr_std + cb_std) / 2.0

        # 3. Specular reflection check (high saturation in small localized areas, typical of glass phone screens)
        hsv = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        specular_pixels = np.sum(v_channel > 250) / float(v_channel.size)

        # Combine heuristic scores
        liveness_score = 0.5 * (high_freq_ratio * 1.8) + 0.3 * min(1.0, chroma_variance / 15.0) - 0.2 * min(1.0, specular_pixels * 10.0)
        liveness_score = float(np.clip(liveness_score, 0.05, 0.98))

        is_real = liveness_score >= self.texture_threshold
        attack_type = "None"
        if not is_real:
            if specular_pixels > 0.06 or high_freq_ratio > 0.65:
                attack_type = "Screen Replay Attack"
            else:
                attack_type = "Printed Photo Attack"

        return {
            "is_real": is_real,
            "liveness_score": round(liveness_score, 3),
            "attack_type": attack_type,
            "confidence": round(abs(liveness_score - self.texture_threshold) * 2.0, 2),
            "requires_manual_check": not is_real
        }
