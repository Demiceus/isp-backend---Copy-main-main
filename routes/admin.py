from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from collections import Counter
from app.models import MLFeedback, Message, db

from app.models import (
    db,
    Customer,
    ChatSession,
    Review,
    Escalation,
    MLFeedback,
)

from services.admin_ai import (
    get_admin_statistics,
    ask_admin_ai,
)


admin_bp = Blueprint("admin", __name__)


# =========================================================
# ADMIN STATISTICS
# =========================================================

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


# =========================================================
# ADMIN AI
# =========================================================

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


# =========================================================
# ADMIN ANALYTICS
# =========================================================

@admin_bp.route("/analytics", methods=["GET"])
def admin_analytics():
    """
    Dashboard-ready operational analytics
    for the admin UI.
    """

    now = datetime.utcnow()
    since = now - timedelta(days=6)

    daily = []

    for i in range(7):

        day = (since + timedelta(days=i)).date()
        next_day = day + timedelta(days=1)

        total_sessions = (
            ChatSession.query
            .filter(
                ChatSession.started_at >= day,
                ChatSession.started_at < next_day
            )
            .count()
        )

        escalations = (
            Escalation.query
            .filter(
                Escalation.created_at >= day,
                Escalation.created_at < next_day
            )
            .count()
        )

        daily.append({
            "day": day.strftime("%a"),
            "total": total_sessions,
            "escalations": escalations
        })

    categories = Counter(
        x.complaint_type
        for x in ChatSession.query.filter(
            ChatSession.complaint_type.isnot(None),
            ChatSession.complaint_type != ""
        ).all()
    )

    sentiment = {
        "positive": Review.query.filter_by(
            sentiment_label="positive"
        ).count(),

        "neutral": Review.query.filter_by(
            sentiment_label="neutral"
        ).count(),

        "negative": Review.query.filter_by(
            sentiment_label="negative"
        ).count(),
    }

    return jsonify({
        "status": "success",
        "data": {

            "customers": Customer.query.count(),

            "total_sessions": ChatSession.query.count(),

            "unresolved_complaints": (
                ChatSession.query
                .filter_by(session_status="unresolved")
                .count()
            ),

            "resolved_complaints": (
                ChatSession.query
                .filter_by(session_status="resolved")
                .count()
            ),

            "total_reviews": Review.query.count(),

            "open_escalations": (
                Escalation.query
                .filter_by(status="open")
                .count()
            ),

            "sentiment": sentiment,

            "categories": dict(categories),

            "daily": daily,
        }
    }), 200


# =========================================================
# ML FEEDBACK
# =========================================================

@admin_bp.route("/ml/feedback", methods=["GET"])
def ml_feedback():
    """
    Return ML predictions that have not yet been
    reviewed by an administrator.
    """

    rows = (
        MLFeedback.query
        .filter_by(approved=False)
        .order_by(
            MLFeedback.created_at.desc()
        )
        .all()
    )

    results = []

    for row in rows:

        message = db.session.get(Message, row.message_id)

    results.append({
    "id": row.id,
    "message_id": row.message_id,
    "message": message.content if message else "",
    "predicted_category": row.predicted_category,
    "confidence": row.confidence,
    "corrected_category": row.corrected_category,
    "created_at": row.created_at.isoformat() if row.created_at else None,
})

    return jsonify({
        "status": "success",
        "data": results,
    }), 200


# =========================================================
# REVIEW ML FEEDBACK
# =========================================================

@admin_bp.route(
    "/ml/feedback/<int:feedback_id>",
    methods=["POST"]
)
def review_ml_feedback(feedback_id):
    """
    Allow an administrator to correct an ML prediction.
    """

    data = request.get_json() or {}

    corrected_category = (
        data.get("corrected_category") or ""
    ).strip()

    allowed_categories = {
        "billing",
        "installation",
        "intermittent_connection",
        "no_internet",
        "plan_change",
        "router_modem",
        "service_outage",
        "slow_internet",
        "technical_support",
    }

    # -----------------------------------------------------
    # Validate category
    # -----------------------------------------------------

    if corrected_category not in allowed_categories:

        return jsonify({
            "error": "Invalid complaint category."
        }), 400

    # -----------------------------------------------------
    # Find feedback record
    # -----------------------------------------------------

    row = MLFeedback.query.get_or_404(
        feedback_id
    )

    # -----------------------------------------------------
    # Save administrator correction
    # -----------------------------------------------------

    row.corrected_category = corrected_category

    row.approved = True

    # -----------------------------------------------------
    # Save admin who reviewed it
    # -----------------------------------------------------

    if getattr(g, "admin", None):

        row.reviewed_by = g.admin.id

    row.reviewed_at = datetime.utcnow()

    # -----------------------------------------------------
    # Save database changes
    # -----------------------------------------------------

    db.session.commit()

    return jsonify({
        "status": "approved",
        "feedback_id": row.id,
        "corrected_category": corrected_category,
    }), 200