# path: ./app_wrappers.py

import gym
import numpy as np
from log_manager import LogManager
from utils import load_blueprints as Blueprint
from wrappers.enhanced_stats import EnhancedStatsWrapper
from wrappers.log_to_db import LoggingStatsWrapper
from wrappers.advanced_rewards import DynamicRewardManager

EnhancedStatsWrapperBlueprint = Blueprint(
    component_class=EnhancedStatsWrapper,
    component_type="wrapper",
    required=True,
    default_params={},
    arg_map={"env_index": "env_index"},
    name="Enhanced Stats",
    description="Enhances the observation space with additional game statistics, such as coins, score, and player state."
)

RewardManagerBlueprint = Blueprint(
    component_class=DynamicRewardManager,
    component_type="wrapper",
    required=False,
    arg_map={"env_index": "env_index"},
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
