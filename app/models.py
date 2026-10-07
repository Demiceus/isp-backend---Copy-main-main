# app/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    account_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    pin_hash = db.Column(db.String(255))
    status = db.Column(db.String(20), default="active", nullable=False)  # active | pending | disabled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship("ChatSession", backref="customer", lazy=True)
    reviews = db.relationship("Review", backref="customer", lazy=True)


class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)

    complaint_type = db.Column(db.String(50))  # connectivity | billing | outage | router | account
    chat_summary = db.Column(db.Text)

    closure_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    session_status = db.Column(db.String(20), default="unresolved", nullable=False)

    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)

    messages = db.relationship("Message", backref="session", lazy=True)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False)
    sender = db.Column(db.String(10))  # 'customer' | 'bot'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    review_text = db.Column(db.Text, nullable=False)

    sentiment_label = db.Column(db.String(20), nullable=True)
    sentiment_score = db.Column(db.Float, nullable=True)

    matched_session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Escalation(db.Model):
    __tablename__ = "escalations"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey("reviews.id"), nullable=True)

    reason = db.Column(db.String(100))
    status = db.Column(db.String(20), default="open")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(30))  # ai_detected | customer_request | negative_review
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    assigned_to = db.Column(db.String(80), nullable=True)
    
class BatchJob(db.Model):
    __tablename__ = "batch_jobs"

    id = db.Column(db.Integer, primary_key=True)

    operation_type = db.Column(
        db.String(50),
        nullable=False
    )

    target_filter = db.Column(
        db.Text,
        nullable=True
    )

    message = db.Column(
        db.Text,
        nullable=True
    )

    total_targets = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    successful = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    failed = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default="pending",
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    items = db.relationship(
        "BatchItem",
        backref="batch_job",
        lazy=True,
        cascade="all, delete-orphan"
    )


class BatchItem(db.Model):
    __tablename__ = "batch_items"

    id = db.Column(db.Integer, primary_key=True)

    batch_job_id = db.Column(
        db.Integer,
        db.ForeignKey("batch_jobs.id"),
        nullable=False
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.id"),
        nullable=False
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey("chat_sessions.id"),
        nullable=True
    )

    status = db.Column(
        db.String(20),
        default="pending",
        nullable=False
    )

    result = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(80))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="admin", nullable=False)  # admin | agent
