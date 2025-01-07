# path: ./render_manager.py

import torch
from log_manager import LogManager
import threading
import time
from copy import deepcopy
import queue
import cv2
import numpy as np

# Initialize a logger specific to this module
logger = LogManager("RenderMan")

frame_queue = queue.Queue(maxsize=50)


def clear_frame_queue():
    """
    Clears all frames from the frame queue.
    """
    discarded_frames = 0
    while not frame_queue.empty():
        frame_queue.get_nowait()
        discarded_frames += 1
    logger.info("Frame queue cleared", discarded_frames=discarded_frames)



def apply_crt_shader(frame):
    """
    Apply a CRT-like shader effect with radial distortion, scanlines, and advanced dot mask emulation.
    """
    height, width, _ = frame.shape

    # Step 1: Normalize the frame to [0, 1] for processing
    frame_normalized = frame.astype(np.float32) / 255.0

    # Step 2: Apply radial distortion
    distortion = 0.2
    center_x, center_y = width / 2, height / 2
    x, y = np.meshgrid(np.linspace(0, 1, width), np.linspace(0, 1, height))
    x_centered, y_centered = x - 0.5, y - 0.5
    radial_dist = x_centered**2 + y_centered**2
    distortion_factor = 1 + radial_dist * distortion
    x_distorted = x_centered * distortion_factor + 0.5
    y_distorted = y_centered * distortion_factor + 0.5
    map_x = (x_distorted * width).astype(np.float32)
    map_y = (y_distorted * height).astype(np.float32)
    frame_distorted = cv2.remap(frame_normalized, map_x, map_y, interpolation=cv2.INTER_LINEAR)

    # Step 3: Add horizontal scanline effect
    scanline_overlay = np.ones((height, 1), dtype=np.float32)
    scanline_overlay[::2, 0] = 0.9  # Darken every other row
    scanline_overlay = np.repeat(scanline_overlay, width, axis=1).reshape(height, width, 1)
    frame_with_scanlines = frame_distorted * scanline_overlay

    # Step 4: Improved dot-mask simulation
    # Calculate alternating color weights for dot-mask effect
    mod_factor = np.arange(width) % 3  # Cycle through 3 patterns
    dot_mask_weights = np.zeros((1, width, 3), dtype=np.float32)
    dot_mask_weights[:, mod_factor == 0, 0] = 1.05  # Red
    dot_mask_weights[:, mod_factor == 1, 1] = 1.05  # Green
    dot_mask_weights[:, mod_factor == 2, 2] = 1.05  # Blue
    dot_mask_weights[:, :, :] = np.where(dot_mask_weights == 0, 0.8, dot_mask_weights)  # Dampen other channels

    # Apply dot-mask effect row by row
    dot_mask_weights = np.tile(dot_mask_weights, (height, 1, 1))
    frame_with_dot_mask = frame_with_scanlines * dot_mask_weights

    # Step 5: Apply gamma correction
    input_gamma = 2.2
    output_gamma = 2.5
    frame_gamma_corrected = np.clip(frame_with_dot_mask ** (input_gamma / output_gamma), 0, 1)

    # Scale back to [0, 255] for display
    frame_output = (frame_gamma_corrected * 255).astype(np.uint8)

    return frame_output

def render_frame_to_queue(first_env, throttle_interval=0.05):
    """
    Render a frame, apply shader effects, and place it in the frame queue.

    :param first_env: The environment to render frames from.
    :param throttle_interval: Interval between frame captures.
    """
    try:
        frame = first_env.render(mode="rgb_array")
        processed_frame = apply_crt_shader(frame)

        if frame_queue.full():
            discarded_frame = frame_queue.get_nowait()
            logger.debug("Discarded oldest frame due to queue overflow", frame=discarded_frame)
        frame_queue.put(processed_frame, block=False)
        time.sleep(throttle_interval)
    except Exception as e:
        logger.error("Rendering failed", exception=e)


def generate_frame_stream(frame_rate=120):
    """
    Generator function to stream frames as MJPEG.

    :param frame_rate: Target frame rate for the stream.
    :return: Generator yielding MJPEG frames.
    """
    interval = 1.0 / frame_rate
    while True:
        try:
            frame = frame_queue.get()
            _, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(interval)
        except Exception as e:
            logger.error("Error generating frame stream", exception=e)


class RenderManager:
    """
    Manages rendering in a separate thread to ensure it does not block training.
    """
    def __init__(self, render_env, model, cache_update_interval=120, training_active_flag=None, model_updated_flag=None):
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
        self.model_updated_flag = model_updated_flag or threading.Event()
        self.rendering_active = threading.Event()

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
            logger.debug("Cached policy updated successfully.")
        except Exception as e:
            logger.error("Error while updating cached policy.", exception=e)

    def _render_loop(self):
        """Rendering loop that runs in the background.""" 
        try:
            self.obs = self.render_env.reset()
            self.rendering_active.set()
            logger.info("Rendering thread started successfully.")
            while not self.done_event.is_set():
                if not self.training_active_flag():
                    logger.info("Training has stopped; ending render loop.")
                    break

                if self.model_updated_flag.is_set():
                    self._cache_policy()
                    self.model_updated_flag.clear()

                try:
                    with torch.no_grad():
                        action, _ = self.cached_policy.predict(self.obs, deterministic=True)
                    self.obs, _, done, _ = self.render_env.step(action)
                    render_frame_to_queue(self.render_env)
                    if done:
                        self.obs = self.render_env.reset()
                except Exception as e:
                    logger.error("Error during rendering loop iteration.", exception=e)
                    break
        except Exception as e:
            logger.error("Failed to initialize rendering loop.", exception=e)
        finally:
            self.rendering_active.clear()
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
            self.rendering_active.clear()

    def is_rendering(self):
        """Return the rendering status."""
        return self.rendering_active.is_set()

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
            clear_frame_queue()
            logger.info("RenderManager stopped successfully.")
        except Exception as e:
            logger.error("Error stopping RenderManager.", exception=e)
