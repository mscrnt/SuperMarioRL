# path: ./app.py

from flask import Flask, render_template, request
from global_state import training_manager, app_logger # Import global instances
from gui import DEFAULT_HYPERPARAMETERS, DEFAULT_TRAINING_CONFIG
from routes.training_routes import create_training_blueprint
from routes.config_routes import create_config_blueprint
from routes.tensorboard_routes import create_tensorboard_blueprint
from routes.dashboard_routes import create_dashboard_blueprint
from routes.stream_routes import create_stream_blueprint
import logging
import requests
from threading import Timer
from db_manager import DBManager


app = Flask(__name__)
logger = app_logger  # Use the global logger

@app.before_request
def suppress_logging():
    """Suppress logs for specific routes."""
    if request.path == "/training/render_status":
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

# Register Blueprints with logger explicitly passed
app.register_blueprint(create_training_blueprint(training_manager, app_logger, DBManager), url_prefix="/training")
app.register_blueprint(create_config_blueprint(training_manager, app_logger), url_prefix="/config")
app.register_blueprint(create_tensorboard_blueprint(training_manager, app_logger), url_prefix="/tensorboard")
app.register_blueprint(create_stream_blueprint(training_manager, app_logger), url_prefix="/stream")
app.register_blueprint(create_dashboard_blueprint(training_manager, app_logger, DBManager))  # No prefix for the dashboard

@app.route("/", methods=["GET"])
def index():
    """
    Render the main index.html with training_dashboard.html as its default content.
    """
    return render_template(
        "index.html",
        title="Super Mario RL",
        year=2024,  # Example year
    )

def start_tensorboard_via_api():
    """Call the TensorBoard start API when the app launches."""
    try:
        logger.info("Attempting to start TensorBoard via API...")
        response = requests.post("http://127.0.0.1:5000/tensorboard/start")
        if response.status_code == 200:
            logger.info("TensorBoard successfully started via API.")
        else:
            logger.error(f"Failed to start TensorBoard via API. Status code: {response.status_code}, Response: {response.text}")
    except requests.ConnectionError as e:
        logger.error(f"Connection error when trying to start TensorBoard: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when trying to start TensorBoard: {e}")

Timer(1, start_tensorboard_via_api).start()
