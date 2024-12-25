# path: ./app.py

from flask import Flask, request
from global_state import training_manager  # Import global instance
from log_manager import LogManager
from routes.training_routes import create_training_blueprint
from routes.config_routes import create_config_blueprint
from routes.tensorboard_routes import create_tensorboard_blueprint
from routes.dashboard_routes import create_dashboard_blueprint
from routes.stream_routes import create_stream_blueprint
import logging

app = Flask(__name__)
logger = LogManager("app")

@app.before_request
def suppress_logging():
    """Suppress logs for specific routes."""
    if request.path == "/training/render_status":
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

# Register Blueprints with training_manager explicitly passed
app.register_blueprint(create_training_blueprint(training_manager), url_prefix="/training")
app.register_blueprint(create_config_blueprint(training_manager), url_prefix="/config")
app.register_blueprint(create_tensorboard_blueprint(training_manager), url_prefix="/tensorboard")
app.register_blueprint(create_stream_blueprint(training_manager), url_prefix="/stream")
app.register_blueprint(create_dashboard_blueprint(training_manager))  # No prefix for the dashboard

if __name__ == "__main__":
    logger.info("Starting application and initializing training_manager...")
    app.run(debug=True)
