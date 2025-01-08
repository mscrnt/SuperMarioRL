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


def apply_crt_shader(frame, time, rolling_interval=3):  # Less frequent with increased interval
    """
    Apply a CRT-like shader effect with radial distortion, scanlines, dot mask, and rolling lines.
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
    mod_factor = np.arange(width) % 3
    dot_mask_weights = np.zeros((1, width, 3), dtype=np.float32)
    dot_mask_weights[:, mod_factor == 0, 0] = 1.05  # Red
    dot_mask_weights[:, mod_factor == 1, 1] = 1.05  # Green
    dot_mask_weights[:, mod_factor == 2, 2] = 1.05  # Blue
    dot_mask_weights[:, :, :] = np.where(dot_mask_weights == 0, 0.8, dot_mask_weights)
    dot_mask_weights = np.tile(dot_mask_weights, (height, 1, 1))
    frame_with_dot_mask = frame_with_scanlines * dot_mask_weights

    # Step 5: Add rolling lines (hum bars) effect
    if int(time) % rolling_interval == 0:  # Less frequent based on rolling_interval
        rolling_amplitude = 0.02  # Subtle effect
        rolling_frequency = 2  # Slower bars
        rolling_lines = (
            np.sin(2 * np.pi * rolling_frequency * (y + (time % 1))) * rolling_amplitude + 1.0
        )
        rolling_lines = rolling_lines.reshape(height, width, 1)  # Match frame dimensions
        frame_with_rolling_lines = frame_with_dot_mask * rolling_lines
    else:
        frame_with_rolling_lines = frame_with_dot_mask

    # Step 6: Apply gamma correction
    input_gamma = 2.2
    output_gamma = 2.5
    frame_gamma_corrected = np.clip(frame_with_rolling_lines ** (input_gamma / output_gamma), 0, 1)

    # Scale back to [0, 255] for display
    frame_output = (frame_gamma_corrected * 255).astype(np.uint8)

    return frame_output



def render_frame_to_queue(frame):
    """
    Render a frame, apply shader effects, and place it in the frame queue.

    :param frame: The rendered frame (as a NumPy array).
    """
    try:
        # Apply CRT shader effects
        current_time = time.time()
        processed_frame = apply_crt_shader(frame, current_time, rolling_interval=1)

        # Manage the frame queue
        if frame_queue.full():
            discarded_frame = frame_queue.get_nowait()
            logger.debug("Discarded oldest frame due to queue overflow", discarded_frame=discarded_frame)

        frame_queue.put(processed_frame, block=False)
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


    def _render_loop(self, target_render_fps=60, logic_fps=12):
        """
        Rendering loop with fine-tuned interpolation and frame padding for smoother gameplay.
        
        :param target_render_fps: The target FPS for rendering (e.g., 60).
        :param logic_fps: The target FPS for game logic updates (e.g., 24).
        """
        try:
            self.obs = self.render_env.reset()
            self.rendering_active.set()
            logger.info("Rendering thread started successfully.")

            # Calculate intervals for rendering and logic
            render_interval = 1 / target_render_fps
            logic_interval = 1 / logic_fps

            # Time tracking for logic and rendering
            last_render_time = time.time()
            last_logic_time = last_render_time

            # Store the last two logic frames for interpolation
            last_logic_frame = self.render_env.render(mode="rgb_array")
            current_logic_frame = last_logic_frame

            while not self.done_event.is_set():
                if not self.training_active_flag():
                    logger.info("Training has stopped; ending render loop.")
                    break

                if self.model_updated_flag.is_set():
                    self._cache_policy()
                    self.model_updated_flag.clear()

                current_time = time.time()

                # Update game logic if enough time has passed
                while current_time - last_logic_time >= logic_interval:
                    try:
                        with torch.no_grad():
                            action, _ = self.cached_policy.predict(self.obs, deterministic=True)
                        self.obs, _, done, info = self.render_env.step(action)

                        # Shift logic frames for interpolation
                        last_logic_frame = current_logic_frame
                        current_logic_frame = self.render_env.render(mode="rgb_array")

                        # Extract the game timer from `stats`
                        game_timer = info.get("stats", {}).get("time", 0)
                        logger.debug(
                            f"Logic updated | Game Timer Countdown: {game_timer}",
                            elapsed_time=current_time - last_logic_time,
                            logic_interval=logic_interval,
                            current_time=current_time,
                            last_logic_time=last_logic_time
                        )
                        last_logic_time += logic_interval  # Use fixed intervals for consistency

                        if done:
                            self.obs = self.render_env.reset()
                    except Exception as e:
                        logger.error("Error during logic update.", exception=e)

                # Render a frame if enough time has passed
                if current_time - last_render_time >= render_interval:
                    try:
                        # Interpolate or duplicate the logic frames
                        time_since_last_logic = current_time - last_logic_time
                        alpha = max(0.0, min(1.0, time_since_last_logic / logic_interval))

                        # Use the last frame if logic hasn't updated
                        interpolated_frame = self._interpolate_frames(
                            last_logic_frame, current_logic_frame, alpha
                        )

                        # Render the interpolated frame
                        render_frame_to_queue(interpolated_frame)
                        logger.debug(
                            "Frame rendered",
                            elapsed_time=current_time - last_render_time,
                            render_interval=render_interval,
                            current_time=current_time,
                            last_render_time=last_render_time,
                            alpha=alpha
                        )
                        last_render_time = current_time
                    except Exception as e:
                        logger.error("Error during frame rendering.", exception=e)

                # Sleep for the remaining time in the shortest interval
                next_event_time = min(
                    last_logic_time + logic_interval,
                    last_render_time + render_interval,
                )
                sleep_time = max(0, next_event_time - time.time())
                time.sleep(sleep_time)

        except Exception as e:
            logger.error("Failed to initialize rendering loop.", exception=e)
        finally:
            self.rendering_active.clear()
            logger.info("Rendering thread has stopped.")



    def _interpolate_frames(self, frame1, frame2, alpha):
        """
        Interpolate between two frames using the provided alpha.
        
        :param frame1: The first logic frame (previous).
        :param frame2: The second logic frame (current).
        :param alpha: Interpolation factor between 0 and 1.
        :return: Interpolated frame.
        """
        return cv2.addWeighted(frame1, 1 - alpha, frame2, alpha, 0)




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
