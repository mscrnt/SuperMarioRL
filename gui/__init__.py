# path: gui/__init__.py

# Default hyperparameters
DEFAULT_HYPERPARAMETERS = {
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
    "normalize_advantage": True,
    "rollout_buffer_class": None,
    "rollout_buffer_kwargs": None,
    "target_kl": None,
    "seed": 42,
    "pi_net": "128,128",  
    "vf_net": "64,64",
    "device": "auto", 
}

# Default paths
DEFAULT_PATHS = {
    "log_dir": "./logs",
    "tensorboard_log_dir": "./logs/tensorboard",
    "save_path": "./checkpoints",
}

# Default training configuration
DEFAULT_TRAINING_CONFIG = {
    "num_envs": 1,
    "stages": [],
    "random_stages": True,
    "total_timesteps": 2000000,
    "autosave_freq": 100000,
}

# Exported symbols
__all__ = ["DEFAULT_TRAINING_CONFIG", "DEFAULT_HYPERPARAMETERS", "DEFAULT_PATHS"]
