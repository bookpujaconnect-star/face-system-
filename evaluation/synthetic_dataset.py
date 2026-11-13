"""
Synthetic Experimental Dataset Generator
Generates realistic computer vision test samples to rigorously test the AI system
under 10 experimental conditions without requiring external human photo downloads.
"""

import cv2
import numpy as np

class SyntheticDatasetGenerator:
    """Creates deterministic, realistic synthetic facial test images for empirical benchmarks."""

    @staticmethod
    def draw_synthetic_face(seed: int = 42, variation: str = "normal", distance: str = "medium") -> np.ndarray:
        """
        Draw a parameterized realistic synthetic face avatar onto a campus entrance scene background.
        """
        np.random.seed(seed)
        # Campus background (entry gate colors)
        bg = np.full((480, 640, 3), (210, 215, 220), dtype=np.uint8)
        # Background elements (hallway / gate lines)
        cv2.line(bg, (0, 360), (640, 360), (160, 165, 170), 2)
        cv2.rectangle(bg, (50, 0), (90, 480), (140, 145, 150), -1)
        cv2.rectangle(bg, (550, 0), (590, 480), (140, 145, 150), -1)

        # Distance scaling
        if distance == "close":
            scale = 1.4
            center_x, center_y = 320, 240
        elif distance == "far":
            scale = 0.55
            center_x, center_y = 320, 220
        else: # medium
            scale = 1.0
            center_x, center_y = 320, 230

        # Unique skin tones based on student seed
        skin_r = int(np.clip(180 + (seed * 17) % 65, 120, 245))
        skin_g = int(np.clip(140 + (seed * 13) % 55, 95, 205))
        skin_b = int(np.clip(110 + (seed * 11) % 45, 75, 175))
        skin_color = (skin_b, skin_g, skin_r)

        # Parameterize facial geometry distinctly by seed
        face_w = int((100 + (seed * 19) % 40) * scale)
        face_h = int((140 + (seed * 23) % 45) * scale)

        # Orientation shift
        offset_x = 0
        offset_y = 0
        if variation == "orientation_yaw_left":
            offset_x = -int(20 * scale)
        elif variation == "orientation_yaw_right":
            offset_x = int(20 * scale)
        elif variation == "orientation_pitch_down":
            offset_y = int(15 * scale)

        # Draw Face Oval
        cv2.ellipse(
            bg,
            (center_x + offset_x, center_y + offset_y),
            (face_w, face_h),
            0, 0, 360,
            skin_color,
            -1,
            lineType=cv2.LINE_AA
        )

        # Hair
        hair_color = (20 + (seed * 5) % 30, 15 + (seed * 4) % 25, 15 + (seed * 3) % 20)
        cv2.ellipse(
            bg,
            (center_x + offset_x, center_y + offset_y - int(face_h * 0.45)),
            (int(face_w * 1.05), int(face_h * 0.45)),
            0, 180, 360,
            hair_color,
            -1,
            lineType=cv2.LINE_AA
        )

        # Eyes geometry parameterized by seed
        eye_dx = int((32 + (seed * 13) % 26) * scale)
        eye_y = center_y + offset_y - int((10 + (seed * 7) % 18) * scale)
        eye_radius = max(3, int((8 + (seed * 3) % 5) * scale))

        cv2.circle(bg, (center_x + offset_x - eye_dx, eye_y), eye_radius, (255, 255, 255), -1, lineType=cv2.LINE_AA)
        cv2.circle(bg, (center_x + offset_x + eye_dx, eye_y), eye_radius, (255, 255, 255), -1, lineType=cv2.LINE_AA)
        # Irises
        iris_color = (25 + (seed * 7) % 35, 20 + (seed * 5) % 25, 10 + (seed * 3) % 15)
        cv2.circle(bg, (center_x + offset_x - eye_dx, eye_y), max(2, int(eye_radius * 0.55)), iris_color, -1, lineType=cv2.LINE_AA)
        cv2.circle(bg, (center_x + offset_x + eye_dx, eye_y), max(2, int(eye_radius * 0.55)), iris_color, -1, lineType=cv2.LINE_AA)

        # Eyebrows
        brow_y = eye_y - int((12 + (seed * 2) % 8) * scale)
        cv2.line(bg, (center_x + offset_x - eye_dx - int(14 * scale), brow_y), (center_x + offset_x - eye_dx + int(14 * scale), brow_y - int(4 * scale)), hair_color, max(2, int(4 * scale)), lineType=cv2.LINE_AA)
        cv2.line(bg, (center_x + offset_x + eye_dx - int(14 * scale), brow_y - int(4 * scale)), (center_x + offset_x + eye_dx + int(14 * scale), brow_y), hair_color, max(2, int(4 * scale)), lineType=cv2.LINE_AA)

        # Nose
        nose_y = eye_y + int((24 + (seed * 9) % 18) * scale)
        nose_color = (int(skin_b * 0.78), int(skin_g * 0.78), int(skin_r * 0.78))
        cv2.line(bg, (center_x + offset_x, eye_y + int(4 * scale)), (center_x + offset_x, nose_y), nose_color, max(1, int(3 * scale)), lineType=cv2.LINE_AA)
        cv2.ellipse(bg, (center_x + offset_x, nose_y), (int((10 + (seed * 3) % 8) * scale), int(6 * scale)), 0, 0, 180, nose_color, -1, lineType=cv2.LINE_AA)

        # Mouth
        mouth_y = nose_y + int((26 + (seed * 7) % 20) * scale)
        mouth_w = int((20 + (seed * 11) % 18) * scale)
        cv2.ellipse(bg, (center_x + offset_x, mouth_y), (mouth_w, int(8 * scale)), 0, 0, 180, (50, 50, 160), -1, lineType=cv2.LINE_AA)

        # Apply Environmental / Lighting Variations
        if variation == "lighting_low":
            # Underexposed / night entrance
            bg = np.clip(bg.astype(np.float32) * 0.35 - 15, 0, 255).astype(np.uint8)
        elif variation == "lighting_harsh":
            # Bright direct sunlight
            bg = np.clip(bg.astype(np.float32) * 1.5 + 40, 0, 255).astype(np.uint8)
        elif variation == "lighting_directional":
            # Shadow on left side
            h, w = bg.shape[:2]
            gradient = np.tile(np.linspace(0.4, 1.4, w), (h, 1))
            bg = np.clip(bg.astype(np.float32) * gradient[:, :, None], 0, 255).astype(np.uint8)
        elif variation == "quality_motion_blur":
            # Walking past camera rapidly
            kernel_size = 15
            kernel = np.zeros((kernel_size, kernel_size))
            kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size)
            kernel /= kernel_size
            bg = cv2.filter2D(bg, -1, kernel)
        elif variation == "quality_sensor_noise":
            # High ISO grain
            noise = np.random.normal(0, 25, bg.shape).astype(np.float32)
            bg = np.clip(bg.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        elif variation == "presentation_attack_screen":
            # Phone screen presentation (Moiré grid + edge border)
            h, w = bg.shape[:2]
            # Draw phone border around face
            cv2.rectangle(bg, (center_x - face_w - 20, center_y - face_h - 40), (center_x + face_w + 20, center_y + face_h + 40), (20, 20, 20), 12)
            # Add moire grid
            grid = np.zeros((h, w, 3), dtype=np.uint8)
            grid[::4, :, :] = 35
            grid[:, ::4, :] = 35
            bg = cv2.add(bg, grid)
        elif variation == "presentation_attack_print":
            # Printed photo paper (flat contrast, paper texture)
            bg = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY)
            bg = cv2.cvtColor(bg, cv2.COLOR_GRAY2BGR)
            paper_noise = np.random.normal(0, 12, bg.shape).astype(np.float32)
            bg = np.clip(bg.astype(np.float32) + paper_noise, 0, 255).astype(np.uint8)

        return bg

    @staticmethod
    def create_multi_face_frame(student_seeds: list) -> np.ndarray:
        """Create a campus entrance gate frame containing multiple students walking together."""
        bg = np.full((480, 640, 3), (210, 215, 220), dtype=np.uint8)
        # Background entry gate
        cv2.line(bg, (0, 360), (640, 360), (160, 165, 170), 2)
        cv2.rectangle(bg, (30, 0), (60, 480), (140, 145, 150), -1)
        cv2.rectangle(bg, (580, 0), (610, 480), (140, 145, 150), -1)

        positions = [
            (160, 230, 0.85),
            (360, 220, 0.90),
            (500, 240, 0.75)
        ]

        for i, seed in enumerate(student_seeds[:3]):
            cx, cy, scale = positions[i]
            skin_r = int(np.clip(180 + (seed * 17) % 65, 120, 245))
            skin_g = int(np.clip(140 + (seed * 13) % 55, 95, 205))
            skin_b = int(np.clip(110 + (seed * 11) % 45, 75, 175))
            skin_color = (skin_b, skin_g, skin_r)

            fw = int(100 * scale)
            fh = int(130 * scale)

            cv2.ellipse(bg, (cx, cy), (fw, fh), 0, 0, 360, skin_color, -1, lineType=cv2.LINE_AA)
            cv2.ellipse(bg, (cx, cy - int(60 * scale)), (int(fw * 1.05), int(60 * scale)), 0, 180, 360, (30, 25, 25), -1, lineType=cv2.LINE_AA)
            # Eyes
            cv2.circle(bg, (cx - int(35 * scale), cy - int(10 * scale)), max(3, int(8 * scale)), (255, 255, 255), -1)
            cv2.circle(bg, (cx + int(35 * scale), cy - int(10 * scale)), max(3, int(8 * scale)), (255, 255, 255), -1)
            # Mouth
            cv2.ellipse(bg, (cx, cy + int(45 * scale)), (int(20 * scale), int(8 * scale)), 0, 0, 180, (50, 50, 160), -1)

        return bg
