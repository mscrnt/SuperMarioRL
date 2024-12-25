# path: routes/stream_routes.py

from flask import Response, Blueprint
from log_manager import LogManager
from utils import generate_frame_stream
from log_manager import log_queue
import queue

def create_stream_blueprint(training_manager):
    """
    Create the stream blueprint and integrate the training_manager.

    :param training_manager: Global TrainingManager instance to interact with.
    :return: Stream blueprint.
    """
    stream_blueprint = Blueprint("stream_routes", __name__)

    # Create logger
    logger = LogManager("stream_routes")

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

        logger.info("Starting log streaming")
        return Response(generate(), mimetype="text/event-stream")

    @stream_blueprint.route("/video_feed")
    def video_feed():
        """Video streaming route for game rendering."""
        return Response(generate_frame_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return stream_blueprint
