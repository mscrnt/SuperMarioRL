# path: routes/status_routes.py

from flask import Blueprint, jsonify, Response
from log_manager import log_queue
from utils import generate_frame_stream
import queue
import logging

# Create a Blueprint for status routes
status_blueprint = Blueprint("status_routes", __name__)
logger = logging.getLogger("status_routes")

# Global training manager to track the training and rendering status
training_manager = None


@status_blueprint.route("/training_status", methods=["GET"])
def training_status():
    """Return the current training status."""
    global training_manager
    training_active = training_manager.is_training_active() if training_manager else False
    return jsonify({"training": training_active})


@status_blueprint.route("/render_status", methods=["GET"])
def render_status():
    """Check if rendering is active."""
    global training_manager
    try:
        rendering = training_manager.render_manager.is_rendering() if training_manager else False
        return jsonify({"rendering": rendering})
    except Exception as e:
        logger.debug(f"Error checking rendering status: {e}")
        return jsonify({"status": "error", "message": "Failed to check rendering status."}), 500


@status_blueprint.route("/logs/stream")
def stream_logs():
    """Stream logs to the dashboard using server-sent events."""
    def generate():
        while True:
            try:
                log_entry = log_queue.get(timeout=1)
                yield f"data: {log_entry}\n\n"
            except queue.Empty:
                continue

    logger.info("Starting log streaming")
    return Response(generate(), mimetype="text/event-stream")


@status_blueprint.route("/video_feed")
def video_feed():
    """Video streaming route for game rendering."""
    return Response(generate_frame_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")
