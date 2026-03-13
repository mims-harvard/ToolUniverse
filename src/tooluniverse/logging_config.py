"""
Global logging configuration for ToolUniverse

This module provides a centralized logging system based on Python's standard logging module.
It allows controlling debug output across the entire ToolUniverse project with different
verbosity levels.

Usage:
    # Set log level via environment variable
    export TOOLUNIVERSE_LOG_LEVEL=DEBUG

    # Or set programmatically
    from tooluniverse.logging_config import setup_logging, get_logger
    setup_logging('DEBUG')

    # Use in your code
    logger = get_logger(__name__)
    logger.info("This is an info message")
    logger.debug("This is a debug message")
"""

import logging
import os
import sys
from typing import Optional, Callable

# Define custom log levels
PROGRESS_LEVEL = 25  # Between INFO(20) and WARNING(30)
logging.addLevelName(PROGRESS_LEVEL, "PROGRESS")


class ToolUniverseFormatter(logging.Formatter):
    """Custom formatter with colored output and emoji prefixes"""

    # Color codes for different log levels
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "PROGRESS": "\033[34m",  # Blue
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    # Emoji prefixes for different log levels
    EMOJI_PREFIX = {
        "DEBUG": "🔧 ",
        "INFO": "ℹ️  ",
        "PROGRESS": "⏳ ",
        "WARNING": "⚠️  ",
        "ERROR": "❌ ",
        "CRITICAL": "🚨 ",
    }

    def format(self, record):
        # Add emoji prefix
        emoji = self.EMOJI_PREFIX.get(record.levelname, "")

        # Add color if output is to terminal
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, "")
            reset = self.COLORS["RESET"]
            record.levelname = f"{color}{record.levelname}{reset}"

        # Format the message
        formatted = super().format(record)
        return f"{emoji}{formatted}"


class ToolUniverseLogger:
    """
    Singleton logger manager for ToolUniverse
    """

    _instance = None
    _logger = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._setup_logger()
            self._initialized = True

    def _setup_logger(self):
        """Setup the main ToolUniverse logger"""
        self._logger = logging.getLogger("tooluniverse")

        # Remove existing handlers to avoid duplicates
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # Set initial level from environment or default to INFO
        initial_level = os.getenv("TOOLUNIVERSE_LOG_LEVEL", "INFO").upper()
        try:
            level = getattr(logging, initial_level)
        except AttributeError:
            level = logging.INFO

        self._logger.setLevel(level)

        # Create console handler - use stderr for stdio mode
        output_stream = (
            sys.stderr if os.getenv("TOOLUNIVERSE_STDIO_MODE") == "1" else sys.stdout
        )
        handler = logging.StreamHandler(output_stream)
        handler.setLevel(level)

        # Create formatter
        formatter = ToolUniverseFormatter(
            fmt="%(message)s",  # Simple format since we add emoji prefix
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        self._logger.addHandler(handler)

    def reconfigure_for_stdio(self):
        """Reconfigure logger to output to stderr for stdio mode"""
        # Remove existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # Get current level
        level = self._logger.level

        # Create new handler with stderr
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)

        # Create formatter
        formatter = ToolUniverseFormatter(
            fmt="%(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)

        # Add handler to logger
        self._logger.addHandler(handler)

        # Prevent propagation to root logger
        self._logger.propagate = False

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a logger instance"""
        if name:
            return logging.getLogger(f"tooluniverse.{name}")
        # Fallback to module logger if not initialized
        return (
            self._logger
            if self._logger is not None
            else logging.getLogger("tooluniverse")
        )

    def set_level(self, level: str) -> None:
        """Set logging level"""
        try:
            log_level = getattr(logging, level.upper())
            if self._logger is None:
                return
            self._logger.setLevel(log_level)
            for handler in self._logger.handlers:
                handler.setLevel(log_level)
        except AttributeError:
            if self._logger is not None:
                self._logger.warning(
                    f"Invalid log level: {level}. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL"
                )


# Global logger instance
_logger_manager = ToolUniverseLogger()


def reconfigure_for_quiet() -> None:
    """
    Reconfigure logging to suppress INFO-level messages (quiet mode).

    This function should be called after TOOLUNIVERSE_QUIET is set to ensure
    that ℹ️ info lines are suppressed even if the logger singleton was already
    initialized before the env var was exported.
    """
    _logger_manager.set_level("WARNING")


def reconfigure_for_stdio() -> None:
    """
    Reconfigure logging to output to stderr for stdio mode.

    This function should be called at the very beginning of stdio mode
    to ensure all logs go to stderr instead of stdout.
    """
    _logger_manager.reconfigure_for_stdio()
    # Ensure third-party rich/traceback pretty outputs do not go to stdout
    try:
        import rich
        from rich.console import Console

        # Redirect rich default console to stderr in stdio mode
        rich_console = Console(
            file=sys.stderr,
            force_terminal=False,
            markup=False,
            highlight=False,
            emoji=False,
            soft_wrap=False,
        )
        rich.get_console = lambda: rich_console
    except Exception:
        pass
    # Force Python warnings and tracebacks to stderr
    try:
        import warnings

        warnings.showwarning = (
            lambda message, category, filename, lineno, file=None, line=None: print(
                warnings.formatwarning(message, category, filename, lineno, line),
                file=sys.stderr,
            )
        )
    except Exception:
        pass


def setup_logging(level: Optional[str] = None) -> None:
    """
    Setup global logging configuration

    Args:
        level (str): Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    if level:
        _logger_manager.set_level(level)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance

    Args:
        name (str, optional): Logger name (usually __name__)

    Returns
        logging.Logger: Logger instance
    """
    return _logger_manager.get_logger(name)


def set_log_level(level: str) -> None:
    """Set global log level"""
    _logger_manager.set_level(level)


# Convenience functions using the main logger
_main_logger = get_logger()


def debug(msg, *args, **kwargs):
    """Log debug message"""
    _main_logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    """Log info message"""
    _main_logger.info(msg, *args, **kwargs)


def progress_log(msg, *args, **kwargs) -> None:
    """Log progress message"""
    # Preserve dedicated PROGRESS level without monkey-patching Logger
    _main_logger.log(PROGRESS_LEVEL, msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    """Log warning message"""
    _main_logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    """Log error message"""
    _main_logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    """Log critical message"""
    _main_logger.critical(msg, *args, **kwargs)


# For backward compatibility
minimal = info  # Alias minimal to info
verbose = debug  # Alias verbose to debug
progress: Callable[..., None] = progress_log  # Alias for convenience


def get_hook_logger(name: str = "HookManager") -> logging.Logger:
    """
    Get a logger specifically configured for hook operations.

    Args:
        name (str): Name of the logger. Defaults to 'HookManager'

    Returns
        logging.Logger: Configured logger for hook operations
    """
    return get_logger(name)


def log_hook_execution(
    hook_name: str, tool_name: str, execution_time: float, success: bool
):
    """
    Log hook execution details for monitoring and debugging.

    Args:
        hook_name (str): Name of the hook that was executed
        tool_name (str): Name of the tool the hook was applied to
        execution_time (float): Time taken to execute the hook in seconds
        success (bool): Whether the hook execution was successful
    """
    logger = get_hook_logger()
    status = "SUCCESS" if success else "FAILED"
    logger.info(
        f"Hook {hook_name} for tool {tool_name}: {status} ({execution_time:.2f}s)"
    )
