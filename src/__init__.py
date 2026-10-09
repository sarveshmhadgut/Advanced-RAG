"""
Core package initialization with custom rich console and theme settings.
"""

from rich.console import Console
from rich.theme import Theme

__all__: list[str] = ["console", "theme"]

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
