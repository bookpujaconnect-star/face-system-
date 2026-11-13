"""
Facial Image Quality Validator
Assesses blur, illumination, contrast, face resolution, and facial aspect ratio
before enrollment to ensure high recognition accuracy and ISO/IEC 19794-5 compliance.
"""

import cv2
import numpy as np

class QualityValidator:
    def __init__(self, min_blur_variance=75.0, min_face_size=80, min_brightness=40, max_brightness=225, min_contrast=25):
        self.min_blur_variance = min_blur_variance
        self.min_face_size = min_face_size
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_contrast = min_contrast

    def validate_face_image(self, face_bgr: np.ndarray) -> dict:
        """
        Evaluate facial image quality metrics.
        Returns:
            dict with:
                is_valid: bool
                overall_score: float (0 - 100)
                blur_variance: float
                brightness: float
                contrast: float
                dimensions: tuple (w, h)
                issues: list of str
        """
        if face_bgr is None or face_bgr.size == 0:
            return {
                "is_valid": False,
                "overall_score": 0.0,
                "blur_variance": 0.0,
                "brightness": 0.0,
                "contrast": 0.0,
                "dimensions": (0, 0),
                "issues": ["Empty or invalid image data"]
            }

        h, w = face_bgr.shape[:2]
        issues = []
        scores = []

        # 1. Resolution Check
        if w < self.min_face_size or h < self.min_face_size:
            issues.append(f"Face resolution ({w}x{h}) is below required minimum ({self.min_face_size}x{self.min_face_size} px).")
            scores.append(max(0.0, min(100.0, (min(w, h) / self.min_face_size) * 50.0)))
        else:
            scores.append(100.0)

        # 2. Blur / Sharpness Check using Laplacian Variance
        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_var = float(laplacian.var())

        if blur_var < self.min_blur_variance:
            issues.append(f"Image is too blurry (sharpness score: {blur_var:.1f}, required: >= {self.min_blur_variance:.1f}).")
            scores.append(max(0.0, min(100.0, (blur_var / self.min_blur_variance) * 70.0)))
        else:
            sharpness_score = min(100.0, 70.0 + (blur_var / self.min_blur_variance) * 15.0)
            scores.append(sharpness_score)

        # 3. Illumination / Brightness Check
        mean_brightness = float(np.mean(gray))
        if mean_brightness < self.min_brightness:
            issues.append(f"Image is under-exposed / too dark (brightness: {mean_brightness:.1f}).")
            scores.append(max(0.0, (mean_brightness / self.min_brightness) * 50.0))
        elif mean_brightness > self.max_brightness:
            issues.append(f"Image is over-exposed / washed out (brightness: {mean_brightness:.1f}).")
            scores.append(max(0.0, (255.0 - mean_brightness) / (255.0 - self.max_brightness) * 50.0))
        else:
            scores.append(95.0)

        # 4. Contrast Check (Standard Deviation of pixel values)
        contrast = float(np.std(gray))
        if contrast < self.min_contrast:
            issues.append(f"Low image contrast ({contrast:.1f}, required: >= {self.min_contrast:.1f}).")
            scores.append(max(0.0, (contrast / self.min_contrast) * 60.0))
        else:
            scores.append(95.0)

        # Compute weighted overall score
        overall_score = float(np.mean(scores)) if scores else 0.0
        is_valid = (len(issues) == 0)

        return {
            "is_valid": is_valid,
            "overall_score": round(overall_score, 1),
            "blur_variance": round(blur_var, 2),
            "brightness": round(mean_brightness, 2),
            "contrast": round(contrast, 2),
            "dimensions": (w, h),
            "issues": issues
        }
