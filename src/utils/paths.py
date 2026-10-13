"""
Centralized directory paths and filesystem location constants for the project.
"""

import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exception import MyException
from src.logger import logging

try:
    CONFIG_DIRPATH: Path = ROOT / "config"
    DATA_DIRPATH: Path = ROOT / "data"
    DOCUMENTS_DIRPATH: Path = DATA_DIRPATH / "input" / "documents"
    PDFS_DIRPATH: Path = DATA_DIRPATH / "input" / "pdfs"
    LOGS_DIRPATH: Path = ROOT / "logs"
    PARAMS_FILEPATH: Path = CONFIG_DIRPATH / "params.yml"
except Exception as e:
    logging.info(f"Failed to initialize centralized path constants: {e}")
    raise MyException(e, sys) from e


__all__: list[str] = [
    "CONFIG_DIRPATH",
    "DATA_DIRPATH",
    "DOCUMENTS_DIRPATH",
    "LOGS_DIRPATH",
    "PARAMS_FILEPATH",
    "PDFS_DIRPATH",
    "ROOT",
]
