"""
Campus Entry Log Repository
Records entry events, implements cooldown anti-duplication logic,
and supports multi-attribute filtering and reporting.
"""

import time
from datetime import datetime
from bson import ObjectId
from database import get_entry_logs_collection

class EntryLogModel:
    @staticmethod
    def serialize(doc: dict) -> dict:
        if not doc:
            return None
        ts = doc.get("timestamp", time.time())
        dt = datetime.fromtimestamp(ts)
        return {
            "id": str(doc["_id"]),
            "student_id": doc.get("student_id", ""),
            "student_name": doc.get("student_name", "Unknown"),
            "reg_no": doc.get("reg_no", "N/A"),
            "department": doc.get("department", "N/A"),
            "academic_year": doc.get("academic_year", "N/A"),
            "camera_id": doc.get("camera_id", "cam_main"),
            "camera_name": doc.get("camera_name", "Main Gate"),
            "status": doc.get("status", "Identified"),
            "similarity_score": doc.get("similarity_score", 0.0),
            "response_time_ms": doc.get("response_time_ms", 0.0),
            "snapshot_url": doc.get("snapshot_url", ""),
            "timestamp": ts,
            "formatted_date": dt.strftime("%Y-%m-%d"),
            "formatted_time": dt.strftime("%H:%M:%S")
        }

    @staticmethod
    def is_in_cooldown(student_id: str, camera_id: str, cooldown_seconds: int = 30) -> bool:
        """
        Check if an entry for this student has already been logged within cooldown_seconds.
        Prevents spamming the database with 30 logs per second as a student walks past.
        """
        if not student_id:
            return False
        col = get_entry_logs_collection()
        cutoff = time.time() - cooldown_seconds
        recent = col.find_one({
            "student_id": student_id,
            "camera_id": camera_id,
            "timestamp": {"$gte": cutoff}
        })
        return bool(recent)

    @staticmethod
    def record_entry(data: dict, cooldown_seconds: int = 30) -> tuple:
        """
        Record a verified identification event.
        Returns: (logged: bool, log_id: str or None, reason: str)
        """
        student_id = data.get("student_id")
        camera_id = data.get("camera_id", "cam_main")

        if EntryLogModel.is_in_cooldown(student_id, camera_id, cooldown_seconds):
            return False, None, "Cooldown active for this student on this camera."

        col = get_entry_logs_collection()
        doc = {
            "student_id": student_id,
            "student_name": data.get("student_name", "Unknown"),
            "reg_no": data.get("reg_no", "N/A"),
            "department": data.get("department", "N/A"),
            "academic_year": data.get("academic_year", "N/A"),
            "camera_id": camera_id,
            "camera_name": data.get("camera_name", "Main Gate"),
            "status": data.get("status", "Identified"),
            "similarity_score": float(data.get("similarity_score", 0.0)),
            "response_time_ms": float(data.get("response_time_ms", 0.0)),
            "snapshot_url": data.get("snapshot_url", ""),
            "timestamp": time.time()
        }
        res = col.insert_one(doc)
        return True, str(res.inserted_id), "Entry logged successfully."

    @staticmethod
    def get_entries(filters: dict = None, limit: int = 100, skip: int = 0):
        col = get_entry_logs_collection()
        query = {}
        if filters:
            if filters.get("student_id"):
                query["student_id"] = filters["student_id"]
            if filters.get("reg_no"):
                query["reg_no"] = {"$regex": filters["reg_no"], "$options": "i"}
            if filters.get("department") and filters["department"] != "All":
                query["department"] = filters["department"]
            if filters.get("camera_id") and filters["camera_id"] != "All":
                query["camera_id"] = filters["camera_id"]
            if filters.get("start_date") or filters.get("end_date"):
                date_filter = {}
                if filters.get("start_date"):
                    # Convert start_date YYYY-MM-DD to timestamp
                    start_ts = datetime.strptime(filters["start_date"], "%Y-%m-%d").timestamp()
                    date_filter["$gte"] = start_ts
                if filters.get("end_date"):
                    # End of day 23:59:59
                    end_ts = datetime.strptime(filters["end_date"] + " 23:59:59", "%Y-%m-%d %H:%M:%S").timestamp()
                    date_filter["$lte"] = end_ts
                query["timestamp"] = date_filter

        cursor = col.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        total = col.count_documents(query)
        return [EntryLogModel.serialize(d) for d in cursor], total
