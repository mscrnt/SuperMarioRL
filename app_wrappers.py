# path: ./app_wrappers.py

import gym
import numpy as np
from log_manager import LogManager
from utils import load_blueprints as Blueprint


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
        stats = np.array([
            info.get("coins", getattr(self.env.unwrapped, "_coins", 0)),
            info.get("score", getattr(self.env.unwrapped, "_score", 0)),
            info.get("x_pos", getattr(self.env.unwrapped, "_x_position", 0)),
            info.get("player_state", getattr(self.env.unwrapped, "_player_state", 0)),
            info.get("time", getattr(self.env.unwrapped, "_time", 0)),
            int(info.get("flag_get", getattr(self.env.unwrapped, "_flag_get", 0))),
            info.get("world", getattr(self.env.unwrapped, "_world", 0)),
            info.get("stage", getattr(self.env.unwrapped, "_stage", 0)),
            {"small": 0, "tall": 1, "fireball": 2}.get(info.get("status", "small"), 0),
        ], dtype=np.float32)

        if done:
            self.logger.info(f"Env {self.env_index} stats: {stats}")

        processed_obs = {"frame": obs, "stats": stats}
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
    name="Enhanced Stats Wrapper",
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


# Centralized repository for all wrapper blueprints
wrapper_blueprints = {
    "EnhancedStatsWrapper": EnhancedStatsWrapperBlueprint,
    "RewardManager": RewardManagerBlueprint,
}
