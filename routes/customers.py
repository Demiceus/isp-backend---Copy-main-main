# routes/customers.py - admin-only customer account management
import csv, io
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from app.models import db, Customer, ChatSession
from services.auth import new_account_number

customers_bp = Blueprint("customers", __name__)


def _row(c):
    return {"id": c.id, "account_number": c.account_number, "name": c.name, "email": c.email,
            "status": c.status, "created_at": c.created_at.isoformat() if c.created_at else None,
            "sessions": ChatSession.query.filter_by(customer_id=c.id).count()}


@customers_bp.route("/", methods=["GET"])
def list_customers():
    status = request.args.get("status", "all")
    q = Customer.query
    if status != "all":
        q = q.filter_by(status=status)
    return jsonify([_row(c) for c in q.order_by(Customer.created_at.desc()).all()]), 200


@customers_bp.route("/", methods=["POST"])
def create_customer():
    d = request.get_json() or {}
    pin = d.get("pin") or ""
    if len(pin) < 4:
        return jsonify({"error": "PIN must be at least 4 characters."}), 400
    acct = (d.get("account_number") or "").strip() or new_account_number()
    if Customer.query.filter_by(account_number=acct).first():
        return jsonify({"error": "That account number already exists."}), 409
    c = Customer(account_number=acct, name=(d.get("name") or "").strip(), email=(d.get("email") or "").strip(),
                 pin_hash=generate_password_hash(pin), status="active")
    db.session.add(c)
    db.session.commit()
    return jsonify(_row(c)), 201


def _set_status(cid, status):
    c = Customer.query.get_or_404(cid)
    c.status = status
    db.session.commit()
    return jsonify(_row(c)), 200


@customers_bp.route("/<int:cid>/approve", methods=["POST"])
def approve(cid):
    return _set_status(cid, "active")


@customers_bp.route("/<int:cid>/disable", methods=["POST"])
def disable(cid):
    return _set_status(cid, "disabled")


@customers_bp.route("/import", methods=["POST"])
def import_csv():
    """CSV columns: account_number (optional), name, email, pin"""
    text = (request.get_json() or {}).get("csv", "")
    created, skipped, errors = 0, 0, []
    for i, row in enumerate(csv.DictReader(io.StringIO(text.strip())), start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        pin = row.get("pin", "")
        if len(pin) < 4:
            errors.append("Row %d: PIN missing or too short" % i)
            continue
        acct = row.get("account_number") or new_account_number()
        if Customer.query.filter_by(account_number=acct).first():
            skipped += 1
            continue
        db.session.add(Customer(account_number=acct, name=row.get("name"), email=row.get("email"),
                                pin_hash=generate_password_hash(pin), status="active"))
        db.session.flush()
        created += 1
    db.session.commit()
    return jsonify({"created": created, "skipped": skipped, "errors": errors}), 200
