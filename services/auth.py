# services/auth.py - signed-token auth + route guard
import re, random
from flask import request, jsonify, g, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.models import db, Customer, AdminUser, ChatSession

TOKEN_MAX_AGE = 60 * 60 * 12  # 12 hours
OPEN_PREFIXES = ("/api/auth/", "/api/reviews/public")


def _ser():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="netassist-auth")


def make_token(kind, uid):
    return _ser().dumps({"k": kind, "id": uid})


def read_token(kind):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        data = _ser().loads(header[7:], max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("id") if data.get("k") == kind else None


def new_account_number():
    while True:
        number = "NA-%06d" % random.randint(0, 999999)
        if not Customer.query.filter_by(account_number=number).first():
            return number


def init_auth(app):
    @app.before_request
    def guard():
        p = request.path
        if request.method == "OPTIONS" or not p.startswith("/api/"):
            return None
        if p.startswith(OPEN_PREFIXES) or p in ("/api/chat", "/api/chat/"):
            return None

        if p.startswith(("/api/admin", "/api/escalations", "/api/batch", "/api/customers")):
            aid = read_token("admin")
            admin = db.session.get(AdminUser, aid) if aid else None
            if not admin:
                return jsonify({"error": "Admin login required."}), 401
            g.admin = admin
            return None

        if p.startswith(("/api/chat", "/api/reviews")):
            cid = read_token("customer")
            customer = db.session.get(Customer, cid) if cid else None
            if not customer or customer.status != "active":
                return jsonify({"error": "Please log in to your account."}), 401
            g.customer = customer
            m = re.match(r"^/api/chat/(\d+)/", p)
            if m:
                chat = db.session.get(ChatSession, int(m.group(1)))
                if not chat:
                    return jsonify({"error": "Session not found."}), 404
                if chat.customer_id != customer.id:
                    return jsonify({"error": "This session belongs to another account."}), 403
        return None
