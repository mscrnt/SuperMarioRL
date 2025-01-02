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

        # Extend observation space
        frame_space = env.observation_space
        stats_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(15 + len(self.ram_mapping),), dtype=np.float32)
        self.observation_space = gym.spaces.Dict({
            "frame": frame_space,
            "stats": stats_space
        })

        # Track lifecycle stats
        self.total_enemy_kills = 0
        self.total_deaths = 0
        self.total_coins = 0

        # Track per-episode stats
        self.episode_enemy_kills = 0
        self.episode_deaths = 0
        self.episode_coins = 0

        # Track the player's lives
        self.previous_life = self._get_life()

    def _load_ram_mapping(self, json_path):
        """Load RAM state mapping from a JSON file."""
        try:
            with open(json_path, 'r') as file:
                ram_mapping = json.load(file)
            self.logger.info(f"Successfully loaded RAM mapping from {json_path}.")
            return ram_mapping
        except Exception as e:
            self.logger.error(f"Failed to load RAM mapping from {json_path}: {e}")
            return {}

    def _get_nes_env(self):
        """Retrieve the underlying NESEnv instance, even if wrapped in multiple layers."""
        env = self.env
        while hasattr(env, 'env'):
            env = env.env
        if isinstance(env, NESEnv):
            return env
        raise TypeError("Unable to locate NESEnv within wrapped environment.")

    def _get_ram_value(self, address):
        """Retrieve a RAM value from the NESEnv instance."""
        try:
            nes_env = self._get_nes_env()
            return nes_env.ram[address]
        except Exception as e:
            self.logger.error(f"Failed to retrieve RAM value at address {hex(address)}: {e}")
            return 0

    def _read_enemy_kills(self):
        """Count enemy kills from their states in RAM."""
        enemy_state_addresses = [int(addr, 16) for addr, data in self.ram_mapping.items() if data["category"] == "Enemies"]
        try:
            enemy_states = [self._get_ram_value(address) for address in enemy_state_addresses]
            return sum(state in [0x04, 0x20, 0x22, 0x23] for state in enemy_states)
        except Exception:
            return 0

    def _track_deaths(self):
        """Track deaths by checking the player's state in RAM and by comparing the number of lives."""
        player_state_address = int("0x000E", 16)
        player_state = self._get_ram_value(player_state_address)
        current_life = self._get_life()

        # States indicating death
        death_states = [0x06, 0x0B]

        # Count death if player is in a death state or if the lives have decreased
        if player_state in death_states or current_life < self.previous_life:
            self.episode_deaths += 1
            self.total_deaths += 1
            self.logger.info(f"Death detected. Episode deaths: {self.episode_deaths}, Total deaths: {self.total_deaths}")

        # Update previous life
        self.previous_life = current_life

    def _get_life(self):
        """Retrieve the current life count from RAM."""
        life_address = int("0x075A", 16)
        return self._get_ram_value(life_address)

    def _get_mapped_states(self):
        """Extract all RAM states from the mapping and return a dictionary."""
        states = {}
        for addr in self.ram_mapping:
            ram_value = self._get_ram_value(int(addr, 16))
            states[addr] = ram_value
        return states

    def step(self, action):
        """Override the step method to track and add all mapped states to stats."""
        obs, reward, done, info = self.env.step(action)

        # Track kills and deaths
        kills_this_step = self._read_enemy_kills()
        self.episode_enemy_kills += kills_this_step
        self.total_enemy_kills += kills_this_step
        self._track_deaths()

        # Track coins
        coins_this_step = self._get_ram_value(int("0x075E", 16))
        self.episode_coins += coins_this_step
        self.total_coins += coins_this_step

        # Collect step-specific statistics
        stats = {
            "coins": coins_this_step,
            "score": self._get_ram_value(int("0x0117", 16)),
            "x_pos": self._get_ram_value(int("0x071C", 16)),
            "time": self._get_ram_value(int("0x0747", 16)),
            "enemy_kills": kills_this_step,
            "deaths": self.episode_deaths,
            "flag_get": bool(self._get_ram_value(int("0x001D", 16)) == 3),
            "world": self._get_ram_value(int("0x075F", 16)) + 1,
            "stage": self._get_ram_value(int("0x0760", 16)) + 1,
        }

        # Add all mapped RAM states
        mapped_states = self._get_mapped_states()
        stats.update(mapped_states)

        # Flatten the frame and stats into a single array
        combined_obs = np.concatenate([obs.flatten(), np.array(list(stats.values()))])

        return combined_obs, reward, done, {"stats": stats}

    def reset(self, **kwargs):
        """Reset the environment and per-episode stats."""
        obs = self.env.reset(**kwargs)
        self.episode_enemy_kills = 0
        self.episode_deaths = 0
        self.episode_coins = 0
        self.previous_life = self._get_life()
        return np.zeros(obs.shape + (len(self.ram_mapping),))
