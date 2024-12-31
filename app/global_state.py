# path: global_state.py
from train import TrainingManager
from log_manager import LogManager
from db_manager import DBManager  # Import the DBManager class

# Global instance of TrainingManager
training_manager = TrainingManager()

# Global instance of LogManager
app_logger = LogManager("global")

# Initialize the database pool using DBManager
DBManager.initialize_db()

# Hook for application exit to close the DB pool gracefully
import atexit
atexit.register(DBManager.close_db_pool)
