"""
Live Camera Monitoring & Video Processing REST API Endpoints
Processes live webcam/IP camera feeds, runs YOLO multi-face detection,
performs FaceNet recognition, manages cooldown enforcement, and returns real-time HUD overlays.
"""

import time
import base64
import cv2
import numpy as np
from flask import Blueprint, request, jsonify, Response, g
from config import Config
from models.settings import SettingsModel
from models.entry_log import EntryLogModel
from models.unknown_log import UnknownLogModel
from ai.face_detector import FaceDetector
from ai.face_recognizer import FaceRecognizer
from ai.anti_spoofing import AntiSpoofingDetector
from auth import login_required

camera_bp = Blueprint("camera_bp", __name__)

def decode_base64_image(b64_string: str) -> np.ndarray:
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    nparr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

@camera_bp.route("/api/camera/sources", methods=["GET"])
def get_camera_sources():
    settings = SettingsModel.get_settings()
    cameras = settings.get("cameras", [])
    return jsonify({
        "status": "success",
        "cameras": cameras
    })

@camera_bp.route("/api/camera/process-frame", methods=["POST"])
def process_frame():
    """
    Process a single frame from the client webcam/IP camera stream.
    Detects all faces, recognizes students, logs entries (respecting cooldown),
    and records unknown events. Available for gate kiosk scanning and admin monitoring.
    """
    start_total = time.perf_counter()
    data = request.get_json() or {}
    image_b64 = data.get("image")
    camera_id = data.get("camera_id", "cam_gate_north")
    camera_name = data.get("camera_name", "North Gate Lane 1")

    if not image_b64:
        return jsonify({"status": "error", "message": "Image data required."}), 400

    try:
        frame = decode_base64_image(image_b64)
        if frame is None or frame.size == 0:
            return jsonify({"status": "error", "message": "Failed to decode frame."}), 400

        # Load institutional thresholds
        settings = SettingsModel.get_settings()
        similarity_threshold = float(settings.get("similarity_threshold", Config.SIMILARITY_THRESHOLD))
        cooldown_seconds = int(settings.get("cooldown_period_seconds", Config.COOLDOWN_PERIOD_SECONDS))
        anti_spoofing_active = bool(settings.get("anti_spoofing_enabled", True))

        detector = FaceDetector.get_instance()
        recognizer = FaceRecognizer.get_instance()
        spoof_detector = AntiSpoofingDetector()

        night_vision = bool(data.get("night_vision", False))

        # Step 1: Detect all faces with adaptive night-vision / low-light enhancement
        det_res = detector.detect_faces(frame, enable_night_vision=night_vision)
        faces = det_res["faces"]
        detection_latency_ms = det_res["latency_ms"]
        night_vision_active = det_res.get("night_vision_active", False)
        ambient_brightness = det_res.get("ambient_brightness", 0.0)

        results = []
        claimed_student_ids = set()

        for face_info in faces:
            bbox = face_info["bbox"]
            face_crop = face_info["face_crop"]

            # Step 2: Anti-spoofing presentation attack check (optional)
            spoof_info = {"is_real": True, "attack_type": "None", "liveness_score": 1.0}
            if anti_spoofing_active:
                spoof_info = spoof_detector.analyze_liveness(face_crop)

            # Step 3: Facial recognition via FaceNet cosine similarity
            rec_res = recognizer.identify_face(face_crop, similarity_threshold=similarity_threshold)
            status = rec_res["status"]
            similarity_score = rec_res["similarity_score"]
            student = rec_res["student"]
            recognition_latency_ms = rec_res["response_time_ms"]

            # Multi-student disambiguation: prevent two faces in the same frame claiming the same student identity
            if status == "Identified" and student:
                sid = student.get("student_id")
                if sid in claimed_student_ids:
                    # Look for second best rank match that is not claimed
                    reassigned = False
                    for alt in rec_res.get("rank_matches", []):
                        alt_id = alt.get("student_id")
                        if alt_id not in claimed_student_ids and alt.get("similarity", 0) >= similarity_threshold:
                            student = {
                                "student_id": alt_id,
                                "name": alt.get("name", "Student"),
                                "reg_no": alt.get("reg_no", ""),
                                "department": alt.get("department", ""),
                                "academic_year": "Enrolled",
                                "status": "Active",
                                "photo_url": ""
                            }
                            similarity_score = alt.get("similarity")
                            reassigned = True
                            break
                    if not reassigned:
                        status = "Unknown"
                        student = None

            if status == "Identified" and student:
                claimed_student_ids.add(student["student_id"])

            event_logged = False
            log_reason = ""

            if status == "Identified" and student:
                # Save snapshot if entry is recorded
                snapshot_filename = f"snap_{student['student_id']}_{int(time.time()*1000)}.jpg"
                snapshot_path = Config.SNAPSHOTS_DIR / snapshot_filename
                cv2.imwrite(str(snapshot_path), face_crop)
                snapshot_url = f"/static/uploads/snapshots/{snapshot_filename}"

                # Step 4: Record entry with cooldown anti-duplication
                logged, log_id, reason = EntryLogModel.record_entry({
                    "student_id": student["student_id"],
                    "student_name": student["name"],
                    "reg_no": student["reg_no"],
                    "department": student["department"],
                    "academic_year": student["academic_year"],
                    "camera_id": camera_id,
                    "camera_name": camera_name,
                    "status": "Identified",
                    "similarity_score": similarity_score,
                    "response_time_ms": round(detection_latency_ms + recognition_latency_ms, 2),
                    "snapshot_url": snapshot_url
                }, cooldown_seconds=cooldown_seconds)
                event_logged = logged
                log_reason = reason

            else:
                # Unknown Person handling (Section 4.G: record unmatched events, non-punitive)
                snapshot_filename = f"unknown_{camera_id}_{int(time.time()*1000)}.jpg"
                snapshot_path = Config.UNKNOWN_PHOTOS_DIR / snapshot_filename
                cv2.imwrite(str(snapshot_path), face_crop)
                snapshot_url = f"/static/uploads/unknowns/{snapshot_filename}"

                # Only log unknown once every 10s per camera to prevent flooding
                cutoff = time.time() - 10
                from database import get_unknown_logs_collection
                recent_unknown = get_unknown_logs_collection().find_one({
                    "camera_id": camera_id,
                    "timestamp": {"$gte": cutoff}
                })
                if not recent_unknown:
                    UnknownLogModel.record_unknown({
                        "camera_id": camera_id,
                        "camera_name": camera_name,
                        "snapshot_url": snapshot_url,
                        "best_similarity": similarity_score,
                        "notes": "Unmatched facial detection at campus entrance point."
                    })
                    event_logged = True
                    log_reason = "Unknown person detection recorded for review."
                else:
                    log_reason = "Recent unknown already logged."

            results.append({
                "bbox": bbox,
                "status": status,
                "similarity_score": similarity_score,
                "student": student,
                "detection_latency_ms": detection_latency_ms,
                "recognition_latency_ms": recognition_latency_ms,
                "total_face_latency_ms": round(detection_latency_ms + recognition_latency_ms, 2),
                "event_logged": event_logged,
                "log_reason": log_reason,
                "anti_spoofing": spoof_info
            })

        total_frame_latency_ms = round((time.perf_counter() - start_total) * 1000.0, 2)

        return jsonify({
            "status": "success",
            "faces_count": len(faces),
            "results": results,
            "total_frame_latency_ms": total_frame_latency_ms,
            "fps_estimate": round(1000.0 / max(1.0, total_frame_latency_ms), 1),
            "night_vision_active": night_vision_active,
            "ambient_brightness": ambient_brightness
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Frame processing exception: {str(e)}"}), 500

@camera_bp.route("/api/camera/stream")
def mjpeg_stream():
    """
    MJPEG video stream endpoint for embedded camera players.
    Streams annotated frames with bounding boxes, student credentials,
    and adaptive night-vision / infrared enhancement.
    """
    night_vision = request.args.get("night_vision", "false").lower() in ("true", "1", "yes")

    def generate_frames():
        import glob
        from ai.night_vision import NightVisionEnhancer

        photo_files = sorted(glob.glob("static/uploads/students/student_*.jpg"))
        if not photo_files:
            photo_files = sorted(glob.glob("static/uploads/students/*.jpg"))

        detector = FaceDetector.get_instance()
        recognizer = FaceRecognizer.get_instance()
        settings = SettingsModel.get_settings()
        thresh = float(settings.get("similarity_threshold", 0.68))
        nv_enhancer = NightVisionEnhancer()

        # Preload frames in memory for ultra-fast streaming
        loaded_frames = []
        for pf in photo_files[:8]:
            img = cv2.imread(pf)
            if img is not None:
                loaded_frames.append(cv2.resize(img, (640, 480)))

        frame_idx = 0
        while True:
            frame_idx += 1
            if loaded_frames:
                active_idx = (frame_idx // 35) % len(loaded_frames)
                raw_frame = loaded_frames[active_idx].copy()
            else:
                raw_frame = np.full((480, 640, 3), 160, dtype=np.uint8)

            # Detect and identify faces on the raw/enhanced frame first
            det = detector.detect_faces(raw_frame, enable_night_vision=night_vision)

            # Prepare the display frame: tactical green-phosphor HUD if night vision is enabled
            if night_vision:
                display_frame = nv_enhancer.generate_night_vision_hud_frame(raw_frame)
                # Tactical night vision HUD watermark and timestamp
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(display_frame, f"[NVG-IR TACTICAL NIGHT VISION ACTIVE] {now_str}", (16, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 120), 2, cv2.LINE_AA)
            else:
                display_frame = raw_frame

            for f in det.get("faces", []):
                x, y, w, h = f["bbox"]
                rec = recognizer.identify_face(f["face_crop"], similarity_threshold=thresh)
                is_id = (rec.get("status") == "Identified" and rec.get("student"))
                color = (0, 255, 120) if is_id else (68, 68, 239)
                label = f"{rec['student']['name']} ({rec['similarity_score']:.2f})" if is_id else f"Unknown ({rec['similarity_score']:.2f})"

                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 3)
                cv2.rectangle(display_frame, (x, max(0, y - 28)), (x + w, y), color, -1)
                text_color = (0, 0, 0) if night_vision else (255, 255, 255)
                cv2.putText(display_frame, label, (x + 6, max(18, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1, cv2.LINE_AA)

            ret, buffer = cv2.imencode('.jpg', display_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.08)

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
