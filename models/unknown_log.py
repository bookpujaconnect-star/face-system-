"""
Unknown Person Detection Model
Logs unclassified face detections for administrative review and manual verification.
Adheres to human-in-the-loop ethical guidelines: never presumes intruder status.
"""

import time
from datetime import datetime
from bson import ObjectId
from database import get_unknown_logs_collection

class UnknownLogModel:
    @staticmethod
    def serialize(doc: dict) -> dict:
        if not doc:
            return None
        ts = doc.get("timestamp", time.time())
        dt = datetime.fromtimestamp(ts)
        return {
            "id": str(doc["_id"]),
            "camera_id": doc.get("camera_id", "cam_main"),
            "camera_name": doc.get("camera_name", "Main Gate"),
            "snapshot_url": doc.get("snapshot_url", ""),
            "best_similarity": doc.get("best_similarity", 0.0),
            "verified": doc.get("verified", False),
            "verification_status": doc.get("verification_status", "Pending Review"), # Pending Review, Verified Student, Visitor, Dismissed
            "verified_student_id": doc.get("verified_student_id"),
            "notes": doc.get("notes", ""),
            "verified_by": doc.get("verified_by"),
            "verified_at": doc.get("verified_at"),
            "timestamp": ts,
            "formatted_date": dt.strftime("%Y-%m-%d"),
            "formatted_time": dt.strftime("%H:%M:%S")
        }

    @staticmethod
    def record_unknown(data: dict) -> str:
        col = get_unknown_logs_collection()
        doc = {
            "camera_id": data.get("camera_id", "cam_main"),
            "camera_name": data.get("camera_name", "Main Gate"),
            "snapshot_url": data.get("snapshot_url", ""),
            "best_similarity": float(data.get("best_similarity", 0.0)),
            "verified": False,
            "verification_status": "Pending Review",
            "verified_student_id": None,
            "notes": data.get("notes", "Awaiting operator review. Non-punitive evaluation."),
            "verified_by": None,
            "verified_at": None,
            "timestamp": time.time()
        }
        res = col.insert_one(doc)
        return str(res.inserted_id)

    @staticmethod
    def get_all(filters: dict = None, limit: int = 50, skip: int = 0):
        col = get_unknown_logs_collection()
        q = {}
        if filters:
            if "verified" in filters:
                q["verified"] = bool(filters["verified"])
            if filters.get("camera_id") and filters["camera_id"] != "All":
                q["camera_id"] = filters["camera_id"]
        cursor = col.find(q).sort("timestamp", -1).skip(skip).limit(limit)
        total = col.count_documents(q)
        return [UnknownLogModel.serialize(d) for d in cursor], total

    @staticmethod
    def verify(log_id: str, verified_status: str, verified_by: str, student_id: str = None, notes: str = ""):
        col = get_unknown_logs_collection()
        res = col.update_one(
            {"_id": ObjectId(log_id)},
            {"$set": {
                "verified": True,
                "verification_status": verified_status,
                "verified_student_id": student_id,
                "notes": notes,
                "verified_by": verified_by,
                "verified_at": time.time()
            }}
        )
        return res.modified_count > 0

    @staticmethod
    def delete_all():
        col = get_unknown_logs_collection()
        res = col.delete_many({})
        return res.deleted_count

    @staticmethod
    def delete_by_id(log_id: str):
        col = get_unknown_logs_collection()
        res = col.delete_one({"_id": ObjectId(log_id)})
        return res.deleted_count > 0
