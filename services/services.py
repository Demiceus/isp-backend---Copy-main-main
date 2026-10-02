# services.py
import requests
import json
from datetime import datetime, timedelta

from app.config import Config
from app.models import db, ChatSession, Message, Review

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3"

SYSTEM_PROMPT = (
    "You are a customer service assistant for an internet service provider (ISP). "
    "You may ONLY help with: connectivity issues, billing questions, outages, "
    "router troubleshooting, and account/plan questions. "
    "If the customer asks about anything outside these topics, politely redirect "
    "them back to ISP-related support. Do not answer general knowledge questions, "
    "give unrelated advice, or role-play as anything else. "
    "When the issue seems resolved, ask the customer to confirm before ending the chat."
)


# ==========================================================
# ORIGINAL AI RESPONSE
# KEEP THIS
# ==========================================================

def get_ai_reply(session: ChatSession) -> str:
    history = (
        Message.query
        .filter_by(session_id=session.id)
        .order_by(Message.created_at.desc())
        .limit(Config.MAX_HISTORY_MESSAGES)
        .all()
    )

    history.reverse()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in history:
        role = "user" if msg.sender == "customer" else "assistant"

        messages.append({
            "role": role,
            "content": msg.content
        })

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False
            },
            timeout=120,
        )

        response.raise_for_status()

        return response.json()["message"]["content"]

    except requests.RequestException as e:
        print(f"Ollama error: {e}")

        return "I'm having trouble connecting right now. Please try again shortly."


# ==========================================================
# NEW STREAMING AI RESPONSE
# ==========================================================

def get_ai_reply_stream(session: ChatSession):

    history = (
        Message.query
        .filter_by(session_id=session.id)
        .order_by(Message.created_at.desc())
        .limit(Config.MAX_HISTORY_MESSAGES)
        .all()
    )

    history.reverse()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in history:
        role = "user" if msg.sender == "customer" else "assistant"

        messages.append({
            "role": role,
            "content": msg.content
        })

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": True
            },
            stream=True,
            timeout=120,
        )

        response.raise_for_status()

        for line in response.iter_lines():

            if line:
                chunk = json.loads(line)

                if "message" in chunk:

                    content = chunk["message"].get("content", "")

                    if content:
                        yield content

                if chunk.get("done"):
                    break

    except requests.RequestException as e:

        print(f"Ollama error: {e}")

        yield "I'm having trouble connecting right now. Please try again shortly."


# ==========================================================
# RATE LIMITING
# ==========================================================

MIN_SECONDS_BETWEEN_MESSAGES = 2


def is_rate_limited(session: ChatSession) -> bool:

    if not session.last_activity_at:
        return False

    elapsed = datetime.utcnow() - session.last_activity_at

    return elapsed < timedelta(
        seconds=MIN_SECONDS_BETWEEN_MESSAGES
    )


# ==========================================================
# STALE SESSION CHECK
# ==========================================================

def check_and_mark_stale(session: ChatSession):

    if session.closure_confirmed or session.ended_at:
        return False

    stale_cutoff = datetime.utcnow() - timedelta(
        minutes=Config.SESSION_STALE_MINUTES
    )

    if session.last_activity_at < stale_cutoff:

        session.session_status = "unresolved"
        session.ended_at = datetime.utcnow()

        db.session.commit()

        return True

    return False