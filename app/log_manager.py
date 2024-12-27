# path: ./log_manager.py

from icecream import ic
from multiprocessing import Queue
import colorama
from colorama import Fore, Style
import inspect
import os
import traceback
from concurrent_log_handler import ConcurrentRotatingFileHandler
import logging
from datetime import datetime
import re

colorama.init(autoreset=True)

# Shared queue for UI logging
log_queue = Queue()

# Assign unique colors for loggers
COLOR_MAP = {}
COLORS = [
    Fore.GREEN,
    Fore.YELLOW,
    Fore.CYAN,
    Fore.MAGENTA,
    Fore.BLUE,
    Fore.RED,
    Fore.WHITE,
    Fore.LIGHTGREEN_EX,
    Fore.LIGHTYELLOW_EX,
    Fore.LIGHTCYAN_EX,
    Fore.LIGHTMAGENTA_EX,
    Fore.LIGHTBLUE_EX,
    Fore.LIGHTWHITE_EX,
]


def assign_color(name):
    """
    Assign a unique color to each logger based on its name.
    """
    if name not in COLOR_MAP:
        COLOR_MAP[name] = COLORS[len(COLOR_MAP) % len(COLORS)]
    return COLOR_MAP[name]


def strip_ansi_escape_sequences(message):
    """
    Remove ANSI escape sequences (color codes) from a message.
    """
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x9B\x1B][\[()#;?]*[ -/]*[@-~])')
    return ansi_escape.sub("", message)


def send_to_ui_log(message):
    """
    Send clean logs to the shared queue for the UI.
    """
    clean_message = strip_ansi_escape_sequences(message)
    log_queue.put(clean_message)


def configure_ic_logger(name, color):
    """
    Configure IceCream logger with unique colors and contextual information.
    """
    def custom_prefix():
        now = datetime.now().strftime("%H:%M:%S")
        return f"{color}[{name}] {now} | "

    ic.configureOutput(prefix=custom_prefix, includeContext=True)
    return ic


class LogManager:
    """
    Manages logging for debugging with IceCream and traditional logging.
    """
    _instances = {}
    log_file = "./logs/app.log"  # Default log file location

    def __new__(cls, name=None):
        if name is None:
            frame = inspect.currentframe().f_back
            name = os.path.basename(frame.f_code.co_filename).replace(".py", "")
        if name not in cls._instances:
            instance = super(LogManager, cls).__new__(cls)
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name=None):
        if hasattr(self, "initialized"):
            return
        self.initialized = True

        if name is None:
            frame = inspect.currentframe().f_back
            name = os.path.basename(frame.f_code.co_filename).replace(".py", "")
        self.name = name
        self.color = assign_color(name)

        # Set up logger
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)  # Capture all log levels
        self._setup_handlers()

        # Configure IceCream for this logger
        self.ic = configure_ic_logger(self.name, self.color)
        self.logger.debug(f"Logger initialized for {self.name}")

    def _setup_handlers(self):
        """
        Set up handlers for file, terminal, and UI logs.
        """
        self.logger.handlers.clear()

        # Ensure log file directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # File Handler
        file_handler = ConcurrentRotatingFileHandler(
            self.log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"))
        self.logger.addHandler(file_handler)

        # UI Handler
        ui_handler = logging.StreamHandler()
        ui_handler.setLevel(logging.INFO)
        ui_handler.setFormatter(logging.Formatter("%(message)s"))
        ui_handler.emit = lambda record: self._emit_to_ui(record)
        self.logger.addHandler(ui_handler)

        # Terminal Handler
        terminal_handler = logging.StreamHandler()
        terminal_handler.setLevel(logging.INFO)
        terminal_handler.setFormatter(logging.Formatter("%(message)s"))  # Add color dynamically
        terminal_handler.emit = lambda record: self._emit_to_terminal(record)
        self.logger.addHandler(terminal_handler)

    def _emit_to_ui(self, record):
        """
        Process logs for UI display.
        """
        # Extract clean message
        message = strip_ansi_escape_sequences(record.getMessage())
        # Strip logger name, timestamps, and levels
        clean_message = re.sub(r"\[.*?\] ", "", message, count=1)
        send_to_ui_log(clean_message)

    def _emit_to_terminal(self, record):
        """
        Process logs for terminal display.
        """
        # Add color dynamically for terminal
        level_color = self._get_level_color(record.levelname)
        formatted_message = f"{self.color}[{self.name}] {record.getMessage()}"  # No level in the message
        print(f"{level_color}{formatted_message}{Style.RESET_ALL}")

    def _get_level_color(self, levelname):
        """
        Map log levels to specific colors.
        """
        color_map = {
            "DEBUG": Fore.CYAN,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
        }
        return color_map.get(levelname, Fore.WHITE)

    def debug(self, *args, **kwargs):
        self.logger.debug(self._format_message(*args, **kwargs))

    def info(self, *args, **kwargs):
        self.logger.info(self._format_message(*args, **kwargs))

    def warning(self, *args, **kwargs):
        self.logger.warning(self._format_message(*args, **kwargs))

    def error(self, *args, exception=None, **kwargs):
        if exception:
            traceback_details = "".join(traceback.format_exception(None, exception, exception.__traceback__))
            kwargs["traceback"] = traceback_details
        self.logger.error(self._format_message(*args, **kwargs))

    def _format_message(self, *args, **kwargs):
        """
        Format the log message body only, without log level or metadata.
        """
        args_message = " ".join(map(str, args))
        kwargs_message = ", ".join(f"{key}={value}" for key, value in kwargs.items())
        return f"{args_message} {kwargs_message}".strip()
