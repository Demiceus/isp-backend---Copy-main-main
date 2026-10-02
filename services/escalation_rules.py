# services/escalation_rules.py - decides when the AI should hand off to a human agent
import re
from app.models import Message

HUMAN_REQUEST = re.compile(
    r"\b(human|real person|live agent|agent|representative|supervisor|manager|technician|talk to someone|speak to someone)\b",
    re.I,
)
MAX_CUSTOMER_MESSAGES = 6  # still unresolved after this many customer messages


def detect_human_needed(session, content):
    """Return a short reason string if a human agent is needed, else None."""
    if HUMAN_REQUEST.search(content):
        return "customer asked for a human agent"

    count = Message.query.filter_by(session_id=session.id, sender="customer").count()
    if count >= MAX_CUSTOMER_MESSAGES:
        return "issue still unresolved after %d messages" % count

    if count >= 3:
        try:
            from services.sentiment import score_sentiment
            label, conf = score_sentiment(content)
            if label == "negative" and conf >= 0.8:
                return "customer frustrated (strong negative sentiment)"
        except Exception:
            pass
    return None
