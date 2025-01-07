# path: routes/stream_routes.py

from flask import Response, Blueprint
from render_manager import generate_frame_stream
from log_manager import log_queue
import queue


def create_stream_blueprint(training_manager, app_logger):
    """
    Create the stream blueprint and integrate the training_manager and logger.

    :param training_manager: Global TrainingManager instance to interact with.
    :param app_logger: Global logger instance to be shared across blueprints.
    :return: Stream blueprint.
    """
    # Create a new logger for this blueprint
    logger = app_logger.__class__("stream_routes")  # Create a scoped logger

    stream_blueprint = Blueprint("stream_routes", __name__)

    @stream_blueprint.route("/logs")
    def stream_logs():
        """Stream logs to the dashboard using server-sent events."""
        def generate():
            while True:
                try:
                    log_entry = log_queue.get(timeout=1)
                    yield f"data: {log_entry}\n\n"
                except queue.Empty:
                    continue

        logger.debug("Starting log streaming")
        return Response(generate(), mimetype="text/event-stream")

    @stream_blueprint.route("/video_feed")
    def video_feed():
        """Video streaming route for game rendering."""
        logger.debug("Starting video feed stream")
        return Response(generate_frame_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return stream_blueprint

