# routes/auth.py
import time
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, Customer, AdminUser
from services.auth import make_token, new_account_number

auth_bp = Blueprint("auth", __name__)

_fails = {}  # key -> (count, first_fail_time)
MAX_FAILS, WINDOW = 5, 300


def _locked(key):
    count, t0 = _fails.get(key, (0, 0))
    if count >= MAX_FAILS and time.time() - t0 < WINDOW:
        return True
    if time.time() - t0 >= WINDOW:
        _fails.pop(key, None)
    return False


def _fail(key):
    count, t0 = _fails.get(key, (0, time.time()))
    _fails[key] = (count + 1, t0)


@auth_bp.route("/customer/login", methods=["POST"])
def customer_login():
    d = request.get_json() or {}
    acct = (d.get("account_number") or "").strip()
    pin = d.get("pin") or ""
    key = "c:" + acct.lower()
    if _locked(key):
        return jsonify({"error": "Too many failed attempts. Try again in a few minutes."}), 429
    c = Customer.query.filter_by(account_number=acct).first()
    if not c or not c.pin_hash or not check_password_hash(c.pin_hash, pin):
        _fail(key)
        return jsonify({"error": "Invalid account number or PIN."}), 401
    if c.status == "pending":
        return jsonify({"error": "Your account is awaiting approval by NetAssist."}), 403
    if c.status != "active":
        return jsonify({"error": "This account is disabled. Please contact NetAssist."}), 403
    _fails.pop(key, None)
    return jsonify({"token": make_token("customer", c.id), "account_number": c.account_number, "name": c.name}), 200


@auth_bp.route("/customer/register", methods=["POST"])
def customer_register():
    d = request.get_json() or {}
    name = (d.get("name") or "").strip()
    email = (d.get("email") or "").strip()
    pin = d.get("pin") or ""
    if not name or "@" not in email:
        return jsonify({"error": "Enter your name and a valid email."}), 400
    if len(pin) < 4:
        return jsonify({"error": "PIN must be at least 4 characters."}), 400
    c = Customer(account_number=new_account_number(), name=name, email=email,
                 pin_hash=generate_password_hash(pin), status="pending")
    db.session.add(c)
    db.session.commit()
    return jsonify({"account_number": c.account_number,
                    "message": "Request received. You can log in once NetAssist approves your account."}), 201


@auth_bp.route("/admin/login", methods=["POST"])
def admin_login():
    d = request.get_json() or {}
    user = (d.get("username") or "").strip().lower()
    key = "a:" + user
    if _locked(key):
        return jsonify({"error": "Too many failed attempts. Try again in a few minutes."}), 429
    a = AdminUser.query.filter_by(username=user).first()
    if not a or not check_password_hash(a.password_hash, d.get("password") or ""):
        _fail(key)
        return jsonify({"error": "Invalid username or password."}), 401
    _fails.pop(key, None)
    return jsonify({"token": make_token("admin", a.id), "name": a.name or a.username, "role": a.role}), 200
