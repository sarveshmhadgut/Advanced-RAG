"""
Timestamp and datetime formatting utility functions.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exception import MyException

__all__: list[str] = ["get_current_timestamp"]


def get_current_timestamp() -> str:
    """
    Generates a formatted timestamp string for the current time.

    Returns:
        str: The current timestamp formatted as "DD-Mon-YY_HH-MM-SS".

    Raises:
        MyException: If timestamp generation fails.
    """
    try:
        timestamp: str = datetime.now(UTC).strftime("%d-%b-%y_%H-%M-%S")
        return timestamp
    except Exception as e:
        raise MyException(e, sys) from e
