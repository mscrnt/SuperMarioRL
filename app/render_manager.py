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


def apply_crt_shader(frame, time, rolling_interval=3, crt_shader_enabled=False):
    """
    Apply a CRT-like shader effect with radial distortion, scanlines, RCA-style dot mask, and rolling lines.
    """

    if not crt_shader_enabled:
        logger.info("CRT shader effect disabled.")
        return frame

    height, width, _ = frame.shape

    # Step 1: Normalize the frame to [0, 1] for processing
    frame_normalized = frame.astype(np.float32) / 255.0

    # Step 2: Apply radial distortion
    distortion = 0.2
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

    # Step 4: RCA-style shadow mask
    mask_dark = 0.8  # Increased the base brightness
    mask_light = 1.1  # Reduced the contrast between dark and light
    dot_mask = np.ones((height, width, 3), dtype=np.float32) * mask_dark

    for i in range(height):
        for j in range(width):
            # Alternating subpixel emphasis
            if (j % 3 == 0):
                dot_mask[i, j, 0] = mask_light  # Red
            elif (j % 3 == 1):
                dot_mask[i, j, 1] = mask_light  # Green
            elif (j % 3 == 2):
                dot_mask[i, j, 2] = mask_light  # Blue

    frame_with_dot_mask = frame_with_scanlines * dot_mask


    # Step 5: Add rolling lines (hum bars) effect
    if int(time) % rolling_interval == 0:  # Less frequent based on rolling_interval
        rolling_amplitude = 0.02  # Subtle effect
        rolling_frequency = 2  # Slower bars
        rolling_lines = (
            np.sin(2 * np.pi * rolling_frequency * (y + ((time / 2) % 1))) * rolling_amplitude + 1.0
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


def render_frame_to_queue(frame, crt_shader_enabled):
    """
    Render a frame, apply shader effects, and place it in the frame queue.

    :param frame: The rendered frame (as a NumPy array).
    :param crt_shader_enabled: Whether to apply the CRT shader effect.
    """
    try:
        current_time = time.time()
        processed_frame = apply_crt_shader(
            frame, current_time, rolling_interval=1, crt_shader_enabled=crt_shader_enabled
        )

        if frame_queue.full():
            discarded_frame = frame_queue.get_nowait()  # Discard the oldest frame
            logger.debug("Discarded oldest frame to make room in queue.", discarded_frame=discarded_frame)

        frame_queue.put_nowait(processed_frame)
        logger.debug("Frame added to queue successfully.")
    except queue.Full:
        logger.warning("Frame queue is full; skipping frame.")
    except Exception as e:
        logger.error("Rendering failed", exception=e)





def generate_frame_stream(frame_rate=120):
    """
    Generator function to stream frames as MJPEG.
    """
    interval = 1.0 / frame_rate
    while True:
        try:
            frame = frame_queue.get(timeout=1)  # Avoid indefinite blocking
            _, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(interval)
        except queue.Empty:
            logger.warning("Frame queue is empty; waiting for new frames.")
        except Exception as e:
            logger.error("Error generating frame stream.", exception=e)



class RenderManager:
    """
    Manages rendering in a separate thread to ensure it does not block training.
    """
    def __init__(self, render_env, model, cache_update_interval=120, training_active_flag=None, model_updated_flag=None, crt_shader_flag=None):
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
        self.crt_shader_flag = crt_shader_flag or (lambda: False)  # Default to CRT shader disabled
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
        Rendering loop with separate timing for logic updates and frame rendering.
        """
        try:
            self.obs = self.render_env.reset()
            self.rendering_active.set()
            logger.info("Rendering thread started successfully.")

            render_interval = 1 / target_render_fps
            logic_interval = 1 / logic_fps

            last_render_time = time.time()
            last_logic_time = last_render_time

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

                # Update game logic
                if current_time - last_logic_time >= logic_interval:
                    try:
                        with torch.no_grad():
                            action, _ = self.cached_policy.predict(self.obs, deterministic=True)
                        self.obs, _, done, _ = self.render_env.step(action)

                        last_logic_frame = current_logic_frame
                        current_logic_frame = self.render_env.render(mode="rgb_array")

                        if done:
                            self.obs = self.render_env.reset()
                    except Exception as e:
                        logger.error("Error during logic update.", exception=e)

                    last_logic_time = current_time

                # Render a frame
                if current_time - last_render_time >= render_interval:
                    try:
                        alpha = (current_time - last_logic_time) / logic_interval
                        alpha = max(0.0, min(1.0, alpha))

                        interpolated_frame = self._interpolate_frames(
                            last_logic_frame, current_logic_frame, alpha
                        )

                        crt_shader_enabled = self.crt_shader_flag()
                        render_frame_to_queue(interpolated_frame, crt_shader_enabled)
                    except Exception as e:
                        logger.error("Error during frame rendering.", exception=e)

                    last_render_time = current_time

                time.sleep(0.001)  # Prevent busy-waiting
        except Exception as e:
            logger.error("Rendering loop failed.", exception=e)
        finally:
            self.rendering_active.clear()
            logger.info("Rendering thread stopped.")

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
