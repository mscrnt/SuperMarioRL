# path: routes/training_routes.py

from flask import Blueprint, request, jsonify
import threading

def create_training_blueprint(training_manager, app_logger):
    """
    Create the training blueprint and integrate the training_manager and logger.

    :param training_manager: Global TrainingManager instance to interact with.
    :param app_logger: Global logger instance to be shared across blueprints.
    :return: Training blueprint.
    """
    # Create a new logger for this blueprint
    logger = app_logger.__class__("training_routes")  # Create a scoped logger

    training_blueprint = Blueprint("training_routes", __name__)

    # Shared state for training
    training_thread = None
    training_lock = threading.Lock()  # Ensure thread-safe access to training_manager

    @training_blueprint.route("/start_training", methods=["POST"])
    def start_training():
        """Start the training process using TrainingManager."""
        nonlocal training_thread  # Use the blueprint-specific training_thread

        with training_lock:  # Ensure thread-safe access
            if training_manager.is_training_active():
                return jsonify({"status": "running", "message": "Training is already in progress."})

            # Configuration for training
            data = request.get_json() or {}
            config = {
                "training_config": data.get("training_config", {}),
                "hyperparameters": data.get("hyperparameters", {}),
                "enabled_wrappers": data.get("wrappers", []),
                "enabled_callbacks": data.get("callbacks", []),
            }
            logger.info("Received training configuration", extra={"config": config})

            # Set the configuration to the existing training_manager instance
            training_manager.config = config
            logger.debug("TrainingManager configuration updated successfully.")

        def run_training():
            try:
                logger.debug("Starting training initialization.")
                training_manager.initialize_training()
                logger.debug("Starting training loop.")
                training_manager.start_training()
            except Exception as e:
                logger.error(f"Training error: {e}")
            finally:
                try:
                    training_manager.stop_training()
                    logger.info("Training stopped successfully.")
                except Exception as stop_error:
                    logger.error(f"Error during training stop: {stop_error}")

        # Start training in a separate thread
        training_thread = threading.Thread(target=run_training, daemon=True)
        training_thread.start()

        return jsonify({"status": "success", "message": "Training started."})

    @training_blueprint.route("/stop_training", methods=["POST"])
    def stop_training():
        """Stop the training process."""
        with training_lock:  # Ensure thread-safe access
            if not training_manager.is_training_active():
                return jsonify({"status": "not_running", "message": "Training is not running."})

            try:
                training_manager.stop_training()
                logger.info("Training stop command executed.")
                return jsonify({"status": "success", "message": "Training stopped successfully."})
            except Exception as e:
                logger.error(f"Error stopping training: {e}")
                return jsonify({"status": "error", "message": f"Failed to stop training: {str(e)}"})

    @training_blueprint.route("/training_status", methods=["GET"])
    def training_status():
        """Return the current training status."""
        with training_lock:  # Ensure thread-safe access
            try:
                training_active = training_manager.is_training_active()
                logger.debug(f"Training status checked: active={training_active}")
                return jsonify({"training": training_active})
            except Exception as e:
                logger.error(f"Error checking training status: {e}")
                return jsonify({"status": "error", "message": "Failed to check training status."}), 500

    @training_blueprint.route("/render_status", methods=["GET"])
    def render_status():
        """Check if rendering is active."""
        with training_lock:  # Ensure thread-safe access
            try:
                rendering = training_manager.render_manager.is_rendering() if training_manager.render_manager else False
                logger.debug(f"Render status checked: rendering={rendering}")
                return jsonify({"rendering": rendering})
            except Exception as e:
                logger.error(f"Error checking rendering status: {e}")
                return jsonify({"status": "error", "message": "Failed to check rendering status."}), 500

    return training_blueprint
