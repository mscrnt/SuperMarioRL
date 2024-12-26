# path: .routes/config_routes.py

from flask import Blueprint, jsonify, request
from pathlib import Path
import json

def create_config_blueprint(training_manager, app_logger):
    """
    Create the config blueprint and integrate the training_manager and logger.
    
    :param training_manager: Global TrainingManager instance to interact with.
    :param app_logger: Global logger instance to be shared across blueprints.
    :return: Config blueprint.
    """
    # Create a new logger for this blueprint
    logger = app_logger.__class__("config_routes")  # Create a scoped logger

    config_blueprint = Blueprint("config_routes", __name__)

    # Directory to store configurations
    CONFIG_DIR = Path("./configs")
    CONFIG_DIR.mkdir(exist_ok=True)  # Ensure the directory exists

    @config_blueprint.route("/save_config", methods=["POST"])
    def save_config():
        """Save a configuration."""
        data = request.json
        config_name = data.get("name")
        config_data = data.get("config")
        overwrite = data.get("overwrite", False)

        if not config_name or not config_data:
            return jsonify({"status": "error", "message": "Name and configuration data are required."}), 400

        if config_name.lower() == "default":
            return jsonify({"status": "error", "message": "Cannot overwrite the Default configuration."}), 403

        config_path = CONFIG_DIR / f"{config_name}.json"
        if config_path.exists() and not overwrite:
            return jsonify({
                "status": "error",
                "message": f"Configuration '{config_name}' exists. Use 'overwrite=true' to update."
            }), 409

        try:
            with config_path.open("w") as f:
                json.dump(config_data, f, indent=4)
            logger.info(f"Configuration '{config_name}' saved successfully.")
            return jsonify({"status": "success", "message": f"Configuration '{config_name}' saved."})
        except Exception as e:
            logger.error(f"Error saving configuration '{config_name}': {e}")
            return jsonify({"status": "error", "message": f"Failed to save configuration '{config_name}'."}), 500

    @config_blueprint.route("/load_config/<name>", methods=["GET"])
    def load_config(name):
        config_path = CONFIG_DIR / f"{name}.json"
        if not config_path.exists():
            return jsonify({"status": "error", "message": f"Configuration '{name}' not found."}), 404

        try:
            with config_path.open() as f:
                config_data = json.load(f)
            return jsonify({"status": "success", "config": config_data})
        except Exception as e:
            logger.error(f"Error loading configuration '{name}': {str(e)}")
            return jsonify({"status": "error", "message": f"Failed to load configuration '{name}'."}), 500

    @config_blueprint.route("/delete_config/<name>", methods=["DELETE"])
    def delete_config(name):
        """Delete a configuration."""
        if name.lower() == "default":
            return jsonify({"status": "error", "message": "Cannot delete the Default configuration."}), 403

        config_path = CONFIG_DIR / f"{name}.json"
        if not config_path.exists():
            return jsonify({"status": "error", "message": f"Configuration '{name}' not found."}), 404

        try:
            config_path.unlink()
            logger.info(f"Configuration '{name}' deleted successfully.")
            return jsonify({"status": "success", "message": f"Configuration '{name}' deleted."})
        except Exception as e:
            logger.error(f"Error deleting configuration '{name}': {e}")
            return jsonify({"status": "error", "message": f"Failed to delete configuration '{name}'."}), 500

    @config_blueprint.route("/list_configs", methods=["GET"])
    def list_configs():
        """List all configurations."""
        try:
            configs = [p.stem for p in CONFIG_DIR.glob("*.json")]
            logger.info(f"Listed configurations: {configs}")
            return jsonify({"status": "success", "configs": configs})
        except Exception as e:
            logger.error(f"Error listing configurations: {e}")
            return jsonify({"status": "error", "message": "Failed to list configurations."}), 500

    return config_blueprint
