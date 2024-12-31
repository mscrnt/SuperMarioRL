# path: routes/tensorboard_routes.py

from flask import Blueprint, jsonify, render_template
import subprocess
import os
import sys
from pathlib import Path
import threading


def create_tensorboard_blueprint(training_manager, app_logger):
    """
    Create the TensorBoard blueprint and integrate the training_manager and logger.

    :param training_manager: Global TrainingManager instance to interact with.
    :param app_logger: Global logger instance to be shared across blueprints.
    :return: TensorBoard blueprint.
    """
    # Create a scoped logger for this blueprint
    logger = app_logger.__class__("tensorboard_routes")

    tensorboard_blueprint = Blueprint("tensorboard", __name__, url_prefix="/tensorboard")

    # Shared state for TensorBoard
    tensorboard_process = None

    def start_tensorboard(logdir):
        """
        Start TensorBoard using its executable location or Python's environment path.
        """
        nonlocal tensorboard_process
        if tensorboard_process is None or tensorboard_process.poll() is not None:
            try:
                venv_dir = Path(sys.executable).parent
                tensorboard_executable = venv_dir / "tensorboard.exe" if os.name == "nt" else venv_dir / "tensorboard"

                if not tensorboard_executable.is_file():
                    raise FileNotFoundError(f"TensorBoard executable not found at {tensorboard_executable}")

                tensorboard_process = subprocess.Popen(
                    [str(tensorboard_executable), "--logdir", logdir, "--port", "6006", "--bind_all"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                logger.debug(f"TensorBoard started with executable: {tensorboard_executable}")
            except FileNotFoundError as e:
                logger.error(f"Failed to start TensorBoard: {e}")
            except Exception as e:
                logger.error(f"An error occurred while starting TensorBoard: {e}")
        else:
            logger.info("TensorBoard is already running.")

    def stop_tensorboard():
        """
        Stop the TensorBoard process if running.
        """
        nonlocal tensorboard_process
        if tensorboard_process is not None:
            try:
                tensorboard_process.terminate()
                tensorboard_process.wait()
                logger.info("TensorBoard stopped.")
            except Exception as e:
                logger.error(f"Failed to stop TensorBoard: {e}")

    @tensorboard_blueprint.route("/start", methods=["POST"])
    def start_tensorboard_endpoint():
        """
        Start TensorBoard via an API call.
        """
        try:
            start_tensorboard("./logs/tensorboard")  # Update logdir as needed
            return jsonify({"status": "success", "message": "TensorBoard started."})
        except Exception as e:
            logger.error(f"Error starting TensorBoard: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @tensorboard_blueprint.route("/stop", methods=["POST"])
    def stop_tensorboard_endpoint():
        """
        Stop TensorBoard via an API call.
        """
        try:
            stop_tensorboard()
            return jsonify({"status": "success", "message": "TensorBoard stopped."})
        except Exception as e:
            logger.error(f"Error stopping TensorBoard: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @tensorboard_blueprint.route("/", methods=["GET"])
    def tensorboard_content():
        """
        Render the TensorBoard iframe directly.
        """
        logger.info("Rendering TensorBoard iframe")
        return render_template("tensorboard.html")


    return tensorboard_blueprint
