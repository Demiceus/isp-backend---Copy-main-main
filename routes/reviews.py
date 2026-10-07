from flask import Blueprint, request, jsonify, g
from datetime import datetime

from app.models import (
    db,
    Customer,
    Review,
    ChatSession,
    Escalation
)

from services.sentiment import score_sentiment


reviews_bp = Blueprint("reviews", __name__)


def find_matching_session(customer_id):
    """
    Find the customer's most recent chat session that can be associated
    with a customer review.

    A review may be submitted after the chat has already been escalated,
    so do not restrict this to only "unresolved" sessions.
    """
    return (
        ChatSession.query
        .filter(
            ChatSession.customer_id == customer_id,
            ChatSession.session_status.in_([
                "unresolved",
                "escalated",
                "resolved",
            ]),
        )
        .order_by(ChatSession.started_at.desc())
        .first()
    )

@reviews_bp.route("/", methods=["POST"])
def submit_review():

    data = request.get_json() or {}

    review_text = data.get("review_text", "").strip()

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    if not review_text:
        return jsonify({
            "error": "review_text is required"
        }), 400

    # ---------------------------------------------------------
    # FIND CUSTOMER
    # ---------------------------------------------------------

    customer = g.customer  # authenticated account

    # ---------------------------------------------------------
    # ML SENTIMENT ANALYSIS
    # ---------------------------------------------------------

    sentiment, confidence = score_sentiment(review_text)

    # ---------------------------------------------------------
    # FIND RELATED CHAT SESSION
    # ---------------------------------------------------------

    session = find_matching_session(customer.id)

    matched_session_id = None

    if session:
        matched_session_id = session.id

    # ---------------------------------------------------------
    # SAVE REVIEW
    # ---------------------------------------------------------

    review = Review(
        customer_id=customer.id,
        review_text=review_text,
        sentiment_label=sentiment,
        sentiment_score=confidence,
        matched_session_id=matched_session_id
    )

    db.session.add(review)
    db.session.flush()

    # ---------------------------------------------------------
    # POSITIVE REVIEW
    # ---------------------------------------------------------

    if sentiment == "positive":

        if not session:

            db.session.commit()

            return jsonify({
                "status": "positive",
                "sentiment": sentiment,
                "confidence": confidence,
                "message": (
                    "Thank you for your positive feedback."
                ),
                "resolved": False,
                "escalated": False
            }), 201

        # Check whether this session was already escalated.
        existing_escalation = Escalation.query.filter_by(
            session_id=session.id
        ).first()

        if existing_escalation:

            # IMPORTANT:
            # Do not automatically cancel an existing escalation
            # just because the customer later gives a positive review.

            db.session.commit()

            return jsonify({
                "status": "positive",
                "sentiment": sentiment,
                "confidence": confidence,
                "message": (
                    "Thank you for your feedback. "
                    "Your previous support request remains with "
                    "a human support agent."
                ),
                "resolved": False,
                "escalated": True,
                "escalation_id": existing_escalation.id
            }), 201

        # No escalation exists.
        # Positive feedback means the issue can be considered resolved.

        session.closure_confirmed = True
        session.session_status = "resolved"
        session.ended_at = session.ended_at or datetime.utcnow()

        db.session.commit()

        return jsonify({
            "status": "resolved",
            "sentiment": sentiment,
            "confidence": confidence,
            "message": (
                "Thank you for your feedback. "
                "Your issue has been marked as resolved."
            ),
            "resolved": True,
            "escalated": False,
            "session_id": session.id
        }), 201

    # ---------------------------------------------------------
    # NEGATIVE REVIEW
    # ---------------------------------------------------------

    if sentiment == "negative":

        if not session:

            db.session.commit()

            return jsonify({
                "status": "negative",
                "sentiment": sentiment,
                "confidence": confidence,
                "message": (
                    "Thank you for your feedback. "
                    "There is no active unresolved session to escalate."
                ),
                "resolved": False,
                "escalated": False
            }), 201

        # Check for an existing escalation.
        existing_escalation = Escalation.query.filter_by(
            session_id=session.id
        ).first()

        if existing_escalation:

            # Attach the customer review to the existing escalation
            # if that escalation does not already have a review.
            if existing_escalation.review_id is None:
                existing_escalation.review_id = review.id

            session.session_status = "escalated"
            session.ended_at = None

            db.session.commit()

            return jsonify({
                "status": "negative",
                "sentiment": sentiment,
                "confidence": confidence,
                "message": (
                    "Your review has been attached to your "
                    "human support case."
                ),
                "resolved": False,
                "escalated": True,
                "escalation_id": existing_escalation.id,
                "ticket_number": f"NA-CASE-{existing_escalation.id:06d}",
                "session_id": session.id
            }), 201

        # Create new escalation.

        escalation = Escalation(
            session_id=session.id,
            review_id=review.id,
            reason="negative customer review",
            source="negative_review",
            status="open"
        )

        db.session.add(escalation)

        session.session_status = "escalated"
        session.ended_at = None

        db.session.commit()

        return jsonify({
            "status": "escalated",
            "sentiment": sentiment,
            "confidence": confidence,
            "message": (
                "We're sorry that your issue has not been resolved. "
                "Your concern has been forwarded to a human support agent."
            ),
            "resolved": False,
            "escalated": True,
            "escalation_id": escalation.id,
            "ticket_number": f"NA-CASE-{escalation.id:06d}",
            "session_id": session.id
        }), 201

    # ---------------------------------------------------------
    # NEUTRAL REVIEW
    # ---------------------------------------------------------

    if sentiment == "neutral":

        db.session.commit()

        return jsonify({
            "status": "pending",
            "sentiment": sentiment,
            "confidence": confidence,
            "message": (
                "Thank you for your feedback. "
                "Your concern remains pending and has not been "
                "marked as resolved."
            ),
            "resolved": False,
            "escalated": False,
            "session_id": matched_session_id
        }), 201

    # ---------------------------------------------------------
    # UNEXPECTED SENTIMENT
    # ---------------------------------------------------------

    db.session.commit()

    return jsonify({
        "status": "pending",
        "sentiment": sentiment,
        "confidence": confidence,
        "message": "Your feedback has been recorded.",
        "resolved": False,
        "escalated": False
    }), 201


@reviews_bp.route("/public", methods=["GET"])
def public_reviews():
    """Read-only feed for the landing page: latest positive/neutral reviews, first name only."""
    rows = (
        Review.query.filter(Review.sentiment_label.in_(["positive", "neutral"]))
        .order_by(Review.created_at.desc()).limit(6).all()
    )
    out = []
    for r in rows:
        c = Customer.query.get(r.customer_id)
        first = (c.name or "").split(" ")[0] if c and c.name else "NetAssist customer"
        out.append({"name": first, "text": r.review_text[:280],
                    "sentiment": r.sentiment_label, "created_at": r.created_at.isoformat()})
    return jsonify(out), 200
