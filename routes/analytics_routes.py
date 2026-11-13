"""
Analytics & Operational Metrics REST API Endpoints
Aggregates campus traffic, identification success rates, department distributions, and response times.
"""

import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from database import get_students_collection, get_entry_logs_collection, get_unknown_logs_collection, Database
from auth import login_required

analytics_bp = Blueprint("analytics_bp", __name__)

@analytics_bp.route("/api/analytics/dashboard", methods=["GET"])
@login_required
def get_dashboard_metrics():
    students_col = get_students_collection()
    entries_col = get_entry_logs_collection()
    unknowns_col = get_unknown_logs_collection()

    total_registered = students_col.count_documents({})
    total_enrolled = students_col.count_documents({"is_enrolled": True})

    # Today's start timestamp (midnight)
    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_ts = today_dt.timestamp()

    entries_today = entries_col.count_documents({"timestamp": {"$gte": today_ts}})
    unknowns_today = unknowns_col.count_documents({"timestamp": {"$gte": today_ts}})

    # Average recognition time across recent entries
    recent_entries = list(entries_col.find({"timestamp": {"$gte": today_ts}}).limit(200))
    if not recent_entries:
        recent_entries = list(entries_col.find().sort("timestamp", -1).limit(50))

    if recent_entries:
        latencies = [e.get("response_time_ms", 0.0) for e in recent_entries if e.get("response_time_ms", 0.0) > 0]
        avg_rec_time = round(sum(latencies) / len(latencies), 1) if latencies else 65.0
    else:
        avg_rec_time = 0.0

    # Department-wise breakdown
    dept_pipeline = [
        {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    dept_counts = list(students_col.aggregate(dept_pipeline))
    departments_data = {
        "labels": [d["_id"] or "Unassigned" for d in dept_counts],
        "values": [d["count"] for d in dept_counts]
    }

    # Daily entry history for past 7 days
    past_7_days = []
    daily_labels = []
    daily_identified = []
    daily_unknowns = []

    for i in range(6, -1, -1):
        day_start = (today_dt - timedelta(days=i)).timestamp()
        day_end = day_start + 86400
        day_name = (today_dt - timedelta(days=i)).strftime("%a (%d %b)")
        daily_labels.append(day_name)

        c_id = entries_col.count_documents({"timestamp": {"$gte": day_start, "$lt": day_end}})
        c_un = unknowns_col.count_documents({"timestamp": {"$gte": day_start, "$lt": day_end}})

        daily_identified.append(c_id)
        daily_unknowns.append(c_un)

    # Hourly traffic distribution today (00:00 to 23:00)
    hourly_labels = [f"{h:02d}:00" for h in range(24)]
    hourly_entries = [0] * 24
    for e in recent_entries:
        dt = datetime.fromtimestamp(e.get("timestamp", time.time()))
        if dt.date() == datetime.now().date():
            hourly_entries[dt.hour] += 1

    # Database query latency
    db_latency = Database.ping_latency_ms()

    return jsonify({
        "status": "success",
        "kpis": {
            "total_registered_students": total_registered,
            "total_enrolled_biometrics": total_enrolled,
            "total_entries_today": entries_today,
            "total_unknowns_today": unknowns_today,
            "avg_recognition_time_ms": avg_rec_time,
            "db_latency_ms": db_latency
        },
        "department_distribution": departments_data,
        "daily_trends": {
            "labels": daily_labels,
            "identified": daily_identified,
            "unknowns": daily_unknowns
        },
        "hourly_traffic": {
            "labels": hourly_labels,
            "counts": hourly_entries
        }
    })
