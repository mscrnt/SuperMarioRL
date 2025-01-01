import gym
import numpy as np
import json
from log_manager import LogManager
from nes_py import NESEnv


class EnhancedStatsWrapper(gym.Wrapper):
    """
    A wrapper to enhance environment observations with additional statistics.
    Supports environments with direct or wrapped access to RAM states.
    """

    def __init__(self, env, env_index=1, json_path="/app/static/json/ram_states.json"):
        super(EnhancedStatsWrapper, self).__init__(env)
        self.env_index = env_index
        self.logger = LogManager(f"EnhancedStatsWrapper_env_{env_index}")
        self.logger.info("Initializing EnhancedStatsWrapper", env_index=env_index)

        # Load RAM state mapping from JSON
        self.ram_mapping = self._load_ram_mapping(json_path)

        # Extend observation space to include custom statistics
        stats_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.observation_space = gym.spaces.Dict({
            "frame": env.observation_space,
            "stats": stats_space
        })

        # Initialize custom stats tracking
        self.total_enemy_kills = 0
        self.total_deaths = 0
        self.previous_life = self._get_life()

    def _load_ram_mapping(self, json_path):
        """
        Load RAM state mapping from a JSON file.
        """
        try:
            with open(json_path, 'r') as file:
                ram_mapping = json.load(file)
            self.logger.info(f"Successfully loaded RAM mapping from {json_path}.")
            return ram_mapping
        except Exception as e:
            self.logger.error(f"Failed to load RAM mapping from {json_path}: {e}")
            return {}

    def _parse_address_range(self, address):
        """
        Parse a RAM address or range and return a list of integers.
        Handles ranges like '0x0016-0x001B'.
        """
        try:
            if '-' in address:  # Check for range notation
                start, end = address.split('-')
                return list(range(int(start, 16), int(end, 16) + 1))
            return [int(address, 16)]  # Single address
        except ValueError:
            self.logger.warning(f"Invalid address format: {address}. Skipping.")
            return []

    def _get_nes_env(self):
        """
        Retrieve the underlying NESEnv instance, even if wrapped in multiple layers.
        """
        env = self.env
        while hasattr(env, 'env'):
            env = env.env
        if isinstance(env, NESEnv):
            return env
        raise TypeError("Unable to locate NESEnv within wrapped environment.")

    def _get_ram_value(self, address):
        """
        Retrieve a RAM value from the NESEnv instance.
        """
        try:
            nes_env = self._get_nes_env()
            return nes_env.ram[address]
        except Exception as e:
            self.logger.error(f"Failed to retrieve RAM value at address {hex(address)}: {e}")
            return 0

    def _get_life(self):
        """
        Retrieve the current life count from RAM.
        """
        life_address = int("0x075A", 16)  # Use the key itself as the address
        try:
            life = self._get_ram_value(life_address)
            self.logger.debug(f"[RAM] Current life: {life}")
            return life
        except Exception as e:
            self.logger.error(f"Failed to retrieve life: {e}")
            return 3  # Default life count

    def _read_enemy_kills(self):
        """
        Count enemy kills from their states in RAM.
        """
        enemy_state_addresses = []
        for addr, data in self.ram_mapping.items():
            if data["category"] == "Enemies":
                enemy_state_addresses.extend(self._parse_address_range(addr))
        try:
            enemy_states = [self._get_ram_value(address) for address in enemy_state_addresses]
            kills = sum(state in [0x04, 0x20, 0x22, 0x23] for state in enemy_states)
            self.logger.debug(f"Enemy states: {enemy_states}, Kills this step: {kills}")
            return kills
        except Exception as e:
            self.logger.error(f"Failed to retrieve enemy states: {e}")
            return 0  # Default no kills

    def _track_deaths(self):
        """
        Track and log player deaths.
        """
        current_life = self._get_life()
        if current_life < self.previous_life:
            self.total_deaths += 1
            self.logger.info(f"Death detected. Total deaths: {self.total_deaths}")
        self.previous_life = current_life

    def step(self, action):
        """
        Override the step method to track and log statistics.
        """
        obs, reward, done, info = self.env.step(action)

        # Track kills and deaths
        kills_this_step = self._read_enemy_kills()
        self.total_enemy_kills += kills_this_step
        # self.logger.info(f"Kills this step: {kills_this_step}, Total kills: {self.total_enemy_kills}")

        self._track_deaths()

        # Collect statistics
        stats = {
            "coins": info.get("coins", self._get_ram_value(int("0x075E", 16))),
            "score": info.get("score", self._get_ram_value(int("0x0117", 16))),  # Adjusted to valid address
            "x_pos": info.get("x_pos", self._get_ram_value(int("0x071C", 16))),
            "time": info.get("time", self._get_ram_value(int("0x0747", 16))),
            "enemy_kills": self.total_enemy_kills,
            "deaths": self.total_deaths,
            "flag_get": bool(info.get("flag_get", self._get_ram_value(int("0x001D", 16)) == 3)),
            "world": info.get("world", self._get_ram_value(int("0x075F", 16)) + 1),
            "stage": info.get("stage", self._get_ram_value(int("0x0760", 16)) + 1),
        }

        # Log statistics when the episode ends
        if done:
            readable_stats = ", ".join([f"{key}: {value}" for key, value in stats.items()])
            self.logger.info(f"Env {self.env_index} stats: {readable_stats}")

        # Ensure stats fit the observation space
        stats_values = list(stats.values())[:15]
        if len(stats_values) < 15:
            stats_values.extend([0] * (15 - len(stats_values)))

        processed_obs = {"frame": obs, "stats": np.array(stats_values, dtype=np.float32)}
        info["stats"] = stats
        return processed_obs, reward, done, info

    def reset(self, **kwargs):
        """
        Reset the environment and statistics.
        """
        obs = self.env.reset(**kwargs)
        self.total_enemy_kills = 0
        self.total_deaths = 0
        self.previous_life = self._get_life()
        self.logger.info("Environment reset. Stats counters reset.")
        return {"frame": obs, "stats": np.zeros(15, dtype=np.float32)}
