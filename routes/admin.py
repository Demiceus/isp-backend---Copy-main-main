from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from collections import Counter

from app.models import Customer, ChatSession, Review, Escalation

from services.admin_ai import (
    get_admin_statistics,
    ask_admin_ai,
)


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/stats", methods=["GET"])
def admin_stats():
    """
    Return current NetAssist AI statistics.
    """

    statistics = get_admin_statistics()

    return jsonify({
        "status": "success",
        "data": statistics
    }), 200


@admin_bp.route("/ai", methods=["POST"])
def admin_ai():
    """
    Answer an administrator's question using
    verified database information.
    """

    data = request.get_json() or {}

    question = data.get("question", "").strip()

    if not question:
        return jsonify({
            "error": "question is required"
        }), 400

    result = ask_admin_ai(question)

    return jsonify(result), 200

@admin_bp.route("/analytics", methods=["GET"])
def admin_analytics():
    """Dashboard-ready operational analytics for the admin UI."""
    now = datetime.utcnow()
    since = now - timedelta(days=6)

    daily = []
    for i in range(7):
        day = (since + timedelta(days=i)).date()
        next_day = day + timedelta(days=1)
        total_sessions = ChatSession.query.filter(ChatSession.started_at >= day, ChatSession.started_at < next_day).count()
        escalations = Escalation.query.filter(Escalation.created_at >= day, Escalation.created_at < next_day).count()
        daily.append({"day": day.strftime("%a"), "total": total_sessions, "escalations": escalations})

    categories = Counter(
        x.complaint_type for x in ChatSession.query.filter(
            ChatSession.complaint_type.isnot(None), ChatSession.complaint_type != ""
        ).all()
    )

    sentiment = {
        "positive": Review.query.filter_by(sentiment_label="positive").count(),
        "neutral": Review.query.filter_by(sentiment_label="neutral").count(),
        "negative": Review.query.filter_by(sentiment_label="negative").count(),
    }

    return jsonify({
        "status": "success",
        "data": {
            "customers": Customer.query.count(),
            "total_sessions": ChatSession.query.count(),
            "unresolved_complaints": ChatSession.query.filter_by(session_status="unresolved").count(),
            "resolved_complaints": ChatSession.query.filter_by(session_status="resolved").count(),
            "total_reviews": Review.query.count(),
            "open_escalations": Escalation.query.filter_by(status="open").count(),
            "sentiment": sentiment,
            "categories": dict(categories),
            "daily": daily,
        }
    }), 200
