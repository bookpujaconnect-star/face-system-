"""
System & Institutional Settings REST API Endpoints
Allows configuring institution branding, camera endpoints, thresholds, and data retention.
"""

from flask import Blueprint, request, jsonify, g
from models.settings import SettingsModel
from auth import login_required, admin_required, log_audit_event

settings_bp = Blueprint("settings_bp", __name__)

@settings_bp.route("/api/settings", methods=["GET"])
@login_required
def get_settings():
    settings = SettingsModel.get_settings()
    return jsonify({
        "status": "success",
        "settings": settings
    })

@settings_bp.route("/api/settings", methods=["PUT"])
@admin_required
def update_settings():
    data = request.get_json() or {}

    updates = {}
    if "institution_name" in data and data["institution_name"].strip():
        updates["institution_name"] = data["institution_name"].strip()
    if "campus_location" in data:
        updates["campus_location"] = data["campus_location"].strip()
    if "similarity_threshold" in data:
        updates["similarity_threshold"] = float(data["similarity_threshold"])
    if "cooldown_period_seconds" in data:
        updates["cooldown_period_seconds"] = int(data["cooldown_period_seconds"])
    if "face_detection_confidence" in data:
        updates["face_detection_confidence"] = float(data["face_detection_confidence"])
    if "min_blur_variance" in data:
        updates["min_blur_variance"] = float(data["min_blur_variance"])
    if "anti_spoofing_enabled" in data:
        updates["anti_spoofing_enabled"] = bool(data["anti_spoofing_enabled"])
    if "cameras" in data and isinstance(data["cameras"], list):
        updates["cameras"] = data["cameras"]
    if "data_retention" in data and isinstance(data["data_retention"], dict):
        updates["data_retention"] = data["data_retention"]

    success = SettingsModel.update_settings(updates)
    log_audit_event("SETTINGS_UPDATED", g.current_user["email"], {"updated_keys": list(updates.keys())})

    return jsonify({
        "status": "success",
        "message": "Institutional settings updated successfully.",
        "settings": SettingsModel.get_settings()
    })
