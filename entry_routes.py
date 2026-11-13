"""
Campus Entry History & Reporting REST API Endpoints
Provides filtered entry event queries, CSV/Excel report generation, and daily statistics.
"""

import io
import csv
from flask import Blueprint, request, jsonify, Response
from models.entry_log import EntryLogModel
from auth import login_required

entry_bp = Blueprint("entry_bp", __name__)

@entry_bp.route("/api/entries/recent", methods=["GET"])
def get_recent_entries():
    """Public endpoint for gate kiosk to display recent entries."""
    limit = int(request.args.get("limit", 10))
    entries, total = EntryLogModel.get_entries(limit=limit)
    return jsonify({
        "status": "success",
        "entries": entries,
        "total": total
    })

@entry_bp.route("/api/entries", methods=["GET"])
@login_required
def get_entries():
    student_id = request.args.get("student_id")
    reg_no = request.args.get("reg_no")
    department = request.args.get("department")
    camera_id = request.args.get("camera_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    limit = int(request.args.get("limit", 100))
    skip = int(request.args.get("skip", 0))

    filters = {}
    if student_id:
        filters["student_id"] = student_id
    if reg_no:
        filters["reg_no"] = reg_no
    if department:
        filters["department"] = department
    if camera_id:
        filters["camera_id"] = camera_id
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date

    entries, total = EntryLogModel.get_entries(filters=filters, limit=limit, skip=skip)

    return jsonify({
        "status": "success",
        "entries": entries,
        "total": total,
        "limit": limit,
        "skip": skip
    })

@entry_bp.route("/api/entries/export", methods=["GET"])
@login_required
def export_entries():
    """Export filtered entry logs to CSV format."""
    department = request.args.get("department")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    filters = {}
    if department and department != "All":
        filters["department"] = department
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date

    entries, _ = EntryLogModel.get_entries(filters=filters, limit=5000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Log ID", "Date", "Time", "Student Name", "Reg No", "Department", "Academic Year", "Camera ID", "Camera Name", "Similarity Score", "Latency (ms)", "Status"])

    for e in entries:
        writer.writerow([
            e["id"],
            e["formatted_date"],
            e["formatted_time"],
            e["student_name"],
            e["reg_no"],
            e["department"],
            e["academic_year"],
            e["camera_id"],
            e["camera_name"],
            f"{e['similarity_score']:.3f}",
            e["response_time_ms"],
            e["status"]
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=campus_entry_history.csv"}
    )
