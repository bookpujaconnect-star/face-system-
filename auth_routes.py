"""
Authentication API Endpoints
Provides secure admin login, session verification, token refresh, and audit logging.
"""

import time
from flask import Blueprint, request, jsonify, g
from database import get_users_collection, get_audit_logs_collection
from auth import check_password, generate_token, login_required, admin_required, log_audit_event

auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required."}), 400

    col = get_users_collection()
    user = col.find_one({"email": email})

    if not user or not check_password(password, user.get("password_hash", "")):
        log_audit_event("FAILED_LOGIN_ATTEMPT", email, {"reason": "Invalid credentials"})
        return jsonify({"status": "error", "message": "Invalid email or password."}), 401

    if not user.get("is_active", True):
        return jsonify({"status": "error", "message": "Account has been deactivated. Contact administration."}), 403

    # Update last login timestamp
    col.update_one({"_id": user["_id"]}, {"$set": {"last_login": time.time()}})

    token = generate_token(user)
    log_audit_event("USER_LOGIN_SUCCESS", email, {"role": user.get("role")})

    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user.get("name"),
            "email": user.get("email"),
            "role": user.get("role")
        }
    })

@auth_bp.route("/api/auth/me", methods=["GET"])
@login_required
def get_current_profile():
    return jsonify({
        "status": "success",
        "user": g.current_user
    })

@auth_bp.route("/api/auth/logout", methods=["POST"])
@login_required
def logout():
    log_audit_event("USER_LOGOUT", g.current_user.get("email"))
    return jsonify({"status": "success", "message": "Logged out successfully."})

@auth_bp.route("/api/auth/audit-logs", methods=["GET"])
@admin_required
def get_audit_trail():
    col = get_audit_logs_collection()
    cursor = col.find().sort("timestamp", -1).limit(100)
    logs = []
    for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        logs.append(doc)
    return jsonify({"status": "success", "logs": logs})
