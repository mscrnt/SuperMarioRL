import gym
import numpy as np
import json
from log_manager import LogManager


class LoggingStatsWrapper(gym.Wrapper):
    """
    A wrapper to log enhanced statistics to a PostgreSQL database using the DBManager.
    Logs core stats directly into columns and RAM-mapped states into the `additional_info` JSONB column.
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
        Overrides the `step` method to log enhanced statistics after every environment step.
        """
        self.step_count += 1
        obs, reward, done, info = self.env.step(action)

        # Accumulate total reward
        self.total_reward += reward

        # Separate core stats and RAM-mapped states
        full_stats = info.get("stats", {})
        core_stats = {
            "env_id": self.env_index,
            "step": self.step_count,
            "episode": self.episode_count,
            "action": action,
            "reward": reward,
            "total_reward": self.total_reward,
            "world": full_stats.get("world", 0),
            "stage": full_stats.get("stage", 0),
            "x_pos": full_stats.get("x_pos", 0),
            "y_pos": full_stats.get("y_pos", 0),
            "score": full_stats.get("score", 0),
            "coins": full_stats.get("coins", 0),
            "life": full_stats.get("life", 0),
        }

        # Convert RAM states to JSON-compatible values
        ram_states = {key: int(value) if isinstance(value, np.integer) else value for key, value in full_stats.items() if key.startswith("0x")}

        # Add RAM-mapped states to `additional_info`
        core_stats["additional_info"] = json.dumps(ram_states)

        # Log stats to the database
        self.log_to_db(core_stats)

        # Log episode stats if done
        if done:
            self.logger.info(f"Episode {self.episode_count} completed. Final stats:")
            for key, value in core_stats.items():
                self.logger.info(f"  {key}: {value}")

        return obs, reward, done, info

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
                # Convert numpy types to native Python types
                sanitized_stats = {key: (int(value) if isinstance(value, (np.integer, np.int64)) else value)
                                for key, value in stats.items()}
                sanitized_stats = {key: (float(value) if isinstance(value, (np.floating, np.float64)) else value)
                                for key, value in sanitized_stats.items()}

                # Dynamically generate the column list and values
                columns = ', '.join(sanitized_stats.keys())
                placeholders = ', '.join(['%s'] * len(sanitized_stats))
                values = tuple(sanitized_stats.values())

                cursor.execute(f"""
                    INSERT INTO mario_env_stats ({columns})
                    VALUES ({placeholders})
                """, values)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to log stats to the database: {e}")
        finally:
            if conn:
                self.db_manager.release_connection(conn)
