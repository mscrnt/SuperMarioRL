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

        # Extend observation space to include stats
        stats_space = gym.spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.observation_space = gym.spaces.Dict({
            "frame": env.observation_space,
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
        life_address = int("0x075A", 16)  # Address for the life count
        try:
            return self._get_ram_value(life_address)
        except Exception:
            return 3  # Default life count

    def _read_enemy_kills(self):
        """
        Count enemy kills based on RAM states. 
        """
        enemy_state_addresses = []
        for addr, data in self.ram_mapping.items():
            if data["category"] == "Enemies":
                enemy_state_addresses.extend(self._parse_address_range(addr))
        try:
            enemy_states = [self._get_ram_value(address) for address in enemy_state_addresses]
            return sum(state in [0x04, 0x20, 0x22, 0x23] for state in enemy_states)
        except Exception:
            return 0

    def _track_deaths(self):
        """
        Track deaths by checking the player's state in RAM at address 0x000E
        and by comparing the number of lives.
        """
        player_state_address = int("0x000E", 16)
        player_state = self._get_ram_value(player_state_address)

        # State indicating death
        death_state = 0x06  # "Player dies"

        current_life = self._get_life()

        # Count death if player is in the death state or if the lives have decreased
        if player_state == death_state or current_life < self.previous_life:
            # If episode death will equal 4 after this death, return only 3
            if self.episode_deaths == 3:
                return
            self.episode_deaths += 1
            self.total_deaths += 1
            self.logger.info(
                f"Death detected. Episode deaths: {self.episode_deaths}, Total deaths: {self.total_deaths}"
            )

        # Update previous life
        self.previous_life = current_life


    def _parse_address_range(self, address):
        """Parse a RAM address or range and return a list of integers."""
        try:
            if '-' in address:
                start, end = address.split('-')
                return list(range(int(start, 16), int(end, 16) + 1))
            return [int(address, 16)]
        except ValueError:
            self.logger.warning(f"Invalid address format: {address}. Skipping.")
            return []

    def _get_mapped_states(self):
        """Extract all RAM states from the mapping and return a dictionary."""
        states = {}
        for addr, data in self.ram_mapping.items():
            addresses = self._parse_address_range(addr)
            for address in addresses:
                ram_value = self._get_ram_value(address)
                key = f"{addr}_{hex(address)}"
                states[key] = ram_value
        return states

    def step(self, action):
        """
        Override the step method to track stats and enhance the observation.
        """
        obs, reward, done, info = self.env.step(action)

        # Track kills and deaths
        kills_this_step = self._read_enemy_kills()
        self.episode_enemy_kills += kills_this_step
        self._track_deaths()

        # Track coins
        coins_this_step = self._get_ram_value(int("0x075E", 16))
        self.episode_coins += coins_this_step

        # Check if Mario is falling into a pit based on 0x00B5
        player_vertical_position = self._get_ram_value(int("0x00B5", 16))
        falling_into_pit = 1 < player_vertical_position <= 5  # True if vertical position is between 2 and 5 inclusive

        # Collect step-specific statistics
        stats = {
            "coins": coins_this_step,
            "score": self._get_ram_value(int("0x0117", 16)),
            "x_pos": self._get_ram_value(int("0x071C", 16)),
            "time": info.get("time", getattr(self.env.unwrapped, "_time", 0)),
            "enemy_kills": kills_this_step,
            "deaths": self.episode_deaths,
            "flag_get": bool(self._get_ram_value(int("0x001D", 16)) == 3),
            "world": self._get_ram_value(int("0x075F", 16)) + 1,
            "stage": self._get_ram_value(int("0x0760", 16)) + 1,
            "falling_into_pit": falling_into_pit  # New stat to track falling
        }

        # Add all mapped RAM states
        stats.update(self._get_mapped_states())

        # Define keys to exclude from printed stats
        keys_to_exclude = {}

        # Filter out RAM-specific keys
        filtered_stats = {key: value for key, value in stats.items() if key not in keys_to_exclude}

        # if done:
        #     # Convert stats to a readable string
        #     readable_stats = ", ".join([f"{key}: {value}" for key, value in filtered_stats.items()])
        #     self.logger.info(f"Env {self.env_index} stats: {readable_stats}")
        #     self.logger.info(
        #         f"Episode enemy kills: {self.episode_enemy_kills}, deaths: {self.episode_deaths}, "
        #         f"coins: {self.episode_coins}, total enemy kills: {self.total_enemy_kills}, "
        #         f"total deaths: {self.total_deaths}, total coins: {self.total_coins}"
        #     )

        # Ensure stats fit the observation space
        stats_values = list(stats.values())[:15]
        if len(stats_values) < 15:
            stats_values.extend([0] * (15 - len(stats_values)))

        processed_obs = {"frame": obs, "stats": np.array(stats_values, dtype=np.float32)}
        info["stats"] = stats  # Pass all stats, including RAM states, through info
        return processed_obs, reward, done, info


    def reset(self, **kwargs):
        """
        Reset the environment and per-episode stats.
        """
        obs = self.env.reset(**kwargs)
        self.episode_enemy_kills = 0
        self.episode_deaths = 0
        self.episode_coins = 0
        self.previous_life = self._get_life()  # Reset life tracking
        self.game_timer = 400
        return {"frame": obs, "stats": np.zeros(15, dtype=np.float32)}
