# path: routes/training_routes.py

from flask import Blueprint, request, jsonify
import threading

def create_training_blueprint(training_manager, app_logger, db_manager):
    """
    Create the training blueprint and integrate the training_manager, logger, and db_manager.

    :param training_manager: Global TrainingManager instance to interact with.
    :param app_logger: Global logger instance to be shared across blueprints.
    :param db_manager: Database manager instance to provide database access.
    :return: Training blueprint.
    """
    # Scoped logger
    logger = app_logger.__class__("training_routes")

    # Pass db_manager to training_manager
    training_manager.db_manager = db_manager

    training_blueprint = Blueprint("training_routes", __name__)

    # Shared state for training
    training_thread = None
    training_lock = threading.Lock()  # Ensure thread-safe access to training_manager

    def serialize_config(config):
        """Prepare the configuration dictionary for JSON serialization."""
        def safe_serialize(value):
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                return value
            if callable(value):
                return value.__name__
            return str(value)  # Fallback for non-serializable types

        # Ensure defaults and serialize
        serialized_config = {
            "training_config": config.get("training_config", {}),
            "hyperparameters": config.get("hyperparameters", {}),
            "enabled_wrappers": config.get("enabled_wrappers", []),
            "enabled_callbacks": config.get("enabled_callbacks", []),
        }
        return {key: safe_serialize(value) for key, value in serialized_config.items()}

    @training_blueprint.route("/start_training", methods=["POST"])
    def start_training():
        """Start the training process using TrainingManager."""
        nonlocal training_thread

        with training_lock:
            if training_manager.is_training_active():
                return jsonify({"status": "running", "message": "Training is already in progress."})

            data = request.get_json() or {}
            try:
                # Merge existing active config with new data
                current_config = training_manager.get_active_config()
                merged_config = {
                    "training_config": {**current_config.get("training_config", {}), **data.get("training_config", {})},
                    "hyperparameters": {**current_config.get("hyperparameters", {}), **data.get("hyperparameters", {})},
                    "enabled_wrappers": data.get("wrappers", current_config.get("enabled_wrappers", [])),
                    "enabled_callbacks": data.get("callbacks", current_config.get("enabled_callbacks", [])),
                }
                training_manager.set_active_config(merged_config)
                logger.info("TrainingManager configuration updated and set as active.")
            except ValueError as e:
                logger.error(f"Error updating configuration: {e}")
                return jsonify({"status": "error", "message": str(e)}), 400

        def run_training():
            try:
                logger.debug("Starting training initialization.")
                training_manager.initialize_training()
                logger.debug("Starting training loop.")
                training_manager.start_training()
            except Exception as e:
                logger.error(f"Training error: {e}")
                training_manager.stop_training()

        training_thread = threading.Thread(target=run_training, daemon=True)
        training_thread.start()

        return jsonify({
            "status": "success",
            "message": "Training started.",
        })


    @training_blueprint.route("/stop_training", methods=["POST"])
    def stop_training():
        """Stop the training process."""
        with training_lock:
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
        with training_lock:
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
        with training_lock:
            try:
                rendering = training_manager.render_manager.is_rendering() if training_manager.render_manager else False
                logger.debug(f"Render status checked: rendering={rendering}")
                return jsonify({"rendering": rendering})
            except Exception as e:
                logger.error(f"Error checking render status: {e}")
                return jsonify({"status": "error", "message": "Failed to check rendering status."}), 500

    @training_blueprint.route("/model_status", methods=["GET"])
    def model_status():
        """Check if the model has been updated."""
        with training_lock:
            try:
                model_updated = training_manager.is_model_updated()
                logger.debug(f"Model status checked: updated={model_updated}")
                return jsonify({"model_updated": model_updated})
            except Exception as e:
                logger.error(f"Error checking model status: {e}")
                return jsonify({"status": "error", "message": "Failed to check model status."}), 500
            
    @training_blueprint.route("/current_config", methods=["GET"])
    def get_current_config():
        """Return the active or default training configuration.""" 
        with training_lock:
            try:
                current_config = training_manager.get_active_config()
                return jsonify({"status": "success", "config": current_config})
            except Exception as e:
                logger.error(f"Error fetching current configuration: {e}")
                return jsonify({"status": "error", "message": "Failed to fetch configuration."}), 500
            
    @training_blueprint.route("/reset_to_default", methods=["POST"])
    def reset_to_default():
        """Reset the active configuration to default."""
        with training_lock:
            try:
                training_manager.clear_active_config()
                return jsonify({"status": "success", "message": "Configuration reset to default."})
            except Exception as e:
                logger.error(f"Error resetting configuration: {e}")
                return jsonify({"status": "error", "message": "Failed to reset configuration."}), 500



    return training_blueprint
