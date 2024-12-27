# path: ./app_callbacks.py

from stable_baselines3.common.callbacks import BaseCallback
from pathlib import Path
from log_manager import LogManager
from utils import load_blueprints as Blueprint


class AutoSave(BaseCallback):
    """
    A callback for saving the model and checking training status using TrainingManager.
    """

    def __init__(self, check_freq, num_envs, save_path, filename_prefix="", verbose=1, training_manager=None):
        super(AutoSave, self).__init__(verbose)
        self.logger = LogManager("AutoSave")
        self.logger.info(
            "Initializing AutoSave Callback",
            check_freq=check_freq,
            num_envs=num_envs,
            save_path=save_path,
        )
        self.check_freq = int(check_freq / num_envs)
        self.num_envs = num_envs
        self.save_path_base = Path(save_path)
        self.filename = filename_prefix + "autosave_"
        self.training_manager = training_manager

    def _on_step(self) -> bool:
        """Save the model and gracefully stop training if requested."""
        self.logger.debug(f"AutoSave on_step called at step {self.n_calls}")

        if self.n_calls % self.check_freq == 0:
            if self.verbose > 0:
                self.logger.info(f"Saving latest model to {self.save_path_base}")
            self.model.save(self.save_path_base / (self.filename + str(self.n_calls * self.num_envs)))

        # Debug log to trace the training manager's active state
        is_active = self.training_manager.is_training_active() if self.training_manager else True
        self.logger.debug(f"Checking training status: is_training_active={is_active}")

        # Check if training is still active using TrainingManager
        if not is_active:
            self.logger.info("Graceful stop requested by AutoSave. Ending training.")
            self.model.save(self.save_path_base / (self.filename + str(self.n_calls * self.num_envs)))
            return False

        return True


class RenderCallback(BaseCallback):
    """
    A callback to signal the TrainingManager when the model should be updated.
    """

    def __init__(self, training_manager, verbose=0):
        super(RenderCallback, self).__init__(verbose)
        self.training_manager = training_manager
        self.logger = LogManager("RenderCallback")

    def _on_rollout_start(self):
        """Signal TrainingManager to update the cached policy at the start of each rollout."""
        self.training_manager.set_model_updated()
        self.logger.info("Signaled TrainingManager to update cached policy.")

    def _on_step(self) -> bool:
        """Override _on_step since it is abstract in BaseCallback."""
        return True  # No specific logic required here.


# Define the AutoSave blueprint with argument mapping
AutoSaveBlueprint = Blueprint(
    component_class=AutoSave,
    component_type="callback",
    required=True,
    default_params={
        "verbose": 1,
    },
    arg_map={
        "check_freq": "autosave_freq",
        "num_envs": "num_envs",
        "save_path": "save_path",
        "filename_prefix": "filename_prefix",
        "training_manager": "training_manager",
    },
    name="AutoSave",
    description="Automatically saves the model at regular intervals and supports graceful training termination.",
)

# Define the RenderCallback blueprint with argument mapping
RenderCallbackBlueprint = Blueprint(
    component_class=RenderCallback,
    component_type="callback",
    required=True,
    arg_map={
        "training_manager": "training_manager",  # Pass the TrainingManager directly
    },
    name="Model Sync",
    description="Signals the TrainingManager to update cached policy during rollouts.",
)

# Centralized callback blueprint repository
callback_blueprints = {
    "AutoSave": AutoSaveBlueprint,
    "RenderCallback": RenderCallbackBlueprint,
}
