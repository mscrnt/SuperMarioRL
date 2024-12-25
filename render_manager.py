# path: ./render_manager.py

import torch
from log_manager import LogManager
from utils import render_frame_to_queue, clear_frame_queue
import threading
import time
from copy import deepcopy

# Initialize a logger specific to this module
logger = LogManager("RenderMan")


class RenderManager:
    """
    Manages rendering in a separate thread to ensure it does not block training.
    """
    def __init__(self, render_env, model, cache_update_interval=120, training_active_flag=None):
        if render_env is None or model is None:
            raise ValueError("Both 'render_env' and 'model' must be provided to initialize RenderManager.")

        self.render_env = render_env
        self.model = model
        self.cached_policy = None
        self.cache_update_interval = cache_update_interval
        self.done_event = threading.Event()
        self.render_thread = None
        self.obs = None
        self.training_active_flag = training_active_flag or (lambda: True)
        self.rendering_active = False

        try:
            self.cached_policy = deepcopy(self.model.policy)
            logger.info("RenderManager initialized successfully with a cached policy.")
        except Exception as e:
            logger.error("Failed to initialize cached policy during RenderManager initialization.", exception=e)
            raise

    def _cache_policy(self):
        """Update the cached policy with a thread-safe copy."""
        try:
            self.cached_policy.load_state_dict(deepcopy(self.model.policy.state_dict()))
            logger.info("Cached policy updated successfully.")
        except Exception as e:
            logger.error("Error while updating cached policy.", exception=e)

    def _render_loop(self):
        """Rendering loop that runs in the background."""
        try:
            self.obs = self.render_env.reset()
            self.rendering_active = True  # Indicate rendering has started
            logger.info("Rendering thread started successfully.")
            while not self.done_event.is_set():
                try:
                    with torch.no_grad():
                        action, _ = self.cached_policy.predict(self.obs, deterministic=False)
                    self.obs, _, done, _ = self.render_env.step(action)
                    render_frame_to_queue(self.render_env)
                    if done:
                        self.obs = self.render_env.reset()
                except Exception as e:
                    logger.error("Error during rendering loop iteration.", exception=e)
                    break  # Break the rendering loop on iteration error
        except Exception as e:
            logger.error("Failed to initialize rendering loop.", exception=e)
        finally:
            self.rendering_active = False  # Reset flag when rendering stops
            logger.info("Rendering thread has stopped.")


    def start(self):
        """Start the render thread and the model caching mechanism."""
        try:
            self._cache_policy()
            self.render_thread = threading.Thread(target=self._render_loop, daemon=True)
            self.render_thread.start()
            threading.Thread(target=self._update_policy_loop, daemon=True).start()
            logger.info("RenderManager started successfully.")
        except Exception as e:
            logger.error("Failed to start RenderManager.", exception=e)
            self.rendering_active = False

    def is_rendering(self):
        """Return the rendering status."""
        return self.rendering_active and not self.done_event.is_set()


    def _update_policy_loop(self):
        """Periodically update the cached policy."""
        try:
            while not self.done_event.is_set():
                if not self.training_active_flag():
                    logger.info("Training has stopped, halting policy updates.")
                    break
                time.sleep(self.cache_update_interval)
                self._cache_policy()
        except Exception as e:
            logger.error("Error during policy update loop.", exception=e)

    def stop(self):
        """Stop the rendering thread and clear the frame queue."""
        try:
            logger.info("Stopping rendering thread.")
            self.done_event.set()
            if self.render_thread:
                self.render_thread.join()
            clear_frame_queue()  # Clear the frame queue when stopping
            logger.info("RenderManager stopped successfully.")
        except Exception as e:
            logger.error("Error stopping RenderManager.", exception=e)
