# path: ./app_wrappers.py

import gym
import numpy as np
from log_manager import LogManager
from utils import load_blueprints as Blueprint
from wrappers.enhanced_stats import EnhancedStatsWrapper
from wrappers.log_to_db import LoggingStatsWrapper

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
