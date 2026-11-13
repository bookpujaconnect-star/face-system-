"""
Facial Enrollment & Biometrics REST API Endpoints
Handles image quality validation, informed consent verification,
deep learning FaceNet embedding generation, and secure biometric deletion.
"""

import time
import base64
import cv2
import numpy as np
from flask import Blueprint, request, jsonify, g
from config import Config
from models.student import StudentModel
from auth import login_required, admin_required, log_audit_event
from ai.face_detector import FaceDetector
from ai.face_recognizer import FaceRecognizer
from ai.quality_validator import QualityValidator

biometric_bp = Blueprint("biometric_bp", __name__)

def decode_base64_image(b64_string: str) -> np.ndarray:
    """Decode base64 data URI string into OpenCV BGR image array."""
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    img_bytes = base64.b64decode(b64_string)
    nparr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

@biometric_bp.route("/api/biometrics/validate-quality", methods=["POST"])
@login_required
def validate_quality():
    """Evaluate image quality without committing enrollment."""
    data = request.get_json() or {}
    image_b64 = data.get("image")
    if not image_b64:
        return jsonify({"status": "error", "message": "Image data is required."}), 400

    try:
        frame = decode_base64_image(image_b64)
        if frame is None:
            return jsonify({"status": "error", "message": "Failed to decode image."}), 400

        detector = FaceDetector.get_instance()
        det_result = detector.detect_faces(frame)

        if not det_result["faces"]:
            return jsonify({
                "status": "warning",
                "is_valid": False,
                "issues": ["No face detected in the frame. Please position face directly in front of the camera."],
                "metrics": {
                    "faces_detected": 0,
                    "overall_score": 0.0
                }
            })

        face_crop = det_result["faces"][0]["face_crop"]
        validator = QualityValidator(
            min_blur_variance=Config.MIN_BLUR_VARIANCE,
            min_face_size=Config.MIN_FACE_SIZE
        )
        quality = validator.validate_face_image(face_crop)

        return jsonify({
            "status": "success",
            "is_valid": quality["is_valid"],
            "quality": quality,
            "face_box": det_result["faces"][0]["bbox"],
            "detection_latency_ms": det_result["latency_ms"]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@biometric_bp.route("/api/biometrics/enroll", methods=["POST"])
@admin_required
def enroll_student():
    """Enroll student face: requires explicit informed consent, quality check, and FaceNet embedding."""
    data = request.get_json() or {}
    student_id = data.get("student_id")
    image_b64 = data.get("image")
    consent_given = data.get("consent_given", False)

    if not student_id or not image_b64:
        return jsonify({"status": "error", "message": "Student ID and image data are required."}), 400

    # Section 7: Informed biometric consent check
    if not consent_given:
        return jsonify({
            "status": "error",
            "message": "Informed biometric consent must be granted before capturing and storing facial embeddings."
        }), 400

    student = StudentModel.get_by_id(student_id)
    if not student:
        return jsonify({"status": "error", "message": "Student not found."}), 404

    try:
        frame = decode_base64_image(image_b64)
        if frame is None:
            return jsonify({"status": "error", "message": "Failed to decode image."}), 400

        detector = FaceDetector.get_instance()
        det_result = detector.detect_faces(frame)

        if not det_result["faces"]:
            return jsonify({"status": "error", "message": "No face detected in the provided image."}), 422

        if len(det_result["faces"]) > 1:
            return jsonify({"status": "error", "message": "Multiple faces detected. Facial enrollment requires exactly one individual in frame."}), 422

        face_crop = det_result["faces"][0]["face_crop"]

        # Validate quality
        validator = QualityValidator(
            min_blur_variance=Config.MIN_BLUR_VARIANCE,
            min_face_size=Config.MIN_FACE_SIZE
        )
        quality = validator.validate_face_image(face_crop)

        if not quality["is_valid"]:
            return jsonify({
                "status": "error",
                "message": f"Image quality validation failed: {', '.join(quality['issues'])}",
                "quality": quality
            }), 422

        # Generate 512-d FaceNet embedding
        recognizer = FaceRecognizer.get_instance()
        emb = recognizer.extract_embedding(face_crop)

        if emb is None:
            return jsonify({"status": "error", "message": "Could not compute facial feature embedding."}), 500

        # Save enrolled photo
        safe_reg = student["reg_no"].replace("/", "_").replace("\\", "_")
        filename = f"{student_id}_{safe_reg}.jpg"
        filepath = Config.STUDENT_PHOTOS_DIR / filename
        cv2.imwrite(str(filepath), face_crop)
        photo_url = f"/static/uploads/students/{filename}"

        # Save to database
        StudentModel.save_biometrics(student_id, emb.tolist(), photo_url)

        # Update in-memory vector cache
        recognizer.reload_cache()

        log_audit_event("BIOMETRIC_ENROLLED", g.current_user["email"], {
            "student_id": student_id,
            "reg_no": student["reg_no"],
            "quality_score": quality["overall_score"]
        })

        return jsonify({
            "status": "success",
            "message": f"Biometrics enrolled successfully for {student['name']}.",
            "photo_url": photo_url,
            "quality": quality
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Enrollment error: {str(e)}"}), 500

@biometric_bp.route("/api/biometrics/delete", methods=["POST"])
@admin_required
def delete_biometrics():
    """Securely purge facial embeddings and images in compliance with data privacy policies."""
    data = request.get_json() or {}
    student_id = data.get("student_id")

    if not student_id:
        return jsonify({"status": "error", "message": "Student ID is required."}), 400

    student = StudentModel.get_by_id(student_id)
    if not student:
        return jsonify({"status": "error", "message": "Student not found."}), 404

    success = StudentModel.delete_biometrics(student_id)
    FaceRecognizer.get_instance().reload_cache()

    log_audit_event("BIOMETRIC_PURGED", g.current_user["email"], {
        "student_id": student_id,
        "reg_no": student["reg_no"]
    })

    return jsonify({
        "status": "success",
        "message": f"Facial biometric data and embeddings for {student['name']} have been completely erased."
    })
