# path: routes/dashboard_routes.py

from flask import Blueprint, render_template
from gui import DEFAULT_HYPERPARAMETERS, DEFAULT_PATHS, DEFAULT_TRAINING_CONFIG
from log_manager import LogManager
import importlib
import inspect
from utils import load_blueprints


def create_dashboard_blueprint(training_manager):
    """
    Create the dashboard blueprint and integrate the training_manager.
    
    :param training_manager: Global TrainingManager instance to interact with.
    :return: Dashboard blueprint.
    """
    dashboard_blueprint = Blueprint("dashboard", __name__)
    logger = LogManager("dashboard_routes")

    def dynamic_load_blueprints(module_name):
        """
        Dynamically load all blueprint instances from a module.
        """
        try:
            module = importlib.import_module(module_name)
            blueprints = {
                name: obj for name, obj in inspect.getmembers(module)
                if isinstance(obj, load_blueprints)  # Ensure only load_blueprints instances are loaded
            }
            logger.info(f"Loaded blueprints from {module_name}: {list(blueprints.keys())}")
            return blueprints
        except Exception as e:
            logger.error(f"Error loading blueprints from {module_name}: {e}")
            return {}

    # Load blueprints for wrappers and callbacks dynamically
    wrapper_blueprints = dynamic_load_blueprints("app_wrappers")
    callback_blueprints = dynamic_load_blueprints("app_callbacks")

    @dashboard_blueprint.route("/")
    def index():
        """
        Render the main dashboard with training progress, settings, wrappers, and callbacks.
        """
        wrappers = [
            {
                "name": bp.name,
                "description": bp.description,
                "required": bp.required,
                "component_class": bp.component_class.__name__,
            }
            for bp in wrapper_blueprints.values()
        ]
        callbacks = [
            {
                "name": bp.name,
                "description": bp.description,
                "required": bp.required,
            }
            for bp in callback_blueprints.values()
        ]

        logger.info("Rendering index page", wrappers=wrappers, callbacks=callbacks)
        return render_template(
            "index.html",
            title="Training Dashboard",
            hyperparameters=DEFAULT_HYPERPARAMETERS,
            training_config=DEFAULT_TRAINING_CONFIG,
            paths=DEFAULT_PATHS,
            wrappers=wrappers,
            callbacks=callbacks,
        )

    return dashboard_blueprint
