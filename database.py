"""
Database Layer for MongoDB Atlas
Handles connection lifecycle, indexes, and initial configuration auto-seeding.
"""

import os
import time
import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError
import bcrypt
from config import Config

logger = logging.getLogger("campus_ai.database")

class Database:
    _instance = None
    _client = None
    _db = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            try:
                cls._client = MongoClient(
                    Config.MONGO_URI,
                    serverSelectionTimeoutMS=6000,
                    connectTimeoutMS=6000,
                    socketTimeoutMS=10000,
                    maxPoolSize=50,
                    minPoolSize=5
                )
                # Verify connection
                cls._client.admin.command('ping')
                cls._db = cls._client[Config.DB_NAME]
                logger.info(f"Connected to MongoDB Atlas database: {Config.DB_NAME}")
                cls.init_indexes()
                cls.seed_initial_data()
            except Exception as e:
                logger.error(f"MongoDB connection failed: {e}")
                raise e
        return cls._client

    @classmethod
    def get_db(cls):
        if cls._db is None:
            cls.get_client()
        return cls._db

    @classmethod
    def ping_latency_ms(cls):
        """Measure real database query round-trip latency in milliseconds."""
        try:
            start = time.perf_counter()
            cls.get_client().admin.command('ping')
            latency = (time.perf_counter() - start) * 1000.0
            return round(latency, 2)
        except Exception as e:
            logger.warning(f"Error measuring DB latency: {e}")
            return -1.0

    @classmethod
    def init_indexes(cls):
        """Create necessary indexes for high-throughput queries."""
        try:
            db = cls._db
            # Users / Admins
            db.users.create_index([("email", ASCENDING)], unique=True)

            # Students
            db.students.create_index([("reg_no", ASCENDING)], unique=True)
            db.students.create_index([("email", ASCENDING)], sparse=True)
            db.students.create_index([("department", ASCENDING)])
            db.students.create_index([("is_enrolled", ASCENDING)])
            db.students.create_index([("status", ASCENDING)])

            # Entry Logs
            db.entry_logs.create_index([("timestamp", DESCENDING)])
            db.entry_logs.create_index([("student_id", ASCENDING), ("timestamp", DESCENDING)])
            db.entry_logs.create_index([("camera_id", ASCENDING)])
            db.entry_logs.create_index([("status", ASCENDING)])

            # Unknown Logs
            db.unknown_logs.create_index([("timestamp", DESCENDING)])
            db.unknown_logs.create_index([("verified", ASCENDING)])

            # Audit Logs
            db.audit_logs.create_index([("timestamp", DESCENDING)])
            db.audit_logs.create_index([("action", ASCENDING)])

            # Settings
            db.settings.create_index([("key", ASCENDING)], unique=True)
            logger.info("MongoDB indexes verified.")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

    @classmethod
    def seed_initial_data(cls):
        """Seed default administrator and institutional configuration if first run."""
        try:
            db = cls._db
            # 1. Admin User
            admin_user = db.users.find_one({"email": Config.DEFAULT_ADMIN_EMAIL})
            if not admin_user:
                hashed_pw = bcrypt.hashpw(Config.DEFAULT_ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                db.users.insert_one({
                    "name": "System Administrator",
                    "email": Config.DEFAULT_ADMIN_EMAIL,
                    "password_hash": hashed_pw,
                    "role": "admin",
                    "created_at": time.time(),
                    "last_login": None,
                    "is_active": True
                })
                logger.info(f"Default admin created: {Config.DEFAULT_ADMIN_EMAIL}")

            # 2. Institutional Settings
            settings_doc = db.settings.find_one({"key": "institutional_config"})
            if not settings_doc:
                db.settings.insert_one({
                    "key": "institutional_config",
                    "institution_name": Config.DEFAULT_INSTITUTION_NAME,
                    "campus_location": Config.DEFAULT_CAMPUS_LOCATION,
                    "similarity_threshold": Config.SIMILARITY_THRESHOLD,
                    "cooldown_period_seconds": Config.COOLDOWN_PERIOD_SECONDS,
                    "face_detection_confidence": Config.FACE_DETECTION_CONFIDENCE,
                    "min_face_size": Config.MIN_FACE_SIZE,
                    "min_blur_variance": Config.MIN_BLUR_VARIANCE,
                    "anti_spoofing_enabled": Config.ANTI_SPOOFING_ENABLED,
                    "cameras": [
                        {"id": "cam_gate_north", "name": "North Main Entrance - Lane 1", "location": "North Gate", "status": "active", "source": "0"},
                        {"id": "cam_gate_south", "name": "South Entrance - Lane 2", "location": "South Gate", "status": "active", "source": "1"},
                        {"id": "cam_library", "name": "Central Library Entry", "location": "Library Building", "status": "active", "source": "2"}
                    ],
                    "data_retention": {
                        "entry_logs_days": Config.RETENTION_DAYS_ENTRY_LOGS,
                        "unknown_logs_days": Config.RETENTION_DAYS_UNKNOWN_LOGS
                    },
                    "updated_at": time.time()
                })
                logger.info(f"Default institutional configuration initialized: {Config.DEFAULT_INSTITUTION_NAME}")
            else:
                # Update existing doc to reflect current configured institution name
                db.settings.update_one(
                    {"key": "institutional_config"},
                    {"$set": {"institution_name": Config.DEFAULT_INSTITUTION_NAME}}
                )
                logger.info(f"Institutional configuration synchronized: {Config.DEFAULT_INSTITUTION_NAME}")

            # 3. Seed demo student embeddings if none enrolled
            enrolled_count = db.students.count_documents({"is_enrolled": True, "embedding": {"$exists": True, "$ne": None}})
            if enrolled_count == 0:
                logger.info("Auto-enrolling default demo students for live scanning...")
                demo_students = [
                    ("2026/CS/001", "Aarav Sharma", "static/demo_students/student_1.jpg", "Computer Science & Engineering", "4th Year"),
                    ("2026/CS/002", "Priya Patel", "static/demo_students/student_2.jpg", "Computer Science & Engineering", "3rd Year"),
                    ("2026/AI/003", "Rohan Verma", "static/demo_students/student_3.jpg", "Artificial Intelligence & Data Science", "3rd Year"),
                    ("2026/AI/004", "Ananya Iyer", "static/demo_students/student_4.jpg", "Artificial Intelligence & Data Science", "2nd Year"),
                    ("2026/CS/005", "Arnnav Panda", "static/demo_students/student_5.jpg", "Computer Science & Engineering", "4th Year")
                ]
                try:
                    from ai.face_detector import FaceDetector
                    from ai.face_recognizer import FaceRecognizer
                    import cv2
                    det = FaceDetector.get_instance()
                    rec = FaceRecognizer.get_instance()

                    for reg, name, img_path, dept, year in demo_students:
                        if os.path.exists(img_path):
                            img = cv2.imread(img_path)
                            res = det.detect_faces(img)
                            crop = res["faces"][0]["face_crop"] if res["faces"] else img
                            emb = rec.extract_embedding(crop)
                            if emb is not None:
                                emb_list = emb.tolist()
                                existing = db.students.find_one({"reg_no": reg})
                                doc = {
                                    "name": name,
                                    "embedding": emb_list,
                                    "is_enrolled": True,
                                    "biometric_consent": True,
                                    "department": dept,
                                    "academic_year": year,
                                    "photo_url": "/" + img_path,
                                    "updated_at": time.time()
                                }
                                if existing:
                                    db.students.update_one({"_id": existing["_id"]}, {"$set": doc})
                                else:
                                    clean_reg = reg.replace("/", "_").lower()
                                    doc.update({
                                        "reg_no": reg,
                                        "email": f"student_{clean_reg}@institution.edu",
                                        "status": "Active",
                                        "created_at": time.time()
                                    })
                                    db.students.insert_one(doc)
                    rec.reload_cache()
                    logger.info("Demo students enrolled successfully.")
                except Exception as enroll_err:
                    logger.warning(f"Could not auto-seed demo student embeddings: {enroll_err}")
        except Exception as e:
            logger.warning(f"Error seeding initial data: {e}")

# Helper collection getters
def get_db():
    return Database.get_db()

def get_users_collection():
    return get_db().users

def get_students_collection():
    return get_db().students

def get_entry_logs_collection():
    return get_db().entry_logs

def get_unknown_logs_collection():
    return get_db().unknown_logs

def get_audit_logs_collection():
    return get_db().audit_logs

def get_settings_collection():
    return get_db().settings
