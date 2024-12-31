# path: routes/dashboard_routes.py

from flask import Blueprint, render_template, jsonify
from gui import DEFAULT_HYPERPARAMETERS, DEFAULT_TRAINING_CONFIG, DEFAULT_PATHS
from utils import load_blueprints  # Ensure this is correctly defined elsewhere
import importlib
import inspect


def create_dashboard_blueprint(training_manager, app_logger, DBManager):
    """
    Create the dashboard blueprint and integrate the training_manager and logger.

    :param training_manager: Global TrainingManager instance to interact with.
    :param app_logger: Global logger instance to be shared across blueprints.
    :return: Dashboard blueprint.
    """
    # Create a new logger for this blueprint
    logger = app_logger.__class__("dashboard_routes")  # Create a scoped logger

    # Initialize the dashboard blueprint
    dashboard_blueprint = Blueprint("dashboard", __name__)

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
            logger.debug(f"Loaded blueprints from {module_name}: {list(blueprints.keys())}")
            return blueprints
        except Exception as e:
            logger.error(f"Error loading blueprints from {module_name}: {e}")
            return {}

    # Load blueprints for wrappers and callbacks dynamically
    wrapper_blueprints = dynamic_load_blueprints("app_wrappers")
    callback_blueprints = dynamic_load_blueprints("app_callbacks")

    @dashboard_blueprint.route("/dashboard/training", methods=["GET"])
    def training_dashboard():
        """
        Render the main training dashboard.
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

        return render_template(
            "training_dashboard.html",
            title="Training Dashboard",
            hyperparameters=DEFAULT_HYPERPARAMETERS,
            training_config=DEFAULT_TRAINING_CONFIG,
            paths=DEFAULT_PATHS,
            wrappers=wrappers,
            callbacks=callbacks,
        )

    @dashboard_blueprint.route("/dashboard/metrics", methods=["GET"])
    def metrics_dashboard():
        """
        Render the metrics dashboard.
        """
        return render_template("metrics_dashboard.html", title="Metrics Dashboard")

        
    @dashboard_blueprint.route("/metrics/data", methods=["GET"])
    def fetch_metrics_data():
        try:
            conn = DBManager.get_connection()
            with conn.cursor() as cursor:
                # Fetch aggregate metrics for env_id=0
                cursor.execute("""
                    SELECT step, SUM(total_reward) as total_reward
                    FROM mario_env_stats
                    WHERE env_id = 0
                    GROUP BY step
                    ORDER BY step;
                """)
                env0_data = cursor.fetchall()

                # Fetch aggregate metrics for env_id > 0
                cursor.execute("""
                    SELECT step, AVG(total_reward) as avg_reward
                    FROM mario_env_stats
                    WHERE env_id > 0
                    GROUP BY step
                    ORDER BY step;
                """)
                training_data = cursor.fetchall()

            DBManager.release_connection(conn)

            # Structure the data
            metrics = {
                "env0": {row[0]: row[1] for row in env0_data},  # {step: total_reward}
                "training": {row[0]: row[1] for row in training_data},  # {step: avg_reward}
                "rewardDistribution": {"Coins": 40, "Score": 30, "Other": 30},  # Example
            }
            return jsonify(metrics)
        except Exception as e:
            app_logger.error(f"Error fetching metrics data: {e}")
            return jsonify({"error": "Failed to fetch metrics data."}), 500



    return dashboard_blueprint
