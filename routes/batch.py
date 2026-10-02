from flask import Blueprint, request, jsonify

from services.batch_service import (
    preview_batch,
    process_batch,
    get_batch_history,
)


batch_bp = Blueprint("batch", __name__)


@batch_bp.route("/preview", methods=["POST"])
def batch_preview():
    """
    Preview which customers match the selected filters.
    """

    data = request.get_json() or {}

    complaint_type = data.get("complaint_type")
    session_status = data.get("session_status")

    try:
        result = preview_batch(
            complaint_type=complaint_type,
            session_status=session_status
        )

        return jsonify({
            "status": "success",
            "data": result
        }), 200

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400


@batch_bp.route("/process", methods=["POST"])
def batch_process():
    """
    Process a confirmed batch operation.
    """

    data = request.get_json() or {}

    complaint_type = data.get("complaint_type")
    session_status = data.get("session_status")
    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "error": "message is required"
        }), 400

    try:
        result = process_batch(
            complaint_type=complaint_type,
            session_status=session_status,
            message=message
        )

        return jsonify({
            "status": "success",
            "data": result
        }), 201

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400


@batch_bp.route("/history", methods=["GET"])
def batch_history():
    """
    Return previous batch operations.
    """

    history = get_batch_history()

    return jsonify({
        "status": "success",
        "data": history
    }), 200