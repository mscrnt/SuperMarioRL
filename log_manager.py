# path: ./log_manager.py

from icecream import ic, install
from multiprocessing import Queue, current_process
import colorama
from colorama import Fore, Style
import inspect
import os
import traceback
from concurrent_log_handler import ConcurrentRotatingFileHandler
import logging

colorama.init(autoreset=True)

# Shared queue for UI logging
log_queue = Queue()

# Assign unique colors for loggers
COLOR_MAP = {}
COLORS = [Fore.GREEN, Fore.YELLOW, Fore.CYAN, Fore.MAGENTA, Fore.BLUE]


def assign_color(name):
    """
    Assign a unique color to each logger based on its name.
    """
    if name not in COLOR_MAP:
        COLOR_MAP[name] = COLORS[len(COLOR_MAP) % len(COLORS)]
    return COLOR_MAP[name]


def send_to_ui_log(message):
    """
    Send logs to the shared queue for the UI.
    """
    log_queue.put(message)


# Configure IceCream to support dual output (terminal + UI)
def dual_output(message):
    """
    Send logs to both the terminal and UI.
    """
    print(message)  # Terminal output
    send_to_ui_log(message)  # UI queue


ic.configureOutput(
    prefix="",
    includeContext=True,
    outputFunction=dual_output  # Dual output configuration
)


class LevelFilter(logging.Filter):
    """
    Filters logs for specific levels.
    """
    def __init__(self, levels):
        super().__init__()
        self.levels = levels

    def filter(self, record):
        return record.levelno in self.levels


class LogManager:
    """
    Manages logging for simplified and contextual debugging.
    """
    _instances = {}
    log_file = "./logs/app.log"  # Default log file location

    def __new__(cls, name=None):
        """
        Singleton to ensure one instance per logger name.
        """
        if name is None:
            frame = inspect.currentframe().f_back
            name = os.path.basename(frame.f_code.co_filename).replace(".py", "")
        if name not in cls._instances:
            instance = super(LogManager, cls).__new__(cls)
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name=None):
        """
        Initialize the logger and assign a unique color.
        """
        if hasattr(self, "initialized"):
            return
        self.initialized = True

        if name is None:
            frame = inspect.currentframe().f_back
            name = os.path.basename(frame.f_code.co_filename).replace(".py", "")
        self.name = name
        self.color = assign_color(name)

        # Set up a logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)  # Capture all log levels
        self._setup_handlers()

    def _setup_handlers(self):
        """
        Set up handlers for terminal, UI, and file logging.
        """
        self.logger.handlers.clear()

        # Ensure log file directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # Terminal handler
        terminal_handler = logging.StreamHandler()
        terminal_handler.setLevel(logging.INFO)
        terminal_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
        self.logger.addHandler(terminal_handler)

        # Concurrent rotating file handler
        file_handler = ConcurrentRotatingFileHandler(
            self.log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
        self.logger.addHandler(file_handler)

        # UI handler
        ui_handler = logging.StreamHandler()
        ui_handler.setLevel(logging.INFO)
        ui_handler.addFilter(LevelFilter([logging.INFO, logging.ERROR]))
        ui_handler.setFormatter(logging.Formatter("%(name)s - %(message)s"))
        ui_handler.emit = lambda record: send_to_ui_log(ui_handler.format(record))
        self.logger.addHandler(ui_handler)

    def _format_message(self, level, *args, **kwargs):
        """
        Format the log message for readability.
        """
        args_message = " ".join(map(str, args))
        kwargs_message = ", ".join(f"{key}={value}" for key, value in kwargs.items())
        return f"{args_message} {kwargs_message}".strip()

    def log(self, level, *args, **kwargs):
        """
        Log a message with the specified level, arguments, and keyword arguments.
        """
        formatted_message = self._format_message(level, *args, **kwargs)
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(formatted_message)

    def debug(self, *args, **kwargs):
        """
        Debug-level logging.
        """
        self.logger.debug(self._format_message("DEBUG", *args, **kwargs))

    def info(self, *args, **kwargs):
        """
        Info-level logging.
        """
        self.logger.info(self._format_message("INFO", *args, **kwargs))

    def warning(self, *args, **kwargs):
        """
        Warning-level logging.
        """
        self.logger.warning(self._format_message("WARNING", *args, **kwargs))

    def error(self, *args, exception=None, **kwargs):
        """
        Error-level logging with exception details if provided.
        """
        if exception:
            traceback_details = "".join(traceback.format_exception(None, exception, exception.__traceback__))
            kwargs["traceback"] = traceback_details
        self.logger.error(self._format_message("ERROR", *args, **kwargs))
