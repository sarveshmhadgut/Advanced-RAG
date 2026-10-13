"""
I/O and serialization helper functions for YAML configs, text reading, and hashing.
"""

import hashlib
import sys
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import yaml

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exception import MyException, ValidationError
from src.logger import logging

__all__: list[str] = [
    "compute_content_hash",
    "generate_uuid",
    "load_yaml_file",
    "read_text_file",
]


def load_yaml_file(file_path: Path | str) -> dict[str, Any]:
    """
    Safely load and parse a YAML file into a dictionary.

    Args:
        file_path (Path | str): Path to the YAML file to read.

    Returns:
        dict[str, Any]: Parsed dictionary content. Returns empty dict if file is empty.

    Raises:
        MyException: If file path is invalid, does not exist, or YAML parsing fails.
    """
    try:
        logging.info(f"Loading YAML file from: {file_path}...")
        if not file_path:
            raise ValueError("file_path cannot be None or empty")

        target_path: Path = Path(file_path) if isinstance(file_path, str) else file_path
        if not target_path.exists():
            raise FileNotFoundError(f"YAML file does not exist: {target_path}")

        with open(target_path, "r", encoding="utf-8") as f:
            content: Any = yaml.safe_load(f)

        data: dict[str, Any] = content if isinstance(content, dict) else {}
        logging.info(f"Loaded YAML file with {len(data)} top-level keys.")
        return data
    except Exception as e:
        logging.info(f"Failed to load YAML file: {e}")
        raise MyException(e, sys) from e


def read_text_file(
    file_path: Path | str,
    encoding: str = "utf-8",
) -> str:
    """
    Read text content from a file using the specified encoding.

    Args:
        file_path (Path | str): Path to the text file.
        encoding (str, optional): Text encoding. Defaults to "utf-8".

    Returns:
        str: Decoded file content.

    Raises:
        MyException: If file is invalid, missing, or cannot be read.
    """
    try:
        logging.info(f"Reading text file: {file_path}...")
        if not file_path:
            raise ValueError("file_path cannot be None or empty")

        target_path: Path = Path(file_path) if isinstance(file_path, str) else file_path
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path}")

        content: str = target_path.read_text(encoding=encoding)
        logging.info(f"Read {len(content)} characters from {target_path.name}.")
        return content
    except Exception as e:
        logging.info(f"Failed to read text file: {e}")
        raise MyException(e, sys) from e


def compute_content_hash(
    content: str | bytes,
    algorithm: str = "sha256",
) -> str:
    """
    Compute cryptographic hexadecimal hash of text or byte content.

    Args:
        content (str | bytes): Text string or bytes to hash.
        algorithm (str, optional): Hash algorithm from hashlib. Defaults to "sha256".

    Returns:
        str: Hexadecimal digest string.

    Raises:
        MyException: If content is None or hashing fails.
    """
    try:
        logging.info(f"Computing content hash using {algorithm}...")
        if content is None:
            raise ValueError("content cannot be None")

        byte_data: bytes = (
            content.encode("utf-8") if isinstance(content, str) else content
        )
        hasher = hashlib.new(algorithm)
        hasher.update(byte_data)
        digest: str = hasher.hexdigest()

        logging.info(f"Hash computed successfully: {digest[:8]}...")
        return digest
    except Exception as e:
        logging.info(f"Failed to compute content hash: {e}")
        raise MyException(e, sys) from e


def generate_uuid(
    name: str | None = None,
    namespace: UUID | str = NAMESPACE_URL,
    as_hex: bool = False,
    *,
    text: str | None = None,
) -> str:
    """
    Generate a UUID string, either random (UUID4) or deterministic (UUID5).

    When a name or text is provided, a deterministic UUID5 is generated using the
    specified namespace. When omitted, a random UUID4 is generated.

    Args:
        name (str | None, optional): Name or content used to generate deterministic UUID5.
            Defaults to None.
        namespace (UUID | str, optional): Namespace identifier for UUID5.
            Defaults to NAMESPACE_URL.
        as_hex (bool, optional): If True, returns a 32-character hexadecimal string without
            hyphens. If False, returns standard 36-character hyphenated UUID. Defaults to False.
        text (str | None, optional): Keyword-only alias for name. Defaults to None.

    Returns:
        str: Generated UUID string in hexadecimal or standard format.

    Raises:
        ValidationError: If arguments are of invalid types or namespace string is malformed.
        MyException: If UUID generation encounters an unexpected error.
    """
    try:
        logging.info("Generating UUID...")

        target_name: str | None = text if name is None else name
        if target_name is not None and not isinstance(target_name, str):
            raise ValidationError(
                f"Expected 'name' or 'text' to be a string, got {type(target_name).__name__}",
                sys,
            )

        if not isinstance(as_hex, bool):
            raise ValidationError(
                f"Expected 'as_hex' to be a boolean, got {type(as_hex).__name__}",
                sys,
            )

        target_namespace: UUID
        if isinstance(namespace, UUID):
            target_namespace = namespace
        elif isinstance(namespace, str):
            try:
                target_namespace = UUID(namespace)
            except Exception as exc:
                raise ValidationError(
                    f"Invalid namespace UUID string '{namespace}': {exc}",
                    sys,
                ) from exc
        else:
            raise ValidationError(
                f"Expected 'namespace' to be a UUID or str, got {type(namespace).__name__}",
                sys,
            )

        uuid_obj: UUID
        if target_name is not None:
            uuid_obj = uuid5(target_namespace, target_name)
        else:
            uuid_obj = uuid4()

        result_id: str = uuid_obj.hex if as_hex else str(uuid_obj)
        logging.info(f"Generated UUID successfully: {result_id[:8]}...")
        return result_id

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to generate UUID: {e}")
        raise MyException(e, sys) from e
