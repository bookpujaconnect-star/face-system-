"""
System Configuration Module
Centralizes all environment variables, security keys, thresholds, and institutional settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

class Config:
    # Server Configuration
    PORT = int(os.getenv("PORT", 5050))
    HOST = os.getenv("HOST", "0.0.0.0")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY = os.getenv("SECRET_KEY", "campus_ai_super_secret_jwt_key_2026_x89q2")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 24))

    # MongoDB Atlas
    MONGO_URI = os.getenv(
        "MONGO_URI",
        "mongodb+srv://arnnavpanda_db_user:motupanda@cluster0.ncj9dnd.mongodb.net/?appName=Cluster0"
    )
    DB_NAME = os.getenv("DB_NAME", "campus_facial_id_db")

    # Default Institutional Parameters (Configurable via UI/Admin Settings)
    DEFAULT_INSTITUTION_NAME = os.getenv("DEFAULT_INSTITUTION_NAME", "Institute")
    DEFAULT_CAMPUS_LOCATION = os.getenv("DEFAULT_CAMPUS_LOCATION", "Main Campus, North Gate")
    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@institution.edu")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "AdminSecure2026!")

    # Biometrics & AI Thresholds
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.68))
    COOLDOWN_PERIOD_SECONDS = int(os.getenv("COOLDOWN_PERIOD_SECONDS", 30))
    FACE_DETECTION_CONFIDENCE = float(os.getenv("FACE_DETECTION_CONFIDENCE", 0.50))
    MIN_FACE_SIZE = int(os.getenv("MIN_FACE_SIZE", 80))
    MIN_BLUR_VARIANCE = float(os.getenv("MIN_BLUR_VARIANCE", 75.0))
    ANTI_SPOOFING_ENABLED = os.getenv("ANTI_SPOOFING_ENABLED", "True").lower() in ("true", "1", "t")

    # Storage Directories
    UPLOADS_DIR = BASE_DIR / "static" / "uploads"
    STUDENT_PHOTOS_DIR = UPLOADS_DIR / "students"
    UNKNOWN_PHOTOS_DIR = UPLOADS_DIR / "unknowns"
    SNAPSHOTS_DIR = UPLOADS_DIR / "snapshots"

    # Data Retention (Days)
    RETENTION_DAYS_ENTRY_LOGS = int(os.getenv("RETENTION_DAYS_ENTRY_LOGS", 180))
    RETENTION_DAYS_UNKNOWN_LOGS = int(os.getenv("RETENTION_DAYS_UNKNOWN_LOGS", 90))

# Ensure upload directories exist
for path in [Config.UPLOADS_DIR, Config.STUDENT_PHOTOS_DIR, Config.UNKNOWN_PHOTOS_DIR, Config.SNAPSHOTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)
