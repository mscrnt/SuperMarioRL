# path: global_state.py
from train import TrainingManager
from log_manager import LogManager

# Global instance of TrainingManager
training_manager = TrainingManager()

# Global instance of LogManager
app_logger = LogManager("global")
