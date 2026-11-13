"""
Student Management REST API Endpoints
Handles student registration, metadata updates, search, CSV/Excel import/export, and seeding.
"""

import io
import csv
import pandas as pd
from flask import Blueprint, request, jsonify, Response, g
from models.student import StudentModel
from auth import login_required, admin_required, log_audit_event
from ai.face_recognizer import FaceRecognizer

student_bp = Blueprint("student_bp", __name__)

@student_bp.route("/api/students", methods=["GET"])
@login_required
def get_students():
    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    status = request.args.get("status", "").strip()
    enrolled = request.args.get("enrolled", "").strip()
    member_type = request.args.get("member_type", "").strip()
    limit = int(request.args.get("limit", 100))
    skip = int(request.args.get("skip", 0))

    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"reg_no": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    if department and department != "All":
        query["department"] = department
    if status and status != "All":
        query["status"] = status
    if enrolled and enrolled != "All":
        query["is_enrolled"] = (enrolled.lower() in ("true", "1", "yes"))
    if member_type and member_type != "All":
        query["member_type"] = member_type

    students = StudentModel.get_all(query=query, limit=limit, skip=skip)
    total = StudentModel.count(query=query)

    return jsonify({
        "status": "success",
        "students": students,
        "total": total,
        "limit": limit,
        "skip": skip
    })

@student_bp.route("/api/students/<student_id>", methods=["GET"])
@login_required
def get_student_detail(student_id):
    student = StudentModel.get_by_id(student_id)
    if not student:
        return jsonify({"status": "error", "message": "Student not found."}), 404
    return jsonify({"status": "success", "student": student})

@student_bp.route("/api/students", methods=["POST"])
@admin_required
def create_student():
    data = request.get_json() or {}
    reg_no = data.get("reg_no", "").strip().upper()
    name = data.get("name", "").strip()

    if not reg_no or not name:
        return jsonify({"status": "error", "message": "Registration number and student name are required."}), 400

    existing = StudentModel.get_by_reg_no(reg_no)
    if existing:
        return jsonify({"status": "error", "message": f"Student with Reg No '{reg_no}' already exists."}), 409

    student_id = StudentModel.create(data)
    log_audit_event("STUDENT_CREATED", g.current_user["email"], {"student_id": student_id, "reg_no": reg_no})

    return jsonify({
        "status": "success",
        "message": "Student created successfully.",
        "student_id": student_id
    }), 201

@student_bp.route("/api/students/<student_id>", methods=["PUT"])
@admin_required
def update_student(student_id):
    data = request.get_json() or {}
    student = StudentModel.get_by_id(student_id)
    if not student:
        return jsonify({"status": "error", "message": "Student not found."}), 404

    # Disallow overriding biometrics directly via general student update
    updates = {k: v for k, v in data.items() if k not in ["_id", "id", "embedding", "created_at"]}

    success = StudentModel.update(student_id, updates)
    log_audit_event("STUDENT_UPDATED", g.current_user["email"], {"student_id": student_id, "fields": list(updates.keys())})

    return jsonify({"status": "success", "message": "Student record updated."})

@student_bp.route("/api/students/<student_id>", methods=["DELETE"])
@admin_required
def delete_student(student_id):
    student = StudentModel.get_by_id(student_id)
    if not student:
        return jsonify({"status": "error", "message": "Student not found."}), 404

    success = StudentModel.delete(student_id)
    # Refresh in-memory embeddings cache
    FaceRecognizer.get_instance().reload_cache()
    log_audit_event("STUDENT_DELETED", g.current_user["email"], {"student_id": student_id, "reg_no": student["reg_no"]})

    return jsonify({"status": "success", "message": "Student record deleted successfully."})

@student_bp.route("/api/students/import", methods=["POST"])
@admin_required
def import_students():
    """Import student records from uploaded CSV or Excel file."""
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded."}), 400

    file = request.files["file"]
    filename = file.filename.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(file)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            return jsonify({"status": "error", "message": "Unsupported file format. Please upload CSV or Excel (.xlsx)."}), 400

        # Required columns: reg_no, name
        cols = [c.strip().lower() for c in df.columns]
        df.columns = cols

        if "reg_no" not in df.columns or "name" not in df.columns:
            return jsonify({"status": "error", "message": "File must contain 'reg_no' and 'name' columns."}), 400

        imported = 0
        skipped = 0

        for _, row in df.iterrows():
            reg_no = str(row["reg_no"]).strip().upper()
            name = str(row["name"]).strip()
            if not reg_no or not name or reg_no == "NAN" or name == "NAN":
                continue

            existing = StudentModel.get_by_reg_no(reg_no)
            if existing:
                skipped += 1
                continue

            dept = str(row.get("department", "General Engineering")).strip()
            year = str(row.get("academic_year", "1st Year")).strip()
            email = str(row.get("email", "")).strip().lower() if "email" in df.columns and str(row.get("email")) != "nan" else f"{reg_no.lower()}@institution.edu"
            phone = str(row.get("phone", "")).strip() if "phone" in df.columns and str(row.get("phone")) != "nan" else ""

            StudentModel.create({
                "reg_no": reg_no,
                "name": name,
                "department": dept,
                "academic_year": year,
                "email": email,
                "phone": phone,
                "biometric_consent": False
            })
            imported += 1

        log_audit_event("STUDENTS_BULK_IMPORT", g.current_user["email"], {"imported": imported, "skipped": skipped})

        return jsonify({
            "status": "success",
            "message": f"Successfully imported {imported} students. Skipped {skipped} duplicate/empty records.",
            "imported_count": imported,
            "skipped_count": skipped
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to parse file: {str(e)}"}), 500

@student_bp.route("/api/students/export", methods=["GET"])
@login_required
def export_students():
    """Export students roster to CSV."""
    students = StudentModel.get_all(limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Registration No", "Full Name", "Email", "Department", "Academic Year", "Phone", "Status", "Enrolled Biometrics", "Consent Given"])

    for s in students:
        writer.writerow([
            s["reg_no"],
            s["name"],
            s["email"],
            s["department"],
            s["academic_year"],
            s["phone"],
            s["status"],
            "Yes" if s["is_enrolled"] else "No",
            "Yes" if s["biometric_consent"] else "No"
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=students_roster.csv"}
    )

@student_bp.route("/api/students/seed-synthetic", methods=["POST"])
@admin_required
def seed_synthetic_students():
    """Populate database with synthetic student records across multiple departments for demonstration."""
    from evaluation.synthetic_dataset import SyntheticDatasetGenerator
    import cv2
    import os
    from config import Config

    sample_roster = [
        ("2026/CS/001", "Aarav Sharma", "aarav.sharma@institution.edu", "Computer Science & Engineering", "4th Year", "9876543210"),
        ("2026/CS/002", "Priya Patel", "priya.patel@institution.edu", "Computer Science & Engineering", "3rd Year", "9876543211"),
        ("2026/AI/003", "Rohan Verma", "rohan.verma@institution.edu", "Artificial Intelligence & Data Science", "3rd Year", "9876543212"),
        ("2026/AI/004", "Ananya Iyer", "ananya.iyer@institution.edu", "Artificial Intelligence & Data Science", "2nd Year", "9876543213"),
        ("2026/EE/005", "Vikram Reddy", "vikram.reddy@institution.edu", "Electrical & Electronics Engineering", "4th Year", "9876543214"),
        ("2026/EE/006", "Sneha Kulkarni", "sneha.kulkarni@institution.edu", "Electrical & Electronics Engineering", "1st Year", "9876543215"),
        ("2026/ME/007", "Aditya Nair", "aditya.nair@institution.edu", "Mechanical Engineering", "2nd Year", "9876543216"),
        ("2026/CV/008", "Diya Sengupta", "diya.sengupta@institution.edu", "Civil Engineering", "3rd Year", "9876543217")
    ]

    created = 0
    recognizer = FaceRecognizer.get_instance()

    for idx, (reg, name, email, dept, year, phone) in enumerate(sample_roster):
        existing = StudentModel.get_by_reg_no(reg)
        if not existing:
            stu_id = StudentModel.create({
                "reg_no": reg,
                "name": name,
                "email": email,
                "department": dept,
                "academic_year": year,
                "phone": phone,
                "biometric_consent": True
            })

            # Generate synthetic enrollment face sample
            face_img = SyntheticDatasetGenerator.draw_synthetic_face(seed=idx + 1)
            filename = f"student_{reg.replace('/', '_')}.jpg"
            filepath = Config.STUDENT_PHOTOS_DIR / filename
            cv2.imwrite(str(filepath), face_img)

            crop = face_img[100:350, 200:440]
            emb = recognizer.extract_embedding(crop)
            if emb is not None:
                StudentModel.save_biometrics(
                    stu_id,
                    emb.tolist(),
                    f"/static/uploads/students/{filename}"
                )
            created += 1

    recognizer.reload_cache()
    log_audit_event("STUDENTS_SYNTHETIC_SEEDED", g.current_user["email"], {"count": created})

    return jsonify({
        "status": "success",
        "message": f"Seeded {created} synthetic students with valid FaceNet facial embeddings across 5 departments.",
        "created": created
    })
