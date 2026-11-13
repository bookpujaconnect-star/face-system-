"""
Authentication & Authorization Module
Handles password hashing, JWT token issue/verification, role enforcement, and audit logs.
"""

import time
import jwt
import bcrypt
from functools import wraps
from flask import request, jsonify, g
from config import Config
from database import get_users_collection, get_audit_logs_collection

def hash_password(plain_password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

def check_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def generate_token(user_data: dict) -> str:
    """Generate JWT auth token valid for configured hours."""
    now = time.time()
    payload = {
        "sub": str(user_data.get("_id", user_data.get("id"))),
        "email": user_data.get("email"),
        "role": user_data.get("role", "staff"),
        "name": user_data.get("name"),
        "iat": now,
        "exp": now + (Config.JWT_EXPIRATION_HOURS * 3600)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        return jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def log_audit_event(action: str, performed_by: str, details: dict = None, ip_address: str = None):
    """Record security audit trail into MongoDB."""
    try:
        audit_col = get_audit_logs_collection()
        audit_col.insert_one({
            "action": action,
            "performed_by": performed_by,
            "details": details or {},
            "ip_address": ip_address or request.remote_addr if request else "system",
            "timestamp": time.time()
        })
    except Exception as e:
        print(f"Failed to record audit log: {e}")

def get_current_user():
    """Extract and authenticate current user from Authorization header or cookie/session."""
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
    elif request.cookies.get("auth_token"):
        token = request.cookies.get("auth_token")

    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    return payload

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"status": "error", "message": "Authentication required. Please login."}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"status": "error", "message": "Authentication required. Please login."}), 401
        if user.get("role") != "admin":
            return jsonify({"status": "error", "message": "Access denied. Administrator privileges required."}), 403
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function
