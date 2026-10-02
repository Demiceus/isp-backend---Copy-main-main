"""
Dummy data for NetAssist AI.

    python seed.py            add demo data (skips anything that already exists)
    python seed.py --reset    DROP ALL TABLES, recreate them, then add demo data

Demo logins (change these before any real use):
    Admin    admin / admin123        Agent  agent1 / agent123
    Customer NA-100001 ... NA-100010  PIN 1234      (NA-100011 / NA-100012 are pending approval)
"""
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import db, Customer, AdminUser, ChatSession, Message, Review, Escalation

CUSTOMERS = [
    ("NA-100001", "Maria Santos", "maria@example.com", "active"),
    ("NA-100002", "John Reyes", "john@example.com", "active"),
    ("NA-100003", "Ana Cruz", "ana@example.com", "active"),
    ("NA-100004", "Carlo Mendoza", "carlo@example.com", "active"),
    ("NA-100005", "Liza Garcia", "liza@example.com", "active"),
    ("NA-100006", "Mark Villanueva", "mark@example.com", "active"),
    ("NA-100007", "Grace Lim", "grace@example.com", "active"),
    ("NA-100008", "Paolo Ramos", "paolo@example.com", "active"),
    ("NA-100009", "Nina Torres", "nina@example.com", "active"),
    ("NA-100010", "Rico Bautista", "rico@example.com", "active"),
    ("NA-100011", "Dana Flores", "dana@example.com", "pending"),
    ("NA-100012", "Eli Navarro", "eli@example.com", "pending"),
]

# (account, complaint_type, status, [customer message, bot reply], days_ago)
SESSIONS = [
    ("NA-100001", "slow_internet", "unresolved", ["My internet is very slow tonight.", "Please restart your router and run a speed test."], 0),
    ("NA-100002", "no_internet", "unresolved", ["No internet since this morning.", "Check that the modem lights are on."], 0),
    ("NA-100003", "no_internet", "unresolved", ["Internet is down again.", "Sorry about that. Is the LOS light red?"], 1),
    ("NA-100004", "service_outage", "unresolved", ["Is there an outage in my area?", "We are checking for outages in your area."], 1),
    ("NA-100005", "billing", "resolved", ["I was charged twice this month.", "I have flagged the duplicate charge for review."], 2),
    ("NA-100006", "intermittent_connection", "unresolved", ["Connection keeps dropping every few minutes.", "Try a different Ethernet cable."], 2),
    ("NA-100007", "router_modem", "resolved", ["Router keeps rebooting.", "A firmware update should fix this."], 3),
    ("NA-100008", "slow_internet", "unresolved", ["Speeds are far below my plan.", "Let's run diagnostics on your line."], 4),
    ("NA-100009", "installation", "resolved", ["When is my installation?", "Installation is scheduled this Friday."], 5),
    ("NA-100010", "plan_change", "resolved", ["I want to upgrade my plan.", "I can help you upgrade to a faster plan."], 6),
    ("NA-100002", "intermittent_connection", "unresolved", ["It disconnects again!", "Sorry. Let's escalate this."], 3),
]

# (account, text, label, score, days_ago)
REVIEWS = [
    ("NA-100005", "Support fixed my billing issue quickly. Very helpful and polite.", "positive", 0.92, 1),
    ("NA-100007", "The new router works great. Thank you NetAssist!", "positive", 0.95, 2),
    ("NA-100009", "Installation was on time and the technician was professional.", "positive", 0.9, 4),
    ("NA-100010", "Upgrading my plan was easy. Speeds are much better now.", "positive", 0.88, 5),
    ("NA-100001", "Service is okay, though it has been a bit slow lately.", "neutral", 0.6, 1),
    ("NA-100004", "Internet works most of the time. Support answers fine.", "neutral", 0.58, 3),
    ("NA-100002", "Internet keeps disconnecting and nothing gets fixed. Terrible.", "negative", 0.93, 0),
    ("NA-100006", "Very frustrating. Connection drops all day.", "negative", 0.9, 2),
]


def ago(days, hours=0):
    return datetime.utcnow() - timedelta(days=days, hours=hours)


def run(reset=False):
    app = create_app()
    with app.app_context():
        if reset:
            db.drop_all()
        db.create_all()

        for u, n, p, r in (("admin", "Operations Admin", "admin123", "admin"), ("agent1", "Support Agent", "agent123", "agent")):
            if not AdminUser.query.filter_by(username=u).first():
                db.session.add(AdminUser(username=u, name=n, password_hash=generate_password_hash(p), role=r))

        for acct, name, email, status in CUSTOMERS:
            if not Customer.query.filter_by(account_number=acct).first():
                db.session.add(Customer(account_number=acct, name=name, email=email, status=status,
                                        pin_hash=generate_password_hash("1234"), created_at=ago(30)))
        db.session.commit()
        cid = {c.account_number: c.id for c in Customer.query.all()}

        if ChatSession.query.count() == 0:
            made = []
            for acct, ctype, status, (cmsg, bmsg), d in SESSIONS:
                s = ChatSession(customer_id=cid[acct], complaint_type=ctype, session_status=status,
                                closure_confirmed=(status == "resolved"), started_at=ago(d, 2),
                                last_activity_at=ago(d, 1), ended_at=ago(d, 1) if status == "resolved" else None)
                db.session.add(s)
                db.session.flush()
                db.session.add(Message(session_id=s.id, sender="customer", content=cmsg, created_at=ago(d, 2)))
                db.session.add(Message(session_id=s.id, sender="bot", content=bmsg, created_at=ago(d, 2)))
                made.append(s)
            db.session.flush()
            for acct, text, label, score, d in REVIEWS:
                db.session.add(Review(customer_id=cid[acct], review_text=text, sentiment_label=label,
                                      sentiment_score=score, created_at=ago(d)))
            db.session.flush()
            neg = {r.customer_id: r for r in Review.query.filter_by(sentiment_label="negative").all()}
            # escalations: ai_detected (new, unacknowledged), customer_request (in progress), negative_review (closed)
            db.session.add(Escalation(session_id=made[10].id, reason="AI detected: customer asked for a human agent",
                                      source="ai_detected", status="open", created_at=ago(0, 1)))
            db.session.add(Escalation(session_id=made[2].id, reason="customer confirmed issue is unresolved",
                                      source="customer_request", status="in_progress", created_at=ago(1),
                                      acknowledged_at=ago(1), assigned_to="Support Agent"))
            db.session.add(Escalation(session_id=made[5].id, review_id=neg[cid["NA-100006"]].id,
                                      reason="negative customer review", source="negative_review",
                                      status="closed", created_at=ago(2), acknowledged_at=ago(2),
                                      assigned_to="Operations Admin"))
        db.session.commit()
        print("Seeded: %d customers, %d admin users, %d sessions, %d reviews, %d escalations" % (
            Customer.query.count(), AdminUser.query.count(), ChatSession.query.count(),
            Review.query.count(), Escalation.query.count()))


if __name__ == "__main__":
    run(reset="--reset" in sys.argv)
