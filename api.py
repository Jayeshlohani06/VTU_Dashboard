"""
REST API endpoints for VTU Dashboard.
Provides programmatic access to dashboard functionality.
"""

import time
import json
import pandas as pd
from flask import Blueprint, jsonify, request
from cache_config import cache
from logging_config import get_logger

logger = get_logger("api")

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Track server start time for uptime calculation
_START_TIME = time.time()


# ==================== Health ==================== #

@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    uptime_seconds = time.time() - _START_TIME
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    return jsonify({
        "status": "healthy",
        "uptime": f"{hours}h {minutes}m {seconds}s",
        "uptime_seconds": round(uptime_seconds),
        "version": "2.0.0",
        "service": "VTU Student Performance Dashboard",
    })


# ==================== Metrics ==================== #

@api_bp.route("/metrics", methods=["GET"])
def metrics():
    """Basic application metrics for monitoring."""
    import psutil
    import os

    process = psutil.Process(os.getpid()) if _has_psutil() else None

    data = {
        "uptime_seconds": round(time.time() - _START_TIME),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if process:
        data["memory_mb"] = round(process.memory_info().rss / (1024 * 1024), 1)
        data["cpu_percent"] = process.cpu_percent(interval=0.1)

    return jsonify(data)


def _has_psutil():
    try:
        import psutil  # noqa: F401
        return True
    except ImportError:
        return False


# ==================== Data Exports ==================== #

@api_bp.route("/summary", methods=["GET"])
def get_summary():
    """
    Get current session KPIs if data is loaded.
    Query params: session_id (required)
    """
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id parameter required"}), 400

    df = cache.get(session_id)
    if df is None:
        return jsonify({"error": "No data found for session. Upload data via the dashboard first."}), 404

    total = len(df)
    passed = (df["Overall_Result"] == "P").sum() if "Overall_Result" in df.columns else 0
    failed = total - passed

    return jsonify({
        "total_students": int(total),
        "passed": int(passed),
        "failed": int(failed),
        "pass_percentage": round(passed / max(total, 1) * 100, 2),
        "columns": list(df.columns),
        "rows": int(total),
    })


@api_bp.route("/subjects", methods=["GET"])
def get_subjects():
    """
    Get detected subject codes from uploaded data.
    Query params: session_id (required)
    """
    import re
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id parameter required"}), 400

    df = cache.get(session_id)
    if df is None:
        return jsonify({"error": "No data found for session."}), 404

    subjects = []
    for col in df.columns:
        if "_" not in col:
            continue
        prefix, suffix = col.rsplit("_", 1)
        if suffix == "Total" and re.fullmatch(r"\d?[A-Z]{2,}\d{3}[A-Z]?", prefix):
            subjects.append(prefix)

    return jsonify({"subjects": sorted(set(subjects))})


@api_bp.route("/student/<student_id>", methods=["GET"])
def get_student(student_id):
    """
    Get individual student data.
    Query params: session_id (required)
    """
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id parameter required"}), 400

    df = cache.get(session_id)
    if df is None:
        return jsonify({"error": "No data found for session."}), 404

    if "Student ID" in df.columns:
        id_col = "Student ID"
    elif "Student_ID" in df.columns:
        id_col = "Student_ID"
    else:
        return jsonify({"error": "Student ID column not found."}), 500

    match = df[df[id_col].astype(str).str.upper() == student_id.upper()]
    if match.empty:
        return jsonify({"error": f"Student '{student_id}' not found."}), 404

    # Convert to serializable dict
    student_data = match.iloc[0].to_dict()
    cleaned = {}
    for k, v in student_data.items():
        if pd.isna(v):
            cleaned[k] = None
        elif isinstance(v, (int, float)):
            cleaned[k] = v
        else:
            cleaned[k] = str(v)

    return jsonify({"student": cleaned})
