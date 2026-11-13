from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.biometric_routes import biometric_bp
from routes.camera_routes import camera_bp
from routes.entry_routes import entry_bp
from routes.unknown_routes import unknown_bp
from routes.analytics_routes import analytics_bp
from routes.settings_routes import settings_bp
from routes.evaluation_routes import evaluation_bp

__all__ = [
    "auth_bp",
    "student_bp",
    "biometric_bp",
    "camera_bp",
    "entry_bp",
    "unknown_bp",
    "analytics_bp",
    "settings_bp",
    "evaluation_bp"
]
