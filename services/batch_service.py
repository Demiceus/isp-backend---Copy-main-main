import json

from datetime import datetime

from app.models import (
    db,
    Customer,
    ChatSession,
    BatchJob,
    BatchItem,
    Message,
)


VALID_STATUSES = {
    "unresolved",
    "resolved",
}

VALID_CATEGORIES = {
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
}


def find_batch_targets(
    complaint_type=None,
    session_status=None
):
    """
    Find customers/sessions that match the requested
    batch-processing filters.

    The latest matching session for each customer is used.
    """

    query = ChatSession.query

    if complaint_type:
        if complaint_type not in VALID_CATEGORIES:
            raise ValueError(
                f"Unsupported complaint type: {complaint_type}"
            )

        query = query.filter(
            ChatSession.complaint_type == complaint_type
        )

    if session_status:
        if session_status not in VALID_STATUSES:
            raise ValueError(
                f"Unsupported session status: {session_status}"
            )

        query = query.filter(
            ChatSession.session_status == session_status
        )

    sessions = (
        query
        .order_by(ChatSession.started_at.desc())
        .all()
    )

    # Keep only the latest matching session per customer.
    seen_customers = set()
    targets = []

    for session in sessions:

        if session.customer_id in seen_customers:
            continue

        seen_customers.add(session.customer_id)

        targets.append({
            "customer_id": session.customer_id,
            "account_number": session.customer.account_number,
            "name": session.customer.name,
            "email": session.customer.email,
            "session_id": session.id,
            "complaint_type": session.complaint_type,
            "session_status": session.session_status,
        })

    return targets


def preview_batch(
    complaint_type=None,
    session_status=None
):
    """
    Preview the customers that would be included
    in a batch operation.

    No database records are changed.
    """

    targets = find_batch_targets(
        complaint_type=complaint_type,
        session_status=session_status
    )

    return {
        "total_targets": len(targets),
        "targets": targets,
    }


def process_batch(
    complaint_type=None,
    session_status=None,
    message=None
):
    """
    Create and process a batch operation.

    Current implementation records the operation in
    PostgreSQL. It does not send real SMS/email messages.
    """

    if not message:
        raise ValueError("message is required")

    targets = find_batch_targets(
        complaint_type=complaint_type,
        session_status=session_status
    )

    filter_data = {
        "complaint_type": complaint_type,
        "session_status": session_status,
    }

    batch_job = BatchJob(
        operation_type="customer_notification",
        target_filter=json.dumps(filter_data),
        message=message,
        total_targets=len(targets),
        status="processing",
    )

    db.session.add(batch_job)
    db.session.flush()

    successful = 0
    failed = 0

    for target in targets:

        try:
            batch_item = BatchItem(
                batch_job_id=batch_job.id,
                customer_id=target["customer_id"],
                session_id=target["session_id"],
                status="processed",
                result="Notification recorded successfully.",
                completed_at=datetime.utcnow(),
            )

            db.session.add(batch_item)
            
            if target["session_id"]:
                db.session.add(Message(
                    session_id=target["session_id"],
                    sender="agent",
                    content=message,
                ))

            successful += 1

        except Exception as exc:

            batch_item = BatchItem(
                batch_job_id=batch_job.id,
                customer_id=target["customer_id"],
                session_id=target["session_id"],
                status="failed",
                result=str(exc),
                completed_at=datetime.utcnow(),
            )

            db.session.add(batch_item)

            failed += 1

    batch_job.successful = successful
    batch_job.failed = failed
    batch_job.status = "completed"
    batch_job.completed_at = datetime.utcnow()

    db.session.commit()

    return {
        "batch_id": batch_job.id,
        "operation_type": batch_job.operation_type,
        "total_targets": batch_job.total_targets,
        "successful": batch_job.successful,
        "failed": batch_job.failed,
        "status": batch_job.status,
    }


def get_batch_history():
    """
    Return previous batch-processing jobs.
    """

    jobs = (
        BatchJob.query
        .order_by(BatchJob.created_at.desc())
        .all()
    )

    return [
        {
            "id": job.id,
            "operation_type": job.operation_type,
            "target_filter": (
                json.loads(job.target_filter)
                if job.target_filter
                else {}
            ),
            "message": job.message,
            "total_targets": job.total_targets,
            "successful": job.successful,
            "failed": job.failed,
            "status": job.status,
            "created_at": (
                job.created_at.isoformat()
                if job.created_at
                else None
            ),
            "completed_at": (
                job.completed_at.isoformat()
                if job.completed_at
                else None
            ),
        }
        for job in jobs
    ]