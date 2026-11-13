"""
Unknown Person Detection & Review REST API Endpoints
Provides an interface for security and administrative staff to manually verify unclassified faces.
Complies with human-in-the-loop ethical guidelines: non-punitive evaluation.
"""

from flask import Blueprint, request, jsonify, g
from models.unknown_log import UnknownLogModel
from auth import login_required, log_audit_event

unknown_bp = Blueprint("unknown_bp", __name__)

@unknown_bp.route("/api/unknowns", methods=["GET"])
@login_required
def get_unknowns():
    camera_id = request.args.get("camera_id")
    verified = request.args.get("verified")
    limit = int(request.args.get("limit", 50))
    skip = int(request.args.get("skip", 0))

    filters = {}
    if camera_id and camera_id != "All":
        filters["camera_id"] = camera_id
    if verified in ["true", "false"]:
        filters["verified"] = (verified == "true")

    logs, total = UnknownLogModel.get_all(filters=filters, limit=limit, skip=skip)

    return jsonify({
        "status": "success",
        "unknowns": logs,
        "total": total,
        "limit": limit,
        "skip": skip
    })

@unknown_bp.route("/api/unknowns/<log_id>/verify", methods=["POST"])
@login_required
def verify_unknown(log_id):
    """
    Manually verify an unknown person detection.
    Options: 'Verified Student', 'Authorized Visitor', 'Staff/Faculty', 'Dismissed'
    """
    data = request.get_json() or {}
    status = data.get("status", "Verified Student")
    student_id = data.get("student_id")
    notes = data.get("notes", "")

    current_user_email = g.current_user["email"]

    success = UnknownLogModel.verify(
        log_id=log_id,
        verified_status=status,
        verified_by=current_user_email,
        student_id=student_id,
        notes=notes
    )

    if not success:
        return jsonify({"status": "error", "message": "Failed to update unknown log record."}), 404

    log_audit_event("UNKNOWN_PERSON_VERIFIED", current_user_email, {
        "log_id": log_id,
        "verification_status": status,
        "student_id": student_id
    })

    return jsonify({
        "status": "success",
        "message": f"Record verified as '{status}'."
    })

@unknown_bp.route("/api/unknowns/all", methods=["DELETE"])
@login_required
def delete_all_unknowns():
    """Delete all recorded unknown detections from database."""
    current_user_email = g.current_user["email"]
    deleted_count = UnknownLogModel.delete_all()
    log_audit_event("ALL_UNKNOWNS_DELETED", current_user_email, {"deleted_count": deleted_count})
    return jsonify({
        "status": "success",
        "message": f"Successfully deleted all {deleted_count} unknown detection records.",
        "count": deleted_count
    })

@unknown_bp.route("/api/unknowns/<log_id>", methods=["DELETE"])
@login_required
def delete_unknown(log_id):
    """Delete a single unknown detection record."""
    current_user_email = g.current_user["email"]
    success = UnknownLogModel.delete_by_id(log_id)
    if not success:
        return jsonify({"status": "error", "message": "Unknown record not found."}), 404
    log_audit_event("UNKNOWN_RECORD_DELETED", current_user_email, {"log_id": log_id})
    return jsonify({
        "status": "success",
        "message": "Record deleted successfully."
    })
