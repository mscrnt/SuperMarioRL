# path: gui/__init__.py

# Default hyperparameters
DEFAULT_HYPERPARAMETERS = {
    "n_steps": 2048,
    "batch_size": 64,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range_start": 0.2,
    "clip_range_end": 0.05,
    "learning_rate_start": 0.0003,
    "learning_rate_end": 0.00005,
    "n_epochs": 10,
    "vf_coef": 0.9,
    "ent_coef": 0.01,
    "max_grad_norm": 0.5,
    "normalize_advantage": True,
    "seed": 42,
    "device": "auto", 
    "pi_net": "64,64",  
    "vf_net": None,
    "clip_range_vf_start": None,
    "clip_range_vf_end": None,
    "target_kl": None,
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
    "random_stages": False,
    "total_timesteps": 2000000,
    "autosave_freq": 100000,
}

DB_CONFIG = {
    "dbname": "mariodb",
    "user": "mario",
    "password": "peach",
    "host": "127.0.0.1",
    "port": 5432,
}

# Exported symbols
__all__ = ["DEFAULT_TRAINING_CONFIG", "DEFAULT_HYPERPARAMETERS", "DEFAULT_PATHS", "DB_CONFIG"]
