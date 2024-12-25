# path: ./preprocessing.py

import gym
import numpy as np
import collections
import cv2
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
import torch
import torch.nn as nn
from log_manager import LogManager

logger = LogManager("preprocessing")


class MarioFeatureExtractor(BaseFeaturesExtractor):
    """
    Custom feature extractor for Mario environments.
    """

    def __init__(self, observation_space, features_dim=128):
        super(MarioFeatureExtractor, self).__init__(observation_space, features_dim)

        frame_shape = observation_space["frame"].shape
        self.frame_extractor = nn.Sequential(
            nn.Flatten(),
            nn.Linear(frame_shape[0] * frame_shape[1] * frame_shape[2], 256),
            nn.ReLU()
        )

        stats_shape = observation_space["stats"].shape[0]
        self.stats_extractor = nn.Sequential(
            nn.Linear(stats_shape, 64),
            nn.ReLU()
        )

        self.combined = nn.Sequential(
            nn.Linear(256 + 64, features_dim),
            nn.ReLU()
        )

    def forward(self, observations):
        frame_features = self.frame_extractor(observations["frame"])
        stats_features = self.stats_extractor(observations["stats"])
        combined_features = torch.cat([frame_features, stats_features], dim=1)
        return self.combined(combined_features)


class MaxAndSkipEnv(gym.Wrapper):
    """
    Wrapper for skipping frames and maximizing observations over skipped frames.
    """

    def __init__(self, env, skip=4):
        super(MaxAndSkipEnv, self).__init__(env)
        self.skip = skip
        self.obs_buffer = collections.deque(maxlen=2)

    def step(self, action):
        total_reward = 0.0
        done = False

        for _ in range(self.skip):
            obs, reward, done, info = self.env.step(action)
            self.obs_buffer.append(obs)
            total_reward += reward
            if done:
                break

        max_frame = np.max(np.stack(self.obs_buffer), axis=0)
        return max_frame, total_reward, done, info

    def reset(self, **kwargs):
        self.obs_buffer.clear()
        obs = self.env.reset(**kwargs)
        self.obs_buffer.append(obs)
        return obs


class MarioRescale84x84(gym.ObservationWrapper):
    """
    Wrapper to rescale the observation to 84x84 grayscale images.
    """

    def __init__(self, env):
        super(MarioRescale84x84, self).__init__(env)
        self.observation_space = gym.spaces.Box(low=0, high=255, shape=(84, 84, 1), dtype=np.uint8)

    def observation(self, obs):
        return MarioRescale84x84.process(obs)

    @staticmethod
    def process(frame):
        img = frame.astype(np.float32)
        img = img[:, :, 0] * 0.299 + img[:, :, 1] * 0.587 + img[:, :, 2] * 0.114
        resized_screen = cv2.resize(img, (84, 110), interpolation=cv2.INTER_AREA)
        cropped_screen = resized_screen[18:102, :]
        return np.expand_dims(cropped_screen, axis=-1).astype(np.uint8)


class ImageToPyTorch(gym.ObservationWrapper):
    """
    Wrapper to convert image observations to PyTorch format.
    """

    def __init__(self, env):
        super(ImageToPyTorch, self).__init__(env)
        old_shape = self.observation_space["frame"].shape
        self.observation_space = gym.spaces.Dict({
            "frame": gym.spaces.Box(
                low=0.0, high=1.0, shape=(old_shape[-1], old_shape[0], old_shape[1]), dtype=np.float32
            ),
            "stats": env.observation_space["stats"]
        })

    def observation(self, observation):
        return {
            "frame": np.moveaxis(observation["frame"], 2, 0),
            "stats": observation["stats"]
        }


class PixelNormalization(gym.ObservationWrapper):
    """
    Wrapper to normalize pixel values to the range [0, 1].
    """

    def observation(self, obs):
        obs["frame"] = obs["frame"] / 255.0
        return obs