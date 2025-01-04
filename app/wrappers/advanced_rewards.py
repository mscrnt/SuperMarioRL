from log_manager import LogManager
import gym
from wrappers.enhanced_stats import EnhancedStatsWrapper


class DynamicRewardManager(gym.Wrapper):
    """
    A creative reward manager that dynamically calculates rewards using extensive RAM mappings.
    Works seamlessly with EnhancedStatsWrapper by unwrapping the environment.
    """

    def __init__(self, env, env_index=1):
        super(DynamicRewardManager, self).__init__(env)
        self.env_index = env_index
        self.logger = LogManager(f'DynamicRewardManager_env_{env_index}')

        # Locate EnhancedStatsWrapper in the wrapper stack
        self.stats_wrapper = self._get_enhanced_stats_wrapper(env)

        # Use the RAM mapping from EnhancedStatsWrapper
        self.ram_mapping = self.stats_wrapper.ram_mapping

        if not self.ram_mapping:
            raise ValueError("RAM mapping is required for DynamicRewardManager.")
        else:
            self.logger.info(f'RAM mapping loaded: {len(self.ram_mapping)} addresses')

        # Initialize metrics for tracking
        self.previous_state = {
            "coins": 0,
            "x_pos": 0,
            "kills": 0,
            "lives": self.stats_wrapper._get_life(),
            "power_up_state": self.stats_wrapper._get_ram_value(0x0756),
        }

        self.total_boss_defeats = 0
        self.total_flag_reaches = 0
        self.total_deaths = 0

    def _get_enhanced_stats_wrapper(self, env):
        """Unwrap the environment to locate the EnhancedStatsWrapper."""
        while isinstance(env, gym.Wrapper):
            if isinstance(env, EnhancedStatsWrapper):
                return env
            env = env.env
        raise TypeError("DynamicRewardManager requires EnhancedStatsWrapper to be in the environment stack.")

    # def _reward_progress(self, reward):
    #     """Reward Mario for forward progress."""
    #     x_pos = self.stats_wrapper._get_ram_value(0x071C)
    #     progress_reward = max(x_pos - self.previous_state["x_pos"], 0) * 0.1
    #     reward += progress_reward
    #     if progress_reward > 0:
    #         self.logger.info(f"Progress reward: +{progress_reward}")
    #     self.previous_state["x_pos"] = x_pos
    #     return reward

    def _reward_coin_collection(self, reward):
        """Reward Mario for collecting coins."""
        coins = self.stats_wrapper._get_ram_value(0x075E)
        coin_reward = max(coins - self.previous_state["coins"], 0) * 0.5
        reward += coin_reward
        if coin_reward > 0:
            self.logger.info(f"Coin reward: +{coin_reward}")
        self.previous_state["coins"] = coins
        return reward

    def _reward_enemy_kills(self, reward):
        """Reward Mario for defeating enemies."""
        enemy_kills = self.stats_wrapper._read_enemy_kills()
        kill_reward = (enemy_kills - self.previous_state["kills"]) * 5.0
        reward += kill_reward
        if kill_reward > 0:
            self.logger.info(f"Enemy kill reward: +{kill_reward}")
        self.previous_state["kills"] = enemy_kills
        return reward

    def _penalize_deaths(self, reward):
        """Penalize Mario for dying."""
        current_lives = self.stats_wrapper._get_life()
        if current_lives < self.previous_state["lives"]:
            death_penalty = -20.0
            reward += death_penalty
            self.total_deaths += 1
            self.logger.info(f"Death penalty applied: {death_penalty}")
        self.previous_state["lives"] = current_lives
        return reward

    def _detect_hit(self, reward):
        """Detect power-up loss and apply a penalty."""
        current_power_state = self.stats_wrapper._get_ram_value(0x0756)
        if current_power_state < self.previous_state["power_up_state"]:
            hit_penalty = -15.0 * (self.previous_state["power_up_state"] - current_power_state)
            reward += hit_penalty
            self.logger.info(f"Hit penalty applied: {hit_penalty}")
        self.previous_state["power_up_state"] = current_power_state
        return reward

    def _reward_boss_defeat(self, reward):
        """Reward significantly for defeating Bowser."""
        enemy_states = [self.stats_wrapper._get_ram_value(addr) for addr in range(0x0016, 0x001C)]
        if 0x23 in enemy_states:  # Bowser's defeated state
            reward += 100.0
            self.total_boss_defeats += 1
            self.logger.info("Boss defeat bonus: +100.0")
        return reward

    def _reward_for_flag(self, reward):
        """Reward reaching the flagpole."""
        player_state = self.stats_wrapper._get_ram_value(0x001D)
        if player_state == 0x03:  # Sliding down the flagpole
            reward += 50.0
            self.total_flag_reaches += 1
            self.logger.info("Flagpole reach bonus: +50.0")
        return reward

    def _penalize_pitfall(self, reward):
        """Detect falling into a pit and penalize."""
        if self.stats_wrapper._get_ram_value(0x00B5) > 1:  # Mario is below the screen viewport
            pitfall_penalty = -30.0
            reward += pitfall_penalty
            self.logger.info(f"Falling into pit penalty applied: {pitfall_penalty}")
        return reward

    def reward(self, base_reward, action, info):
        """
        Combine rewards and penalties from various game events.
        """
        reward = base_reward
        # reward = self._reward_progress(reward)
        reward = self._reward_coin_collection(reward)
        reward = self._reward_enemy_kills(reward)
        reward = self._penalize_deaths(reward)
        reward = self._reward_boss_defeat(reward)
        reward = self._reward_for_flag(reward)
        reward = self._detect_hit(reward)
        reward = self._penalize_pitfall(reward)
        return reward

    def step(self, action):
        """Override step to include reward modifications."""
        obs, reward, done, info = self.env.step(action)
        modified_reward = self.reward(reward, action, info)
        return obs, modified_reward, done, info

    def reset(self, **kwargs):
        """Reset tracked states at the beginning of an episode."""
        self.previous_state.update({
            "coins": 0,
            "x_pos": 0,
            "kills": 0,
            "lives": self.stats_wrapper._get_life(),
            "power_up_state": self.stats_wrapper._get_ram_value(0x0756),
        })
        return self.env.reset(**kwargs)
