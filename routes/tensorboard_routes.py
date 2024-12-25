# path: routes/tensorboard_routes.py

from flask import Blueprint, jsonify, render_template
import subprocess
import os
import sys
from pathlib import Path
from log_manager import LogManager

# Create the dynamic blueprint
def create_tensorboard_blueprint(training_manager):
    """
    Create the tensorboard blueprint and integrate the training_manager.

    :param training_manager: Global TrainingManager instance to interact with.
    :return: TensorBoard blueprint.
    """
    tensorboard_blueprint = Blueprint("tensorboard_routes", __name__)
    logger = LogManager("tensorboard_routes")

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
                    [str(tensorboard_executable), "--logdir", logdir, "--port", "6006"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                logger.info(f"TensorBoard started with executable: {tensorboard_executable}")
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

    @tensorboard_blueprint.route("/start_tensorboard", methods=["POST"])
    def start_tensorboard_endpoint():
        """Start TensorBoard via an API call."""
        try:
            start_tensorboard("./logs/tensorboard")  # Update logdir as needed
            return jsonify({"status": "success", "message": "TensorBoard started."})
        except Exception as e:
            logger.error(f"Error starting TensorBoard: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @tensorboard_blueprint.route("/stop_tensorboard", methods=["POST"])
    def stop_tensorboard_endpoint():
        """Stop TensorBoard via an API call."""
        try:
            stop_tensorboard()
            return jsonify({"status": "success", "message": "TensorBoard stopped."})
        except Exception as e:
            logger.error(f"Error stopping TensorBoard: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @tensorboard_blueprint.route("/tensorboard")
    def tensorboard():
        """Redirect to TensorBoard UI if running, or show an error."""
        return render_template("tensorboard.html")

    return tensorboard_blueprint
