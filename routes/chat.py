from flask import Blueprint, request, jsonify, Response, stream_with_context, g
from datetime import datetime, timedelta

from app.models import (
    db,
    ChatSession,
    Message,
    Escalation,
    MLFeedback,
)

from services.classifier import classify_complaint
from services.escalation_rules import detect_human_needed

from services.services import (
    get_ai_reply,
    get_ai_reply_stream,
    is_rate_limited,
    check_and_mark_stale,
)

chat_bp = Blueprint("chat", __name__)

def _ticket_number(escalation):
    return f"NA-CASE-{escalation.id:06d}"


def _active_escalation(session):
    return Escalation.query.filter(
        Escalation.session_id == session.id,
        Escalation.status.in_(["open", "in_progress"])
    ).order_by(Escalation.created_at.desc()).first()


@chat_bp.route("/history", methods=["GET"])
def chat_history():
    customer = g.customer  # authenticated account

    msgs = (
        Message.query
        .join(ChatSession, Message.session_id == ChatSession.id)
        .filter(ChatSession.customer_id == customer.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    latest = (
        ChatSession.query
        .filter_by(customer_id=customer.id)
        .order_by(ChatSession.id.desc())
        .first()
    )

    active_escalation = _active_escalation(latest) if latest else None

    return jsonify({
        "latest_session_id": latest.id if latest else None,
        "latest_session_ended": bool(latest and latest.ended_at),
        "latest_session_status": latest.session_status if latest else None,
        "latest_escalation": ({
            "escalation_id": active_escalation.id,
            "ticket_number": _ticket_number(active_escalation),
            "status": active_escalation.status,
            "reason": active_escalation.reason,
            "source": active_escalation.source,
            "assigned_to": active_escalation.assigned_to,
            "created_at": active_escalation.created_at.isoformat(),
        } if active_escalation else None),
        "messages": [
            {
                "sender": m.sender,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }), 200

@chat_bp.route("/", methods=["GET"])
def chat_home():
    return jsonify({
        "status": "ok",
        "message": "NetAssist AI Chat API is running",
        "endpoints": {
            "start": "POST /api/chat/start",
            "message": "POST /api/chat/<session_id>/message",
            "confirm_closure": "POST /api/chat/<session_id>/confirm-closure"
        }
    }), 200


@chat_bp.route("/start", methods=["POST"])
def start_session():
    data = request.get_json() or {}

    complaint_type = data.get("complaint_type")
    customer = g.customer  # authenticated account

    # Backdate activity slightly so the customer's first message
    # (sent right after the session starts) is not rate limited.
    session = ChatSession(
        customer_id=customer.id,
        complaint_type=complaint_type,
        last_activity_at=datetime.utcnow() - timedelta(seconds=30)
    )

    db.session.add(session)
    db.session.commit()

    return jsonify({
        "session_id": session.id,
        "status": "unresolved"
    }), 201


@chat_bp.route("/<int:session_id>/message", methods=["POST"])
def send_message(session_id):
    session = ChatSession.query.get_or_404(session_id)

    # Check whether the session has become inactive
    check_and_mark_stale(session)

    if session.ended_at:
        return jsonify({
            "error": "This session has ended. Please start a new one."
        }), 409

    if is_rate_limited(session):
        return jsonify({
            "error": "Please wait a moment before sending another message."
        }), 429

    data = request.get_json() or {}

    content = data.get("content", "").strip()

    if not content:
        return jsonify({
            "error": "content is required"
        }), 400

    # --------------------------------------------------
    # 1. CLASSIFY CUSTOMER COMPLAINT
    # --------------------------------------------------

    classification = classify_complaint(content)

    category = classification["category"]
    confidence = classification["confidence"]

    # --------------------------------------------------
    # 2. SAVE CUSTOMER MESSAGE
    # --------------------------------------------------

    customer_msg = Message(
    session_id=session.id,
    sender="customer",
    content=content
    )

    db.session.add(customer_msg)
    db.session.flush()  
    
    feedback = MLFeedback(
    message_id=customer_msg.id,
    predicted_category=category,
    confidence=confidence
)

    db.session.add(feedback)

    # Update detected complaint category
    session.complaint_type = category
    session.last_activity_at = datetime.utcnow()

    db.session.commit()

    # --------------------------------------------------
    # 3. GENERATE AI RESPONSE
    # --------------------------------------------------

    active_escalation = _active_escalation(session)
    handoff = detect_human_needed(session, content) if not active_escalation else None
    escalated_now = False

    if active_escalation:
        # Once a case is handed to a human, customer messages go directly
        # into the same 1-to-1 case instead of being answered by Ollama.
        reply_text = "Your message has been sent to your human support agent."
    elif handoff:
        escalation = Escalation(
            session_id=session.id,
            reason="AI detected: " + handoff,
            source="ai_detected",
            status="open"
        )
        db.session.add(escalation)
        session.session_status = "escalated"
        db.session.commit()
        escalated_now = True
        reply_text = (
            "I'm connecting you with a human support agent. "
            "They have been notified and will review your case."
        )
    else:
        reply_text = get_ai_reply(session)

    # --------------------------------------------------
    # 4. SAVE BOT RESPONSE
    # --------------------------------------------------

    bot_msg = Message(
        session_id=session.id,
        sender="bot",
        content=reply_text
    )

    db.session.add(bot_msg)

    session.last_activity_at = datetime.utcnow()

    db.session.commit()

    escalation = _active_escalation(session)
    return jsonify({
        "reply": reply_text,
        "category": category,
        "confidence": confidence,
        "session_status": session.session_status,
        "escalated": bool(escalation),
        "escalation": ({
            "escalation_id": escalation.id,
            "ticket_number": _ticket_number(escalation),
            "status": escalation.status,
            "assigned_to": escalation.assigned_to,
        } if escalation else None)
    }), 200
    
@chat_bp.route("/<int:session_id>/message/stream", methods=["POST"])
def send_message_stream(session_id):
    session = ChatSession.query.get_or_404(session_id)

    check_and_mark_stale(session)

    if session.ended_at:
        return jsonify({
            "error": "This session has ended. Please start a new one."
        }), 409

    if is_rate_limited(session):
        return jsonify({
            "error": "Please wait a moment before sending another message."
        }), 429

    data = request.get_json() or {}

    content = data.get("content", "").strip()

    if not content:
        return jsonify({
            "error": "content is required"
        }), 400

    # --------------------------------------------------
    # 1. CLASSIFY CUSTOMER COMPLAINT
    # --------------------------------------------------

    classification = classify_complaint(content)

    category = classification["category"]
    confidence = classification["confidence"]

    # --------------------------------------------------
    # 2. SAVE CUSTOMER MESSAGE
    # --------------------------------------------------

    customer_msg = Message(
        session_id=session.id,
        sender="customer",
        content=content
    )

    db.session.add(customer_msg)

    # Flush so customer_msg.id is available
    db.session.flush()

    # --------------------------------------------------
    # 3. SAVE ML FEEDBACK
    # --------------------------------------------------

    feedback = MLFeedback(
        message_id=customer_msg.id,
        predicted_category=category,
        confidence=confidence
    )

    db.session.add(feedback)

    # --------------------------------------------------
    # 4. UPDATE SESSION
    # --------------------------------------------------

    session.complaint_type = category
    session.last_activity_at = datetime.utcnow()

    db.session.commit()

    # --------------------------------------------------
    # 5. CHECK HUMAN ESCALATION
    # --------------------------------------------------

    active_escalation = _active_escalation(session)

    handoff = (
        detect_human_needed(session, content)
        if not active_escalation
        else None
    )

    # --------------------------------------------------
    # 6. CREATE ESCALATION IF NEEDED
    # --------------------------------------------------

    if handoff and not active_escalation:

        active_escalation = Escalation(
            session_id=session.id,
            reason="AI detected: " + handoff,
            source="ai_detected",
            status="open"
        )

        db.session.add(active_escalation)

        session.session_status = "escalated"

        db.session.commit()

    # --------------------------------------------------
    # 7. STREAM RESPONSE
    # --------------------------------------------------

    def generate():

        full_reply = ""

        if active_escalation:

            reply = (
                "I'm connecting you with a human support agent. "
                "They have been notified and will review your case."
                if handoff
                else
                "Your message has been sent to your human support agent."
            )

            # Stream the handoff response in small chunks
            words = reply.split(" ")

            for i, word in enumerate(words):

                chunk = word + (
                    " "
                    if i < len(words) - 1
                    else ""
                )

                full_reply += chunk

                yield chunk

        else:

            for chunk in get_ai_reply_stream(session):

                full_reply += chunk

                yield chunk

        # --------------------------------------------------
        # 8. SAVE BOT RESPONSE
        # --------------------------------------------------

        db.session.add(
            Message(
                session_id=session.id,
                sender="bot",
                content=full_reply
            )
        )

        session.last_activity_at = datetime.utcnow()

        db.session.commit()

    # --------------------------------------------------
    # 9. RETURN STREAM
    # --------------------------------------------------

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@chat_bp.route("/<int:session_id>/status", methods=["GET"])
def session_status(session_id):
    session = ChatSession.query.get_or_404(session_id)
    escalation = _active_escalation(session)
    return jsonify({
        "session_id": session.id,
        "session_status": session.session_status,
        "ended": bool(session.ended_at),
        "escalation": ({
            "escalation_id": escalation.id,
            "ticket_number": _ticket_number(escalation),
            "status": escalation.status,
            "reason": escalation.reason,
            "source": escalation.source,
            "assigned_to": escalation.assigned_to,
            "created_at": escalation.created_at.isoformat(),
        } if escalation else None)
    }), 200

@chat_bp.route("/<int:session_id>/confirm-closure", methods=["POST"])
def confirm_closure(session_id):
    session = ChatSession.query.get_or_404(session_id)

    # Do not allow confirmation on an already ended session
    if session.ended_at:
        return jsonify({
            "error": "This session has already ended."
        }), 409

    data = request.get_json() or {}

    resolved = data.get("resolved")

    # --------------------------------------------------
    # VALIDATE YES / NO RESPONSE
    # --------------------------------------------------

    if not isinstance(resolved, bool):
        return jsonify({
            "error": "resolved must be true (YES) or false (NO)"
        }), 400

    # --------------------------------------------------
    # YES → RESOLVED
    # --------------------------------------------------

    if resolved is True:

        session.closure_confirmed = True
        session.session_status = "resolved"
        session.ended_at = datetime.utcnow()

        active_escalation = _active_escalation(session)
        if active_escalation:
            active_escalation.status = "closed"

        db.session.commit()

        return jsonify({
            "status": "resolved",
            "message": "Thank you for confirming. Your issue has been marked as resolved.",
            "escalated": False,
            "ticket_number": _ticket_number(active_escalation) if active_escalation else None
        }), 200

    # --------------------------------------------------
    # NO → ESCALATION
    # --------------------------------------------------

    session.closure_confirmed = False
    session.session_status = "escalated"
    # Keep the session open so the customer and assigned agent can continue
    # the same 1-to-1 conversation.
    session.ended_at = None

    # Check if an escalation already exists
    existing_escalation = Escalation.query.filter_by(
        session_id=session.id
    ).first()

    if existing_escalation:
        session.session_status = "escalated"
        db.session.commit()
        return jsonify({
            "status": "escalated",
            "message": "Your issue has been forwarded to a human support agent.",
            "escalated": True,
            "escalation_id": existing_escalation.id,
            "ticket_number": _ticket_number(existing_escalation)
        }), 200

    # Create new escalation
    escalation = Escalation(
        session_id=session.id,
        reason="customer confirmed issue is unresolved",
        source="customer_request",
        status="open"
    )

    db.session.add(escalation)
    db.session.commit()

    return jsonify({
        "status": "unresolved",
        "message": "Your issue will be forwarded to a human support agent.",
        "escalated": True,
        "escalation_id": escalation.id
    }), 200
    
    