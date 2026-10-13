"""
Terminal visual display, separator, and header formatting utilities.
"""

import shutil
import sys
from pathlib import Path

from rich.console import Console
from rich.theme import Theme
from termcolor import colored

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exception import MyException
from src.logger import logging

__all__: list[str] = [
    "console",
    "get_terminal_width",
    "print_divider",
    "print_header",
    "theme",
]

theme: Theme = Theme(
    {
        "json.key": "#c1a2ff",
        "json.string": "#FCCEA1",
        "json.number": "#A1C4FD",
        "json.boolean": "#A6F5D8",
        "json.null": "#ffb3ba",
    }
)

console: Console = Console(
    theme=theme,
    force_terminal=True,
    force_jupyter=False,
    color_system="truecolor",
)


def get_terminal_width(fallback: int = 80) -> int:
    """
    Determine the current terminal column width, defaulting to fallback if unavailable.

    Args:
        fallback (int, optional): Fallback column width if detection fails. Defaults to 80.

    Returns:
        int: Terminal column width in characters.

    Raises:
        MyException: If determining terminal width fails.
    """
    try:
        logging.info("Determining terminal width...")
        if fallback <= 0:
            raise ValueError("fallback must be greater than zero")

        width: int = shutil.get_terminal_size(fallback=(fallback, 24)).columns
        logging.info(f"Terminal width resolved to {width} columns.")
        return width
    except Exception as e:
        logging.info(f"Failed to determine terminal width: {e}")
        raise MyException(e, sys) from e


def print_divider(
    width: int | None = None,
    char: str = "_",
    color: str = "grey",
) -> None:
    """
    Print a horizontal terminal-width divider line with styled color.

    Args:
        width (int | None, optional): Width of divider in characters. Defaults to detected terminal width.
        char (str, optional): Repeating character for divider line. Defaults to "_".
        color (str, optional): Termcolor color name. Defaults to "grey".

    Returns:
        None

    Raises:
        MyException: If printing divider fails.
    """
    try:
        logging.info("Printing terminal divider...")
        if not char:
            raise ValueError("char cannot be empty")

        terminal_width: int = (
            width if width is not None and width > 0 else get_terminal_width()
        )
        print(colored(char * terminal_width, color))
        logging.info("Terminal divider printed.")
    except Exception as e:
        logging.info(f"Failed to print divider: {e}")
        raise MyException(e, sys) from e


def print_header(
    title: str,
    width: int | None = None,
    text_color: str = "blue",
    line_color: str = "grey",
) -> None:
    """
    Print a centered title surrounded by horizontal divider lines.

    Args:
        title (str): Title text to display centered in the terminal.
        width (int | None, optional): Total display width. Defaults to detected terminal width.
        text_color (str, optional): Termcolor color name for the title text. Defaults to "blue".
        line_color (str, optional): Termcolor color name for the divider lines. Defaults to "grey".

    Returns:
        None

    Raises:
        MyException: If title is None or printing header fails.
    """
    try:
        logging.info(f"Printing header for title: {title}...")
        if title is None:
            raise ValueError("title cannot be None")

        terminal_width: int = (
            width if width is not None and width > 0 else get_terminal_width()
        )
        divider: str = colored("_" * terminal_width, line_color)
        centered_title: str = colored(title.center(terminal_width), text_color)

        print(divider, centered_title)
        logging.info("Header printed successfully.")
    except Exception as e:
        logging.info(f"Failed to print header: {e}")
        raise MyException(e, sys) from e
