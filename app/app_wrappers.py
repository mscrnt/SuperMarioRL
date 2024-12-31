# path: ./app_wrappers.py

import gym
import numpy as np
from log_manager import LogManager
from utils import load_blueprints as Blueprint
from psycopg2.extras import Json




class EnhancedStatsWrapper(gym.Wrapper):
    """
    A wrapper to enhance environment observations with additional statistics.
    """

    def __init__(self, env, env_index=1):
        super(EnhancedStatsWrapper, self).__init__(env)
        self.env_index = env_index
        self.logger = LogManager(f"EnhancedStatsWrapper_env_{env_index}")
        self.logger.info("Initializing EnhancedStatsWrapper", env_index=env_index)

        # Extend observation space to include custom statistics
        stats_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(9,), dtype=np.float32)
        self.observation_space = gym.spaces.Dict({
            "frame": env.observation_space,
            "stats": stats_space
        })

    def step(self, action):
        obs, reward, done, info = self.env.step(action)

        # Collect statistics from the environment
        stats = {
            "coins": info.get("coins", getattr(self.env.unwrapped, "_coins", 0)),
            "score": info.get("score", getattr(self.env.unwrapped, "_score", 0)),
            "x_pos": info.get("x_pos", getattr(self.env.unwrapped, "_x_position", 0)),
            "player_state": info.get("player_state", getattr(self.env.unwrapped, "_player_state", 0)),
            "time": info.get("time", getattr(self.env.unwrapped, "_time", 0)),
            "flag_get": bool(info.get("flag_get", getattr(self.env.unwrapped, "_flag_get", 0))),
            "world": info.get("world", getattr(self.env.unwrapped, "_world", 0)),
            "stage": info.get("stage", getattr(self.env.unwrapped, "_stage", 0)),
            "status": {"small": 0, "tall": 1, "fireball": 2}.get(info.get("status", "small"), 0),
        }

        if done:
            readable_stats = ", ".join([f"{key}: {value}" for key, value in stats.items()])
            self.logger.info(f"Env {self.env_index} stats: {readable_stats}")

        processed_obs = {"frame": obs, "stats": np.array(list(stats.values()), dtype=np.float32)}
        info["stats"] = stats
        return processed_obs, reward, done, info

    def reset(self, **kwargs):
        obs = self.env.reset(**kwargs)
        return {"frame": obs, "stats": np.zeros(9, dtype=np.float32)}



EnhancedStatsWrapperBlueprint = Blueprint(
    component_class=EnhancedStatsWrapper,
    component_type="wrapper",
    required=True,
    default_params={},
    arg_map={"env_index": "env_index"},
    name="Enhanced Stats",
    description="Enhances the observation space with additional game statistics, such as coins, score, and player state."
)


class RewardManager(gym.Wrapper):
    """
    A wrapper to modify rewards based on custom logic.
    """

    def __init__(self, env):
        super(RewardManager, self).__init__(env)
        self.previous_coins = 0
        self.logger = LogManager("RewardManager")

    def reward(self, reward, action, info):
        """
        Modify the reward based on collected stats.
        """
        modified_reward = 0

        # Reward for collecting coins
        coins = info.get("coins", 0)
        if coins > self.previous_coins:
            coin_reward = (coins - self.previous_coins) * 0.5
            modified_reward += coin_reward
            self.logger.info("Coin reward applied", coin_reward=coin_reward)
        self.previous_coins = coins

        return reward + modified_reward

    def step(self, action):
        obs, reward, done, info = self.env.step(action)
        reward = self.reward(reward, action, info)
        return obs, reward, done, info

    def reset(self, **kwargs):
        self.previous_coins = 0
        return self.env.reset(**kwargs)


RewardManagerBlueprint = Blueprint(
    component_class=RewardManager,
    component_type="wrapper",
    required=False,
    arg_map={},
    name="Reward Manager",
    description="Adjusts rewards dynamically based on game statistics, such as coins collected."
)

class LoggingStatsWrapper(gym.Wrapper):
    """
    A wrapper to log enhanced statistics to a PostgreSQL database using the DBManager.
    Tracks steps, episodes, actions, and specific events for detailed analysis or replay.
    """
    def __init__(self, env, db_manager=None, env_index=1):
        super(LoggingStatsWrapper, self).__init__(env)
        self.env_index = env_index
        self.logger = LogManager(f"LoggingStatsWrapper_env_{env_index}")
        self.logger.info("Initializing LoggingStatsWrapper", env_index=env_index)
        self.db_manager = db_manager

        # Validate the DBManager
        if not self.db_manager:
            self.logger.error("No DBManager provided. Database logging will not be available.")
        else:
            self.logger.info("DBManager successfully linked to LoggingStatsWrapper.")

        # Initialize counters and stats
        self.step_count = 0
        self.episode_count = 0
        self.total_reward = 0
        self.level_stats = {}  # Aggregates stats per level (world, stage)

    def reset(self, **kwargs):
        """
        Resets the environment and prepares for a new episode.
        """
        self.episode_count += 1
        self.logger.info(f"Resetting environment for episode {self.episode_count}")

        # Reset counters
        self.step_count = 0
        self.total_reward = 0

        # Reset environment
        obs = self.env.reset(**kwargs)

        return obs

    def step(self, action):
        """
        Overrides the `step` method to log statistics after every environment step.
        Tracks steps, episodes, actions, and specific events.
        """
        self.step_count += 1
        obs, reward, done, info = self.env.step(action)

        # Accumulate total reward
        self.total_reward += reward

        # Collect stats from the `info` dictionary
        stats = {
            "world": info.get("world", 0),
            "stage": info.get("stage", 0),
            "area": info.get("area", 0),
            "x_pos": info.get("x_pos", 0),
            "y_pos": info.get("y_pos", 0),
            "score": info.get("score", 0),
            "coins": info.get("coins", 0),
            "life": info.get("life", 0),
            "status": info.get("status", "unknown"),
            "player_state": info.get("player_state", "unknown"),
            "flag_get": info.get("flag_get", False),
            "step": self.step_count,
            "episode": self.episode_count,
            "action": action,  # Track the action taken
            "reward": reward,
        }

        # Track specific events
        self._track_events(stats, done)

        # Log to the database
        self.log_to_db(stats)

        return obs, reward, done, info

    def _track_events(self, stats, done):
        """
        Tracks specific events like deaths, power-up pickups, and pipe usage.
        """
        level_key = (stats["world"], stats["stage"])

        # Initialize level stats if not already
        if level_key not in self.level_stats:
            self.level_stats[level_key] = {"deaths": 0, "x_pos_sum": 0, "total_coins": 0, "power_ups": 0, "pipes_used": 0}

        # Death tracking
        if done and stats["life"] == 0:
            self.level_stats[level_key]["deaths"] += 1
            self.logger.info(f"Env {self.env_index}: Death recorded on level {level_key} (Episode {self.episode_count}).")

        # Power-up tracking
        if stats["player_state"] in ["tall", "fireball"]:
            self.level_stats[level_key]["power_ups"] += 1
            self.logger.info(f"Env {self.env_index}: Power-up collected on level {level_key}.")

        # Pipe usage tracking
        if stats["player_state"] == "pipe":
            self.level_stats[level_key]["pipes_used"] += 1
            self.logger.info(f"Env {self.env_index}: Pipe used on level {level_key}.")

        # Aggregate stats
        self.level_stats[level_key]["x_pos_sum"] += stats["x_pos"]
        self.level_stats[level_key]["total_coins"] += stats["coins"]

    def log_to_db(self, stats):
        """
        Logs the given stats to the database.
        """
        if not self.db_manager or self.db_manager._db_pool is None:
            self.logger.warning("DBManager not initialized in this process. Reinitializing...")
            from db_manager import DBManager  # Import DBManager to avoid circular imports
            DBManager.initialize_db()
            self.db_manager = DBManager

        try:
            conn = self.db_manager.get_connection()
            with conn.cursor() as cursor:
                stats = {key: (int(value) if isinstance(value, np.integer) else value)
                         for key, value in stats.items()}
                cursor.execute("""
                    INSERT INTO mario_env_stats (env_id, world, stage, area, x_position, y_position, score, coins, life,
                    status, player_state, flag_get, additional_info, step, episode, action, reward, total_reward)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.env_index,
                    stats.get('world', 0),
                    stats.get('stage', 0),
                    stats.get('area', 0),
                    stats.get('x_pos', 0),
                    stats.get('y_pos', 0),
                    stats.get('score', 0),
                    stats.get('coins', 0),
                    stats.get('life', 0),
                    stats.get('status', 'unknown'),
                    stats.get('player_state', 'unknown'),
                    stats.get('flag_get', False),
                    Json(stats),
                    stats.get('step', 0),
                    stats.get('episode', 0),
                    stats.get('action', None),
                    stats.get('reward', 0),
                    self.total_reward,
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log stats to the database: {e}")
        finally:
            if conn:
                self.db_manager.release_connection(conn)


LoggingStatsWrapperBlueprint = Blueprint(
    component_class=LoggingStatsWrapper,
    component_type="wrapper",
    required=True,
    default_params={},
    arg_map={"db_manager": "db_manager", "env_index": "env_index"},
    name="Logging Stats",
    description="Logs enhanced environment statistics to a PostgreSQL database."
)

# Centralized repository for all wrapper blueprints
wrapper_blueprints = {
    "EnhancedStatsWrapper": EnhancedStatsWrapperBlueprint,
    "RewardManager": RewardManagerBlueprint,
    "LoggingStatsWrapper": LoggingStatsWrapperBlueprint,
}
