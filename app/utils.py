# path: ./utils.py

import gym_super_mario_bros
import cv2
from log_manager import LogManager
import time
import queue
from abc import ABC
from inspect import signature
from preprocessing import MaxAndSkipEnv, MarioRescale84x84, PixelNormalization, ImageToPyTorch
from gym_super_mario_bros.actions import COMPLEX_MOVEMENT
from nes_py.wrappers import JoypadSpace

# Initialize a logger specific to this module
logger = LogManager("utils")

# Queue to share rendered frames for streaming
frame_queue = queue.Queue(maxsize=50)


class load_blueprints(ABC):
    """
    A universal blueprint for defining components like callbacks and wrappers.
    """

    def __init__(
        self,
        component_class,
        component_type,
        required=False,
        default_params=None,
        arg_map=None,
        name=None,
        description=None,
    ):
        if component_type not in {"callback", "wrapper"}:
            raise ValueError(f"Invalid component type: {component_type}. Must be 'callback' or 'wrapper'.")

        self.component_class = component_class
        self.component_type = component_type
        self.required = required
        self.default_params = default_params or {}
        self.arg_map = arg_map or {}
        self.name = name or component_class.__name__
        self.description = description or "No description provided."

    def is_required(self):
        """Check if the blueprint is required."""
        return self.required

    def create_instance(self, config=None, env=None, **override_params):
        """
        Create an instance of the component with optional parameter overrides.

        :param config: Configuration dictionary to resolve dynamic arguments.
        :param env: Environment to be passed to wrappers that require it.
        :param override_params: Parameters to override the defaults.
        :return: An instance of the component.
        """
        # Combine default parameters with overrides
        params = {**self.default_params, **override_params}

        # Automatically resolve arguments based on the configuration and arg_map
        if config and self.arg_map:
            for arg_name, config_key in self.arg_map.items():
                if config_key in config and arg_name not in params:
                    params[arg_name] = config[config_key]

        # Add the `env` argument for wrappers
        if self.component_type == "wrapper":
            logger.debug(f"Checking env argument for wrapper {self.name}")
            if env is None:
                logger.error(f"The 'env' argument is missing for wrapper {self.name}.")
                raise ValueError(f"The 'env' argument is required for wrapper {self.name}.")
            params["env"] = env

        # Validate arguments against the component's signature
        component_sig = signature(self.component_class)
        valid_params = {k: v for k, v in params.items() if k in component_sig.parameters}

        # Debug: Log final parameters passed to the component
        logger.debug(f"Creating {self.component_class.__name__} with parameters: {valid_params}")
        return self.component_class(**valid_params)


def create_mario_env(env, wrappers_order):
    """
    Applies a fixed order of wrappers to the environment.

    :param env: Base environment to be wrapped.
    :param wrappers_order: List of wrapper callables or blueprints to apply.
    :return: Fully wrapped environment.
    """
    for wrapper in wrappers_order:
        if callable(wrapper):
            # If the wrapper is callable, call it directly
            env = wrapper(env)
        elif isinstance(wrapper, tuple):
            # If the wrapper requires arguments, unpack and call
            wrapper_func, args, kwargs = wrapper
            if isinstance(wrapper_func, load_blueprints):
                # Handle blueprint-specific instance creation
                env = wrapper_func.create_instance(env=env, **kwargs)
            else:
                # Handle direct wrapper functions
                env = wrapper_func(env, *args, **kwargs)
    return env



def create_env(random_stages=False, stages=None, env_index=1, selected_wrappers=None, blueprints=None):
    """
    Creates and wraps the Super Mario environment with dynamic wrapper application.
    
    :param random_stages: Whether to use random stages in the environment.
    :param stages: A list of specific stages to include (used with random_stages=True).
    :param env_index: Index of the environment for logging and configuration.
    :param selected_wrappers: Names of wrappers to apply dynamically.
    :param blueprints: Dictionary of wrapper blueprints to use for dynamic application.
    :return: A callable function that initializes and returns the wrapped environment.
    """
    def _init():
        env_logger = LogManager(f"env_{env_index}")
        env_logger.info(f"Initializing environment {env_index}")

        # Debug: Log selected wrappers and blueprints
        env_logger.debug(f"Selected wrappers: {selected_wrappers}")
        env_logger.debug(f"Available blueprints: {list(blueprints.keys())}")

        # Create base environment
        if random_stages:
            env = gym_super_mario_bros.make("SuperMarioBrosRandomStages-v0", stages=stages)
            env_logger.debug(f"Base environment created with random stages: {stages}")
        else:
            env = gym_super_mario_bros.make("SuperMarioBros-v0")
            env_logger.debug("Base environment created without random stages.")

        # Predefined wrappers in the desired order with required arguments
        wrappers_order = [
            (JoypadSpace, [COMPLEX_MOVEMENT], {}),
            (MaxAndSkipEnv, [], {}),
            (MarioRescale84x84, [], {}),
        ]

        # Process dynamically selected wrappers
        if selected_wrappers and blueprints:
            unique_wrapper_keys = set()
            for wrapper_name in selected_wrappers:
                env_logger.debug(f"Processing wrapper: {wrapper_name}")
                # Match blueprint by friendly name or component class name
                blueprint = next(
                    (bp for bp in blueprints.values()
                     if bp.name == wrapper_name or bp.component_class.__name__ == wrapper_name),
                    None,
                )
                if blueprint:
                    # Avoid duplicates
                    if blueprint.component_class.__name__ not in unique_wrapper_keys:
                        wrappers_order.append((blueprint, [], {"config": {"env_index": env_index}}))
                        unique_wrapper_keys.add(blueprint.component_class.__name__)
                        env_logger.info(f"Wrapper {blueprint.name} added to the order.")
                    else:
                        env_logger.warning(f"Duplicate wrapper {blueprint.name} ignored.")
                else:
                    env_logger.warning(f"Wrapper {wrapper_name} not found in blueprints. Skipping.")

        # Add final wrappers
        wrappers_order.extend([
            (PixelNormalization, [], {}),
            (ImageToPyTorch, [], {}),
        ])

        # Deduplicate wrappers to ensure order is maintained without redundancy
        seen_wrappers = set()
        deduplicated_wrappers_order = []
        for wrapper in wrappers_order:
            wrapper_key = wrapper[0].__name__ if callable(wrapper[0]) else wrapper[0].name
            if wrapper_key not in seen_wrappers:
                deduplicated_wrappers_order.append(wrapper)
                seen_wrappers.add(wrapper_key)

        # Apply all wrappers in the deduplicated order
        env_logger.debug(
            "Applying wrappers in order: "
            + ", ".join(
                [w[0].__name__ if callable(w[0]) else w[0].name for w in deduplicated_wrappers_order]
            )
        )
        env = create_mario_env(env, deduplicated_wrappers_order)

        env_logger.info(f"Environment {env_index} initialized successfully with all wrappers.")
        return env

    return _init

def render_frame_to_queue(first_env, throttle_interval=0.05):
    """
    Render a frame and place it in the frame queue for streaming.

    :param first_env: The environment to render frames from.
    :param throttle_interval: Interval between frame captures.
    """
    try:
        frame = first_env.render(mode="rgb_array")
        if frame_queue.full():
            discarded_frame = frame_queue.get_nowait()
            logger.debug("Discarded oldest frame due to queue overflow", frame=discarded_frame)
        frame_queue.put(frame, block=False)
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


def linear_schedule(initial_value, final_value=0.0):
    """
    Linear learning rate schedule.

    :param initial_value: Initial value of the parameter.
    :param final_value: Final value of the parameter.
    :return: A function to compute the parameter value based on progress.
    """
    if isinstance(initial_value, str):
        initial_value = float(initial_value)
        final_value = float(final_value)
        assert initial_value > 0.0, "linear_schedule works only with positive decreasing values"

    def func(progress):
        value = final_value + progress * (initial_value - final_value)
        logger.debug("Linear schedule computed", initial=initial_value, final=final_value, progress=progress, value=value)
        return value

    return func


def clear_frame_queue():
    """
    Clears all frames from the frame queue.
    """
    discarded_frames = 0
    while not frame_queue.empty():
        frame_queue.get_nowait()
        discarded_frames += 1
    logger.info("Frame queue cleared", discarded_frames=discarded_frames)
