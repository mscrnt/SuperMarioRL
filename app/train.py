# path: ./train.py

from gui import DEFAULT_TRAINING_CONFIG, DEFAULT_HYPERPARAMETERS
from render_manager import RenderManager
from log_manager import LogManager
from utils import create_env, linear_schedule, load_blueprints as Blueprint
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor
from stable_baselines3.common.callbacks import CallbackList
from preprocessing import MarioFeatureExtractor
import threading
import importlib
import inspect


logger = LogManager("TrainingManager")


class TrainingManager:
    def __init__(self, config=None, db_manager=None):
        """
        Initialize the TrainingManager.

        :param config: Configuration for training.
        :param db_manager: Instance of the DBManager for database operations.
        """
        # Load blueprints dynamically
        self.wrapper_blueprints = self.load_blueprints("app_wrappers")
        self.callback_blueprints = self.load_blueprints("app_callbacks")

        # Initialize default configuration
        self.default_config = self.get_default_config(
            wrapper_blueprints=self.wrapper_blueprints,
            callback_blueprints=self.callback_blueprints,
        )

        # Use provided or default configuration
        self.config = config or self.default_config

        # Initialize active configuration
        self.active_config = {"config": None, "use_active": False}

        # Other attributes
        self.db_manager = db_manager  # Assign the db_manager
        self.training_active_event = threading.Event()
        self.training_active_event.clear()
        self.model_updated_flag = threading.Event()
        self.model_updated_flag.clear()
        self.render_manager = None
        self.model = None
        self.env = None
        self.wrapper_blueprints = {}
        self.callback_blueprints = {}
        self.callback_instances = []
        self.selected_wrappers = []
        self.shader_settings = {
            "radial_distortion": False,
            "scanlines": False,
            "dot_mask": False,
            "rolling_lines": False,
            "gamma_correction": False,
        }

    def get_shader_settings(self):
        """Get the current shader settings."""
        return self.shader_settings

    def toggle_shader(self, key, enabled):
        """Toggle a specific shader setting."""
        if key not in self.shader_settings:
            raise ValueError(f"Invalid shader key: {key}")
        self.shader_settings[key] = enabled

    def toggle_all_shaders(self, enable_all):
        """Enable or disable all shader settings."""
        for key in self.shader_settings:
            self.shader_settings[key] = enable_all

    def set_active_config(self, config):
        """Set the active configuration."""
        self.active_config = {"config": config, "use_active": True}
        logger.info("Active configuration updated.")

    def get_active_config(self):
        """
        Retrieve the active configuration.
        If no active configuration exists, return the default.
        """
        return self.active_config["config"] if self.active_config["use_active"] else self.default_config


    def clear_active_config(self):
        """Clear the active configuration and reset to default."""
        self.active_config = {"config": None, "use_active": False}
        logger.info("Active configuration cleared.")

    def get_effective_config(self):
        """
        Determine the effective configuration to use: 
        active configuration if available, otherwise default.
        """
        return self.get_active_config() if self.active_config["use_active"] else self.default_config


    @staticmethod
    def get_default_config(wrapper_blueprints=None, callback_blueprints=None):
        """Return the default training configuration with required wrappers and callbacks."""
        # Fallback to empty dictionaries if blueprints are not provided
        wrapper_blueprints = wrapper_blueprints or {}
        callback_blueprints = callback_blueprints or {}

        # Identify required wrappers and callbacks
        required_wrappers = [
            name for name, blueprint in wrapper_blueprints.items() if blueprint.is_required()
        ]
        required_callbacks = [
            name for name, blueprint in callback_blueprints.items() if blueprint.is_required()
        ]

        # Return the default configuration with required components
        return {
            "training_config": DEFAULT_TRAINING_CONFIG.copy(),
            "hyperparameters": DEFAULT_HYPERPARAMETERS.copy(),
            "enabled_wrappers": required_wrappers,
            "enabled_callbacks": required_callbacks,
        }

    @staticmethod
    def load_blueprints(module_name):
        """Dynamically load all blueprints from a given module."""
        try:
            module = importlib.import_module(module_name)
            blueprints = {
                name: obj for name, obj in inspect.getmembers(module)
                if isinstance(obj, Blueprint)
            }
            logger.info(f"Loaded blueprints from {module_name}: {list(blueprints.keys())}")
            return blueprints
        except Exception as e:
            logger.error(f"Error loading blueprints from {module_name}: {e}")
            return {}

    def stop_training(self):
        """Stop training and rendering gracefully."""
        logger.info("Stopping training...")
        self.training_active_event.clear()
        if self.render_manager:
            self.render_manager.stop()
        logger.info("Training stopped.")

    def is_training_active(self):
        """Check if training is active."""
        return self.training_active_event.is_set()

    def is_model_updated(self):
        """Check if the model has been updated."""
        return self.model_updated_flag.is_set()

    def clear_model_updated(self):
        """Clear the model updated flag."""
        self.model_updated_flag.clear()

    def set_model_updated(self):
        """Set the model updated flag."""
        self.model_updated_flag.set()

    def initialize_training(self):
        """Initialize training configurations, environments, and the model."""
        logger.debug("Initializing training with config", extra={"config": self.config})

        # Load blueprints dynamically
        self.wrapper_blueprints = self.load_blueprints("app_wrappers")
        self.callback_blueprints = self.load_blueprints("app_callbacks")

        logger.debug(f"Loaded wrapper blueprints: {list(self.wrapper_blueprints.keys())}")
        logger.debug(f"Loaded callback blueprints: {list(self.callback_blueprints.keys())}")

        # Load the active configuration
        self.config = self.get_active_config()

        # Merge and parse user configuration
        self._merge_and_parse_config()

        # Initialize callbacks and wrappers
        self._initialize_callbacks_and_wrappers()

        # Initialize environments and model
        self._initialize_environments_and_model()

        # Initialize the RenderManager
        self.render_manager = RenderManager(
            render_env=self.render_env,
            model=self.model,
            training_active_flag=self.is_training_active,
            model_updated_flag=self.model_updated_flag,
            shader_settings_flag=lambda: self.shader_settings  # Dynamically fetch shader states
        )

    def update_config(self, new_config):
        """Update the training configuration with a new configuration."""
        try:
            # Ensure self.config contains all necessary keys
            self.config.setdefault("training_config", {})
            self.config.setdefault("hyperparameters", {})
            self.config.setdefault("enabled_wrappers", [])
            self.config.setdefault("enabled_callbacks", [])

            # Update with new configuration values
            self.config["training_config"].update(new_config.get("training_config", {}))
            self.config["hyperparameters"].update(new_config.get("hyperparameters", {}))
            self.config["enabled_wrappers"] = new_config.get("enabled_wrappers", self.config["enabled_wrappers"])
            self.config["enabled_callbacks"] = new_config.get("enabled_callbacks", self.config["enabled_callbacks"])
            
            logger.info("Training configuration updated successfully.")
        except Exception as e:
            logger.error("Failed to update configuration", exception=e)
            raise ValueError("Invalid configuration format or data")


    def _merge_and_parse_config(self):
        """Merge and parse user-provided configurations."""
        default_config = {
            "num_envs": 1,
            "stages": [],
            "random_stages": False,  # Default to False
            "total_timesteps": 32000000,
            "n_steps": 2048,
            "batch_size": 64,
            "gamma": 0.99,
            "gae_lambda": 0.95,
            "clip_range_start": 0.2,
            "clip_range_end": 0.05,
            "clip_range_vf_start": None,
            "clip_range_vf_end": None,
            "learning_rate_start": 0.0003,
            "learning_rate_end": 0.00005,
            "n_epochs": 10,
            "vf_coef": 0.9,
            "ent_coef": 0.01,
            "max_grad_norm": 0.5,
            "normalize_advantage": True,  # Default to True
            "sde_sample_freq": -1,
            "policy_kwargs": {
                "features_extractor_class": MarioFeatureExtractor,
                "features_extractor_kwargs": {"features_dim": 128},
                "net_arch": [{"pi": [256, 256], "vf": [256, 256]}],
            },
            "tensorboard_log": "./logs/tensorboard",
            "save_path": "./checkpoints",
            "device": "auto",
            "shader_settings": {
                "radialDistortion": False,
                "scanlines": False,
                "dotMask": False,
                "rollingLines": False,
                "gammaCorrection": False,
            },
        }

        training_config = self.config.get("training_config", {})
        hyperparameters = self.config.get("hyperparameters", {})

        # Initialize wrappers and callbacks as empty lists
        enabled_wrappers = self.config.get("enabled_wrappers", [])
        enabled_callbacks = self.config.get("enabled_callbacks", [])

        # Parse stages input to convert from comma-separated string
        stages = training_config.get("stages", [])
        if isinstance(stages, str):  # Convert string to a list
            stages = [stage.strip() for stage in stages.split(",") if stage.strip()]
        training_config["stages"] = stages

        # Parse and merge configurations
        for key, value in {**training_config, **hyperparameters}.items():
            if value in ("None", None, ""):  # Handle None and empty strings
                training_config[key] = None
                hyperparameters[key] = None
            elif isinstance(value, str) and value.replace(".", "", 1).isdigit():
                training_config[key] = float(value) if "." in value else int(value)
                hyperparameters[key] = float(value) if "." in value else int(value)

        default_config.update(training_config)
        default_config.update(hyperparameters)

        # Add dynamic schedules
        default_config["learning_rate"] = linear_schedule(
            float(default_config["learning_rate_start"]), float(default_config["learning_rate_end"])
        )
        default_config["clip_range"] = linear_schedule(
            float(default_config["clip_range_start"]), float(default_config["clip_range_end"])
        )
        if default_config.get("clip_range_vf_start") is not None and default_config.get("clip_range_vf_end") is not None:
            default_config["clip_range_vf"] = linear_schedule(
                float(default_config["clip_range_vf_start"]), float(default_config["clip_range_vf_end"])
            )

        # Preserve wrappers and callbacks
        default_config["enabled_wrappers"] = enabled_wrappers
        default_config["enabled_callbacks"] = enabled_callbacks
        self.config = default_config

    def _initialize_callbacks_and_wrappers(self):
        """Initialize selected wrappers and callbacks."""
        logger.debug(f"Config data: {self.config}")

        # Initialize callbacks
        enabled_callbacks = set(self.config.get("enabled_callbacks", []))
        required_callbacks = {
            name for name, blueprint in self.callback_blueprints.items() if blueprint.is_required()
        }
        enabled_callbacks.update(required_callbacks)  # Ensure required callbacks are always included

        logger.info(f"Enabled callbacks from config: {enabled_callbacks}")
        self.callback_instances = []

        for name, blueprint in self.callback_blueprints.items():
            if name in enabled_callbacks:
                logger.debug(f"Initializing callback: {blueprint.name}")
                self.callback_instances.append(
                    blueprint.create_instance(config=self.config, training_manager=self)
                )
            else:
                logger.warning(f"Callback '{blueprint.name}' not selected or not required. Skipping.")

        if not self.callback_instances:
            logger.warning("No valid callbacks initialized. Training will proceed without callbacks.")

        # Initialize wrappers
        enabled_wrappers = set(self.config.get("enabled_wrappers", []))  # Get manually selected wrappers
        required_wrappers = {
            name for name, blueprint in self.wrapper_blueprints.items() if blueprint.is_required()
        }
        enabled_wrappers.update(required_wrappers)  # Ensure required wrappers are always included

        logger.info(f"Enabled wrappers from config: {enabled_wrappers}")
        self.selected_wrappers = []

        for name, blueprint in self.wrapper_blueprints.items():
            if name in enabled_wrappers:  # Include both required and manually selected wrappers
                logger.debug(f"Selecting wrapper: {blueprint.name}")
                self.selected_wrappers.append(blueprint.name)
            else:
                logger.warning(f"Wrapper '{blueprint.name}' not selected or not required. Skipping.")

        logger.debug(f"Final selected wrappers: {self.selected_wrappers}")
        logger.debug(f"Final selected callbacks: {[callback.__class__.__name__ for callback in self.callback_instances]}")




    def _initialize_environments_and_model(self):
        """Initialize the environment and the model."""
        try:
            # Pass db_manager when creating the render environment
            if self.config["random_stages"] == "True":
                self.render_env = create_env(
                    random_stages=self.config["random_stages"],
                    stages=self.config["stages"],
                    env_index=0,
                    selected_wrappers=self.selected_wrappers,
                    blueprints=self.wrapper_blueprints,
                    db_manager=self.db_manager  # Pass db_manager here
                )()
            else:
                self.render_env = create_env(
                    env_index=0,
                    selected_wrappers=self.selected_wrappers,
                    blueprints=self.wrapper_blueprints,
                    db_manager=self.db_manager  # Pass db_manager here
                )()

            # Create training environments
            num_envs = int(self.config["num_envs"])
            if self.config["random_stages"] == "True":
                env_fns = [
                    create_env(
                        random_stages=self.config["random_stages"],
                        stages=self.config["stages"],
                        env_index=i + 1,
                        selected_wrappers=self.selected_wrappers,
                        blueprints=self.wrapper_blueprints,
                        db_manager=self.db_manager  # Pass db_manager here
                    )
                    for i in range(num_envs)
                ]
            else:
                env_fns = [
                    create_env(
                        env_index=i + 1,
                        selected_wrappers=self.selected_wrappers,
                        blueprints=self.wrapper_blueprints,
                        db_manager=self.db_manager  # Pass db_manager here
                    )
                    for i in range(num_envs)
                ]
            self.env = VecMonitor(SubprocVecEnv(env_fns))

            # Create PPO model
            self.model = PPO(
                "MultiInputPolicy",
                self.env,
                verbose=1,
                gamma=self.config["gamma"],
                n_steps=self.config["n_steps"],
                batch_size=self.config["batch_size"],
                n_epochs=self.config["n_epochs"],
                learning_rate=self.config["learning_rate"],
                clip_range=self.config["clip_range"],
                clip_range_vf=self.config.get("clip_range_vf"),
                normalize_advantage=self.config["normalize_advantage"],
                ent_coef=self.config["ent_coef"],
                vf_coef=self.config["vf_coef"],
                max_grad_norm=self.config["max_grad_norm"],
                policy_kwargs=self.config["policy_kwargs"],
                target_kl=self.config["target_kl"],
                tensorboard_log=self.config["tensorboard_log"],
                seed=self.config["seed"],
                device=self.config["device"],
            )
        except Exception as e:
            logger.error("Error initializing environments or model.", exception=e)
            raise


    def start_training(self):
        """Start the training loop and rendering."""
        logger.info("Starting training process...")
        self.training_active_event.set()
        try:
            self.render_manager.start()
            logger.debug(f"Training loop active: {self.is_training_active()}")
            self.model.learn(
                total_timesteps=self.config.get("total_timesteps", 32000000),
                callback=CallbackList(self.callback_instances),
            )
        except Exception as e:
            logger.error(f"An error occurred during training: {e}")
        finally:
            self.stop_training()
