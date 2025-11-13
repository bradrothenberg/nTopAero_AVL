"""Verbose logging system with timestamped progress messages."""

import sys
from datetime import datetime
from enum import Enum
from typing import Optional

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class LogLevel(Enum):
    """Log message levels."""
    DEBUG = 0
    INFO = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4


class VerboseLogger:
    """
    Logger with hierarchical indentation and color-coded output.

    Features:
    - Timestamped messages
    - Hierarchical indentation for nested operations
    - Color-coded output (warnings, errors, success)
    - Toggle verbose/quiet modes
    """

    def __init__(self, verbose: bool = True, use_colors: bool = True) -> None:
        """
        Initialize the logger.

        Args:
            verbose: Enable verbose output
            use_colors: Use color-coded output (if colorama available)
        """
        self.verbose = verbose
        self.use_colors = use_colors and COLORAMA_AVAILABLE
        self._indent_level = 0
        self._last_was_progress = False

    def _format_timestamp(self) -> str:
        """Get formatted timestamp."""
        return datetime.now().strftime("%H:%M:%S")

    def _colorize(self, text: str, level: LogLevel) -> str:
        """Apply color to text based on log level."""
        if not self.use_colors:
            return text

        color_map = {
            LogLevel.DEBUG: Fore.CYAN,
            LogLevel.INFO: Fore.WHITE,
            LogLevel.SUCCESS: Fore.GREEN,
            LogLevel.WARNING: Fore.YELLOW,
            LogLevel.ERROR: Fore.RED,
        }

        return f"{color_map[level]}{text}{Style.RESET_ALL}"

    def _get_prefix(self, level: LogLevel) -> str:
        """Get message prefix based on level."""
        prefix_map = {
            LogLevel.DEBUG: "  ->",
            LogLevel.INFO: "  ->",
            LogLevel.SUCCESS: "  [OK]",
            LogLevel.WARNING: "  [WARN]",
            LogLevel.ERROR: "  [ERR]",
        }
        return prefix_map[level]

    def _log(self, message: str, level: LogLevel, indent_offset: int = 0) -> None:
        """
        Internal logging method.

        Args:
            message: Message to log
            level: Log level
            indent_offset: Additional indentation (can be negative)
        """
        if not self.verbose and level not in [LogLevel.WARNING, LogLevel.ERROR]:
            return

        timestamp = self._format_timestamp()
        indent = "  " * (self._indent_level + indent_offset)
        prefix = self._get_prefix(level)

        # Format the line
        line = f"[{timestamp}] {indent}{prefix} {message}"

        # Colorize if enabled
        if self.use_colors:
            line = self._colorize(line, level)

        # Print to stderr for errors, stdout otherwise
        output = sys.stderr if level == LogLevel.ERROR else sys.stdout
        print(line, file=output)
        self._last_was_progress = False

    def debug(self, message: str) -> None:
        """Log debug message."""
        self._log(message, LogLevel.DEBUG)

    def info(self, message: str) -> None:
        """Log info message."""
        self._log(message, LogLevel.INFO)

    def success(self, message: str) -> None:
        """Log success message."""
        self._log(message, LogLevel.SUCCESS)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self._log(message, LogLevel.WARNING)

    def error(self, message: str) -> None:
        """Log error message."""
        self._log(message, LogLevel.ERROR)

    def header(self, message: str, char: str = "-") -> None:
        """
        Print a header with box drawing.

        Args:
            message: Header text
            char: Character to use for the box
        """
        if not self.verbose:
            return

        width = 60
        print(f"\n+{char * (width - 2)}+")
        print(f"| {message:<{width - 4}} |")
        print(f"+{char * (width - 2)}+")
        self._last_was_progress = False

    def section(self, message: str) -> None:
        """Start a new section with indentation."""
        self.header(message, char="-")
        self._indent_level = 0

    def indent(self) -> None:
        """Increase indentation level."""
        self._indent_level += 1

    def dedent(self) -> None:
        """Decrease indentation level."""
        self._indent_level = max(0, self._indent_level - 1)

    def progress(self, message: str, current: int, total: int) -> None:
        """
        Display a progress indicator.

        Args:
            message: Progress message
            current: Current progress value
            total: Total progress value
        """
        if not self.verbose:
            return

        percentage = int(100 * current / total) if total > 0 else 0
        bar_length = 40
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = "#" * filled + "." * (bar_length - filled)

        timestamp = self._format_timestamp()
        indent = "  " * self._indent_level

        line = f"\r[{timestamp}] {indent}  -> {message} [{bar}] {percentage}%"

        # Clear to end of line if previous was progress
        if self._last_was_progress:
            line = "\r" + " " * 100 + line

        print(line, end="", flush=True)

        # Print newline when complete
        if current >= total:
            print()

        self._last_was_progress = True

    def banner(self, title: str, version: Optional[str] = None) -> None:
        """
        Print a banner at the start of execution.

        Args:
            title: Application title
            version: Version string
        """
        if not self.verbose:
            return

        line = "=" * 60
        print(f"\n{line}")
        if version:
            print(f"  {title} v{version}")
        else:
            print(f"  {title}")
        print(f"{line}\n")
        self._last_was_progress = False

    def summary(self, message: str, items: Optional[list[str]] = None) -> None:
        """
        Print a summary box.

        Args:
            message: Summary message
            items: Optional list of items to display
        """
        if not self.verbose:
            return

        line = "=" * 60
        print(f"\n{line}")
        print(f"  {message}")

        if items:
            print()
            for item in items:
                print(f"    -> {item}")

        print(f"{line}\n")
        self._last_was_progress = False


# Global logger instance
_logger: Optional[VerboseLogger] = None


def get_logger(verbose: bool = True, use_colors: bool = True) -> VerboseLogger:
    """
    Get or create the global logger instance.

    Args:
        verbose: Enable verbose output
        use_colors: Use color-coded output

    Returns:
        VerboseLogger instance
    """
    global _logger
    if _logger is None:
        _logger = VerboseLogger(verbose=verbose, use_colors=use_colors)
    return _logger


def set_verbose(verbose: bool) -> None:
    """
    Set verbose mode for the global logger.

    Args:
        verbose: Enable verbose output
    """
    logger = get_logger()
    logger.verbose = verbose
