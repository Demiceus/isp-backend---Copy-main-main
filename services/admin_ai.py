import requests
from collections import Counter

from app.models import (
    Customer,
    ChatSession,
    Review,
    Escalation,
)


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3"


def get_admin_statistics():
    """
    Collect real statistics from the NetAssist AI database.
    """

    total_customers = Customer.query.count()

    total_sessions = ChatSession.query.count()

    unresolved_complaints = ChatSession.query.filter_by(
        session_status="unresolved"
    ).count()

    resolved_complaints = ChatSession.query.filter_by(
        session_status="resolved"
    ).count()

    total_reviews = Review.query.count()

    positive_reviews = Review.query.filter_by(
        sentiment_label="positive"
    ).count()

    neutral_reviews = Review.query.filter_by(
        sentiment_label="neutral"
    ).count()

    negative_reviews = Review.query.filter_by(
        sentiment_label="negative"
    ).count()

    total_escalations = Escalation.query.count()

    open_escalations = Escalation.query.filter_by(
        status="open"
    ).count()

    return {
        "customers": total_customers,
        "total_sessions": total_sessions,
        "unresolved_complaints": unresolved_complaints,
        "resolved_complaints": resolved_complaints,
        "total_reviews": total_reviews,
        "positive_reviews": positive_reviews,
        "neutral_reviews": neutral_reviews,
        "negative_reviews": negative_reviews,
        "total_escalations": total_escalations,
        "open_escalations": open_escalations,
    }


# ==========================================================
# COMPLAINT ANALYTICS
# ==========================================================

def get_complaint_statistics():
    """
    Count chat sessions by complaint category.

    The category comes from ChatSession.complaint_type,
    which is populated by the complaint classifier.
    """

    sessions = (
        ChatSession.query
        .filter(
            ChatSession.complaint_type.isnot(None),
            ChatSession.complaint_type != ""
        )
        .all()
    )

    counts = Counter(
        session.complaint_type
        for session in sessions
    )

    return dict(
        sorted(
            counts.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )


def get_complaint_category_count(category):
    """
    Return the number of sessions belonging to a
    complaint category (a string) or a group of
    categories (a list).
    """

    if isinstance(category, list):
        return ChatSession.query.filter(
            ChatSession.complaint_type.in_(category)
        ).count()

    return ChatSession.query.filter_by(
        complaint_type=category
    ).count()


def get_top_complaint_category():
    """
    Return the complaint category with the highest
    number of sessions.
    """

    complaint_statistics = get_complaint_statistics()

    if not complaint_statistics:
        return None, 0

    category, count = next(
        iter(complaint_statistics.items())
    )

    return category, count


# ==========================================================
# QUESTION IDENTIFICATION
# ==========================================================

def identify_admin_question(question: str):
    """
    Identify which database statistic the administrator
    is asking about.
    """

    text = question.lower().strip()

    # ------------------------------------------------------
    # TOP COMPLAINT CATEGORY
    # ------------------------------------------------------

    if (
        ("most" in text or "highest" in text)
        and (
            "complaint" in text
            or "issue" in text
        )
    ):
        return "top_complaint_category"

    # ------------------------------------------------------
    # COMPLAINT CATEGORY BREAKDOWN
    # ------------------------------------------------------

    if (
        "complaints by category" in text
        or "complaint breakdown" in text
        or "complaint categories" in text
        or "complaint types" in text
        or "complaints per category" in text
    ):
        return "complaint_categories"

    # ------------------------------------------------------
    # SPECIFIC COMPLAINT TYPES
    # ------------------------------------------------------

    complaint_categories = [
        "slow_internet",
        "no_internet",
        "intermittent_connection",
        "router_modem",
        "service_outage",
        "billing",
        "installation",
        "plan_change",
        "technical_support",
        "account",
    ]

    category_aliases = {
        "slow internet": "slow_internet",
        "slow connection": "slow_internet",

        "no internet": "no_internet",
        "no connection": "no_internet",

        "intermittent connection": "intermittent_connection",
        "intermittent internet": "intermittent_connection",

        "router": "router_modem",
        "modem": "router_modem",
        "router modem": "router_modem",

        "outage": "service_outage",
        "service outage": "service_outage",

        "billing": "billing",
        "bill": "billing",

        "installation": "installation",
        "install": "installation",

        "plan change": "plan_change",
        "change plan": "plan_change",

        "technical support": "technical_support",
        "technical": "technical_support",

        "account issue": "account",
        "account problem": "account",
    }

    for alias, category in category_aliases.items():
        if alias in text:
            return {
                "type": "complaint_category",
                "category": category,
            }

    # Generic connection wording -> all connection categories
    if any(w in text for w in ("internet", "connection", "connectivity")):
        return {
            "type": "complaint_category",
            "category": [
                "slow_internet",
                "no_internet",
                "intermittent_connection",
            ],
        }

    # ------------------------------------------------------
    # SENTIMENT / REVIEWS
    # ------------------------------------------------------

    if (
        "negative review" in text
        or "negative feedback" in text
    ):
        return "negative_reviews"

    if (
        "positive review" in text
        or "positive feedback" in text
    ):
        return "positive_reviews"

    if (
        "neutral review" in text
        or "neutral feedback" in text
    ):
        return "neutral_reviews"

    if (
        "total review" in text
        or "reviews" in text
        or "feedback" in text
    ):
        return "total_reviews"

    # ------------------------------------------------------
    # ESCALATIONS
    # ------------------------------------------------------

    if "open escalation" in text:
        return "open_escalations"

    if "total escalation" in text or "escalations" in text:
        return "total_escalations"

    # ------------------------------------------------------
    # COMPLAINT STATUS
    # ------------------------------------------------------

    if (
        "unresolved complaint" in text
        or "unresolved complaints" in text
        or "unresolved" in text
    ):
        return "unresolved_complaints"

    if (
        "resolved complaint" in text
        or "resolved complaints" in text
        or "resolved" in text
    ):
        return "resolved_complaints"

    # ------------------------------------------------------
    # CUSTOMERS
    # ------------------------------------------------------

    if (
        "customer" in text
        or "customers" in text
        or "accounts" in text
    ):
        return "customers"

    # ------------------------------------------------------
    # CHAT SESSIONS
    # ------------------------------------------------------

    if (
        "chat session" in text
        or "chat sessions" in text
        or "sessions" in text
    ):
        return "total_sessions"

    return None


# ==========================================================
# LLAMA RESPONSE
# ==========================================================

def generate_admin_answer(
    question: str,
    statistic_name: str,
    value
):
    """
    Use Llama 3 to turn verified database information
    into a natural-language administrative response.
    """

    prompt = f"""
You are the administrative assistant for NetAssist AI.

Answer the administrator's question using ONLY the
verified database information provided below.

Administrator question:
{question}

Verified database information:
{statistic_name} = {value}

Rules:
- Do not invent numbers.
- Do not change any verified values.
- Do not claim information that is not provided.
- Give a concise and professional answer.
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a database-grounded "
                            "administrative assistant for "
                            "an ISP customer service system."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()

        return response.json()["message"]["content"]

    except requests.RequestException as e:
        print(f"Admin AI Ollama error: {e}")

        return (
            "The verified database information is: "
            f"{value}"
        )


# ==========================================================
# ADMIN AI
# ==========================================================

def ask_admin_ai(question: str):
    """
    Process an administrator's question using
    verified database information.
    """

    statistics = get_admin_statistics()

    identified = identify_admin_question(question)

    # ------------------------------------------------------
    # UNKNOWN QUESTION
    # ------------------------------------------------------

    if identified is None:
        return {
            "success": False,
            "answer": (
                "I can currently answer questions about "
                "customers, chat sessions, complaint status, "
                "complaint categories, reviews, sentiment, "
                "and escalations."
            ),
            "data": None,
        }

    # ------------------------------------------------------
    # SPECIFIC COMPLAINT CATEGORY
    # ------------------------------------------------------

    if isinstance(identified, dict):

        if identified["type"] == "complaint_category":

            category = identified["category"]

            value = get_complaint_category_count(
                category
            )

            answer = generate_admin_answer(
                question,
                category,
                value
            )

            return {
                "success": True,
                "answer": answer,
                "data": {
                    "metric": "complaint_category",
                    "category": category,
                    "value": value,
                },
            }

    # ------------------------------------------------------
    # COMPLAINT CATEGORY BREAKDOWN
    # ------------------------------------------------------

    if identified == "complaint_categories":

        complaint_statistics = get_complaint_statistics()

        answer = generate_admin_answer(
            question,
            "complaint_categories",
            complaint_statistics
        )

        return {
            "success": True,
            "answer": answer,
            "data": {
                "metric": "complaint_categories",
                "values": complaint_statistics,
            },
        }

    # ------------------------------------------------------
    # TOP COMPLAINT CATEGORY
    # ------------------------------------------------------

    if identified == "top_complaint_category":

        category, value = get_top_complaint_category()

        if category is None:
            return {
                "success": True,
                "answer": (
                    "There are currently no classified "
                    "complaints in the database."
                ),
                "data": {
                    "metric": "top_complaint_category",
                    "category": None,
                    "value": 0,
                },
            }

        answer = generate_admin_answer(
            question,
            "top_complaint_category",
            {
                "category": category,
                "count": value,
            }
        )

        return {
            "success": True,
            "answer": answer,
            "data": {
                "metric": "top_complaint_category",
                "category": category,
                "value": value,
            },
        }

    # ------------------------------------------------------
    # NORMAL STATISTICS
    # ------------------------------------------------------

    value = statistics[identified]

    answer = generate_admin_answer(
        question,
        identified,
        value
    )

    return {
        "success": True,
        "answer": answer,
        "data": {
            "metric": identified,
            "value": value,
        },
    }