# path: ./app.py

from flask import Flask, request
from global_state import training_manager, app_logger  # Import global instances
from routes.training_routes import create_training_blueprint
from routes.config_routes import create_config_blueprint
from routes.tensorboard_routes import create_tensorboard_blueprint
from routes.dashboard_routes import create_dashboard_blueprint
from routes.stream_routes import create_stream_blueprint
import logging

app = Flask(__name__)
logger = app_logger  # Use the global logger

@app.before_request
def suppress_logging():
    """Suppress logs for specific routes."""
    if request.path == "/training/render_status":
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

# Register Blueprints with logger explicitly passed
app.register_blueprint(create_training_blueprint(training_manager, app_logger), url_prefix="/training")
app.register_blueprint(create_config_blueprint(training_manager, app_logger), url_prefix="/config")
app.register_blueprint(create_tensorboard_blueprint(training_manager, app_logger), url_prefix="/tensorboard")
app.register_blueprint(create_stream_blueprint(training_manager, app_logger), url_prefix="/stream")
app.register_blueprint(create_dashboard_blueprint(training_manager, app_logger))  # No prefix for the dashboard

if __name__ == "__main__":
    logger.info("Starting application and initializing components...")
    app.run(debug=True)
