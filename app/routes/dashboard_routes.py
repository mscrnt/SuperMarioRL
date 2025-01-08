# path: routes/dashboard_routes.py

from flask import Blueprint, render_template, jsonify, request
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
        """
        Fetch metrics dynamically based on query parameters, supporting JSONB fields.
        """
        try:
            # Extract query parameters
            stat_keys = request.args.getlist("stat_keys")  # List of stats to fetch
            group_by = request.args.get("group_by", "step")  # Default grouping by "step"
            aggregation_type = request.args.get("agg_type", "SUM").upper()  # Aggregation type (SUM, AVG, etc.)

            if not stat_keys:
                return jsonify({"error": "No stat_keys provided"}), 400

            if aggregation_type not in {"SUM", "AVG", "COUNT", "MAX", "MIN"}:
                return jsonify({"error": f"Invalid aggregation type '{aggregation_type}' provided."}), 400

            conn = DBManager.get_connection()
            data = {"env0Stats": {}, "trainingStats": {}}

            with conn.cursor() as cursor:
                for stat in stat_keys:
                    # Determine whether the stat is a column or a JSONB field
                    if stat in {"enemy_kills", "deaths", "reward"}:  # Regular columns
                        column_path = f"{stat}"
                    else:  # JSONB fields in `additional_info`
                        column_path = f"additional_info->>'{stat}'"

                    # Debug: Check if the stat exists
                    if stat in {"enemy_kills", "deaths", "reward"}:
                        cursor.execute(f"SELECT COUNT(*) FROM mario_env_stats WHERE {stat} IS NOT NULL;")
                    else:
                        cursor.execute(f"SELECT COUNT(*) FROM mario_env_stats WHERE additional_info ? '{stat}';")
                    key_count = cursor.fetchone()[0]

                    if key_count == 0:
                        app_logger.warning(f"Key '{stat}' does not exist in any rows. Skipping.")
                        continue

                    # Aggregate metrics for env_id=0 (monitor)
                    cursor.execute(f"""
                        SELECT {group_by}, {aggregation_type}(CAST({column_path} AS FLOAT)) as result
                        FROM mario_env_stats
                        WHERE env_id = 0 AND ({stat} IS NOT NULL OR additional_info ? '{stat}')
                        GROUP BY {group_by}
                        ORDER BY {group_by};
                    """)
                    env0_data = cursor.fetchall()
                    data["env0Stats"][stat] = {row[0]: row[1] for row in env0_data}

                    # Aggregate metrics for env_id > 0 (training)
                    cursor.execute(f"""
                        SELECT {group_by}, {aggregation_type}(CAST({column_path} AS FLOAT)) as result
                        FROM mario_env_stats
                        WHERE env_id > 0 AND ({stat} IS NOT NULL OR additional_info ? '{stat}')
                        GROUP BY {group_by}
                        ORDER BY {group_by};
                    """)
                    training_data = cursor.fetchall()
                    data["trainingStats"][stat] = {row[0]: row[1] for row in training_data}

            DBManager.release_connection(conn)
            return jsonify(data)

        except Exception as e:
            app_logger.error(f"Error fetching metrics data: {e}")
            return jsonify({"error": "Failed to fetch metrics data."}), 500

    
    return dashboard_blueprint
