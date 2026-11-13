"""
Student Data Model & Repository
Manages student records, metadata, enrollment flags, embeddings, and consent.
"""

import time
from bson import ObjectId
from database import get_students_collection

class StudentModel:
    @staticmethod
    def serialize(doc: dict) -> dict:
        if not doc:
            return None
        return {
            "id": str(doc["_id"]),
            "reg_no": doc.get("reg_no", ""),
            "name": doc.get("name", ""),
            "email": doc.get("email", ""),
            "department": doc.get("department", ""),
            "academic_year": doc.get("academic_year", ""),
            "member_type": doc.get("member_type", "Student"),  # Student or Faculty
            "designation": doc.get("designation", doc.get("academic_year", "")),
            "phone": doc.get("phone", ""),
            "status": doc.get("status", "Active"),  # Active, Inactive, Suspended
            "is_enrolled": doc.get("is_enrolled", False),
            "biometric_consent": doc.get("biometric_consent", False),
            "consent_date": doc.get("consent_date"),
            "photo_url": doc.get("photo_url", ""),
            "has_embedding": bool(doc.get("embedding")),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at")
        }

    @staticmethod
    def get_all(query=None, limit=100, skip=0):
        col = get_students_collection()
        q = query or {}
        cursor = col.find(q).sort("created_at", -1).skip(skip).limit(limit)
        return [StudentModel.serialize(d) for d in cursor]

    @staticmethod
    def count(query=None):
        return get_students_collection().count_documents(query or {})

    @staticmethod
    def get_by_id(student_id: str):
        try:
            doc = get_students_collection().find_one({"_id": ObjectId(student_id)})
            return StudentModel.serialize(doc)
        except Exception:
            return None

    @staticmethod
    def get_by_reg_no(reg_no: str):
        doc = get_students_collection().find_one({"reg_no": reg_no.strip().upper()})
        return StudentModel.serialize(doc)

    @staticmethod
    def create(data: dict):
        col = get_students_collection()
        now = time.time()
        record = {
            "reg_no": data["reg_no"].strip().upper(),
            "name": data["name"].strip(),
            "email": data.get("email", "").strip().lower(),
            "department": data.get("department", "General Engineering"),
            "academic_year": data.get("academic_year", "1st Year"),
            "member_type": data.get("member_type", "Student"),
            "designation": data.get("designation", data.get("academic_year", "1st Year")),
            "phone": data.get("phone", "").strip(),
            "status": data.get("status", "Active"),
            "is_enrolled": False,
            "biometric_consent": bool(data.get("biometric_consent", False)),
            "consent_date": now if data.get("biometric_consent") else None,
            "photo_url": data.get("photo_url", ""),
            "embedding": None,
            "created_at": now,
            "updated_at": now
        }
        res = col.insert_one(record)
        return str(res.inserted_id)

    @staticmethod
    def update(student_id: str, updates: dict):
        col = get_students_collection()
        updates["updated_at"] = time.time()
        # If reg_no is modified, ensure uppercase
        if "reg_no" in updates:
            updates["reg_no"] = updates["reg_no"].strip().upper()
        if "email" in updates:
            updates["email"] = updates["email"].strip().lower()

        res = col.update_one({"_id": ObjectId(student_id)}, {"$set": updates})
        return res.modified_count > 0

    @staticmethod
    def delete(student_id: str):
        col = get_students_collection()
        res = col.delete_one({"_id": ObjectId(student_id)})
        return res.deleted_count > 0

    @staticmethod
    def delete_biometrics(student_id: str):
        """Right to be forgotten: Securely clear embedding and enrollment photo."""
        col = get_students_collection()
        res = col.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {
                "embedding": None,
                "is_enrolled": False,
                "photo_url": "",
                "biometric_consent": False,
                "consent_date": None,
                "updated_at": time.time()
            }}
        )
        return res.modified_count > 0

    @staticmethod
    def save_biometrics(student_id: str, embedding: list, photo_url: str):
        col = get_students_collection()
        now = time.time()
        res = col.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {
                "embedding": embedding,
                "photo_url": photo_url,
                "is_enrolled": True,
                "biometric_consent": True,
                "consent_date": now,
                "updated_at": now
            }}
        )
        return res.modified_count > 0
