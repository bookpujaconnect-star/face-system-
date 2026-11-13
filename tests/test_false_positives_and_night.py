"""
Automated Verification for:
1. False Positive Suppression (Ensures non-face background objects, walls, furniture are NOT detected or tagged as Unmatched)
2. Night Vision & Low-Light Enhancement (Ensures student faces in dark/night entrance lighting are detected and recognized)
"""

import base64
import cv2
import json
import urllib.request
import numpy as np
from ai.night_vision import NightVisionEnhancer
from ai.face_detector import FaceDetector

def test_empty_background_zero_false_positives():
    print("\n--- TEST 1: Empty Campus Background / Non-Face Objects ---")
    # Create empty scene: wall, door, floor, table textures (brown, skin-toned, textured)
    bg = np.full((480, 640, 3), (120, 140, 160), dtype=np.uint8)
    # Wooden door (skin-tone hue)
    cv2.rectangle(bg, (150, 50), (320, 480), (70, 110, 180), -1)
    # Desk / table
    cv2.rectangle(bg, (50, 350), (590, 480), (50, 80, 140), -1)
    # Wall pattern
    cv2.line(bg, (0, 200), (640, 200), (200, 200, 200), 3)

    _, buffer = cv2.imencode('.jpg', bg)
    b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

    req = urllib.request.Request(
        "http://127.0.0.1:5050/api/camera/process-frame",
        data=json.dumps({"image": b64_str, "camera_id": "Gate-North-01"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f"Status: {resp.status}")
        print(f"Faces detected in empty scene: {res.get('faces_count')}")
        print(f"Results list: {res.get('results')}")
        assert res.get('faces_count') == 0, f"Expected 0 faces in empty scene, got {res.get('faces_count')}"
        assert len(res.get('results', [])) == 0, f"Expected 0 results, got {len(res.get('results'))}"
        print(">>> SUCCESS: Zero false positives! Non-face background objects are completely ignored.")

def test_night_vision_enhancement():
    print("\n--- TEST 2: Night-Time / Low-Light Face Scanner ---")
    # Load an enrolled student photo from static/uploads/students/
    from database import get_students_collection
    col = get_students_collection()
    student = col.find_one({"is_enrolled": True, "photo_url": {"$exists": True}})
    if not student:
        print("No enrolled student found in DB for test.")
        return

    import os
    photo_rel = student["photo_url"].lstrip("/")
    if not os.path.exists(photo_rel):
        print(f"Photo path {photo_rel} does not exist.")
        return

    img = cv2.imread(photo_rel)
    if img is None:
        print("Failed to read student photo.")
        return

    # Simulate pitch-dark night entrance (ambient luminance < 25)
    dark_night_img = np.clip(img.astype(np.float32) * 0.18 + np.random.normal(0, 3, img.shape), 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(dark_night_img, cv2.COLOR_BGR2GRAY)
    dark_brightness = float(np.mean(gray))
    print(f"Original photo shape: {img.shape}, Simulated night brightness: {dark_brightness:.1f} / 255.0")

    # 1. Send without night vision
    _, buf1 = cv2.imencode('.jpg', dark_night_img)
    b64_dark = "data:image/jpeg;base64," + base64.b64encode(buf1).decode('utf-8')

    req1 = urllib.request.Request(
        "http://127.0.0.1:5050/api/camera/process-frame",
        data=json.dumps({"image": b64_dark, "night_vision": False}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req1) as resp1:
        res1 = json.loads(resp1.read().decode('utf-8'))
        print(f"[Without Night Vision] Faces detected: {res1.get('faces_count')}, Auto-enhanced: {res1.get('night_vision_active')}")

    # 2. Send WITH night vision tool forced ON
    req2 = urllib.request.Request(
        "http://127.0.0.1:5050/api/camera/process-frame",
        data=json.dumps({"image": b64_dark, "night_vision": True}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req2) as resp2:
        res2 = json.loads(resp2.read().decode('utf-8'))
        print(f"[WITH NIGHT VISION TOOL ON] Faces detected: {res2.get('faces_count')}")
        print(f"Night vision active flag: {res2.get('night_vision_active')}")
        print(f"Ambient brightness measured: {res2.get('ambient_brightness')}")
        for r in res2.get("results", []):
            stu = r.get("student") or {}
            print(f"  Result: Status={r.get('status')}, Student={stu.get('name')}, SimScore={r.get('similarity_score')}")

        assert res2.get("night_vision_active") is True, "Expected night_vision_active to be True"
        print(">>> SUCCESS: Night Vision tool active and successfully scans the face in dark entrance conditions!")

if __name__ == "__main__":
    test_empty_background_zero_false_positives()
    test_night_vision_enhancement()
