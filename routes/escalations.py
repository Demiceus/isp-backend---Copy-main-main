# routes/escalations.py
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from app.models import db, Escalation, ChatSession, Review, Customer, Message

escalations_bp = Blueprint("escalations", __name__)


def _ticket_number(escalation):
    return f"NA-CASE-{escalation.id:06d}"


@escalations_bp.route("/", methods=["GET"])
def list_escalations():
    """Returns the escalation queue for human agents, optionally filtered by status."""
    status = request.args.get("status", "open")  # open | in_progress | closed | all

    query = Escalation.query
    if status != "all":
        query = query.filter_by(status=status)

    escalations = query.order_by(Escalation.created_at.desc()).all()

    result = []
    for esc in escalations:
        session = ChatSession.query.get(esc.session_id)
        review = Review.query.get(esc.review_id) if esc.review_id else None
        customer = Customer.query.get(session.customer_id) if session else None

        result.append({
            "escalation_id": esc.id,
            "ticket_number": _ticket_number(esc),
            "status": esc.status,
            "reason": esc.reason,
            "source": esc.source,
            "assigned_to": esc.assigned_to,
            "created_at": esc.created_at.isoformat(),
            "customer_account": customer.account_number if customer else None,
            "complaint_type": session.complaint_type if session else None,
            "chat_summary": session.chat_summary if session else None,
            "review_text": review.review_text if review else None,
            "sentiment_label": review.sentiment_label if review else None,
        })

    return jsonify(result), 200


@escalations_bp.route("/<int:escalation_id>", methods=["GET"])
def get_escalation(escalation_id):
    """Full detail view for a single escalation, including the chat's message history."""
    esc = Escalation.query.get_or_404(escalation_id)
    session = ChatSession.query.get(esc.session_id)
    review = Review.query.get(esc.review_id) if esc.review_id else None
    customer = Customer.query.get(session.customer_id) if session else None

    messages = [
        {"sender": m.sender, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in sorted(session.messages, key=lambda m: m.created_at)
    ] if session else []

    return jsonify({
        "escalation_id": esc.id,
        "ticket_number": _ticket_number(esc),
        "status": esc.status,
        "reason": esc.reason,
        "source": esc.source,
        "assigned_to": esc.assigned_to,
        "customer_account": customer.account_number if customer else None,
        "session_id": session.id if session else None,
        "complaint_type": session.complaint_type if session else None,
        "messages": messages,
        "review_text": review.review_text if review else None,
        "sentiment_label": review.sentiment_label if review else None,
        "sentiment_score": review.sentiment_score if review else None,
    }), 200


@escalations_bp.route("/<int:escalation_id>/status", methods=["PATCH"])
def update_status(escalation_id):
    """Agent updates escalation status as they work the case."""
    esc = Escalation.query.get_or_404(escalation_id)
    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in ("open", "in_progress", "closed"):
        return jsonify({"error": "status must be open, in_progress, or closed"}), 400

    session = ChatSession.query.get(esc.session_id)
    esc.status = new_status
    if session:
        session.session_status = "escalated" if new_status != "closed" else "resolved"
        if new_status == "closed":
            session.ended_at = datetime.utcnow()
            session.closure_confirmed = False
        else:
            session.ended_at = None
    db.session.commit()

    return jsonify({
        "escalation_id": esc.id,
        "ticket_number": _ticket_number(esc),
        "status": esc.status,
    }), 200


@escalations_bp.route("/<int:escalation_id>/reply", methods=["POST"])
def reply_to_customer(escalation_id):
    """Send a 1-to-1 human-agent message into the customer's escalation conversation."""
    esc = Escalation.query.get_or_404(escalation_id)
    if esc.status == "closed":
        return jsonify({"error": "This case is closed."}), 409

    data = request.get_json() or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400
    if len(content) > 2000:
        return jsonify({"error": "Message is too long."}), 400

    session = ChatSession.query.get_or_404(esc.session_id)
    msg = Message(session_id=session.id, sender="agent", content=content)
    db.session.add(msg)
    esc.status = "in_progress"
    esc.acknowledged_at = esc.acknowledged_at or datetime.utcnow()
    esc.assigned_to = g.admin.name or g.admin.username
    session.session_status = "escalated"
    session.ended_at = None
    session.last_activity_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "ok": True,
        "escalation_id": esc.id,
        "ticket_number": _ticket_number(esc),
        "assigned_to": esc.assigned_to,
        "message": {
            "sender": "agent",
            "content": content,
            "created_at": msg.created_at.isoformat(),
        }
    }), 201


@escalations_bp.route("/notifications", methods=["GET"])
def notifications():
    """Open escalations no agent has acknowledged yet (drives the agent alert badge)."""
    pending = (Escalation.query.filter_by(status="open", acknowledged_at=None)
               .order_by(Escalation.created_at.desc()).all())
    return jsonify({
        "count": len(pending),
        "latest": [{"escalation_id": e.id, "ticket_number": _ticket_number(e), "reason": e.reason, "source": e.source,
                    "created_at": e.created_at.isoformat()} for e in pending[:5]],
    }), 200


@escalations_bp.route("/<int:escalation_id>/acknowledge", methods=["POST"])
def acknowledge(escalation_id):
    esc = Escalation.query.get_or_404(escalation_id)
    if not esc.acknowledged_at:
        esc.acknowledged_at = datetime.utcnow()
        esc.assigned_to = g.admin.name or g.admin.username
        db.session.commit()
    return jsonify({"escalation_id": esc.id, "assigned_to": esc.assigned_to}), 200
