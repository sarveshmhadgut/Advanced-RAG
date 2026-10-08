"""
Handles inference of topics from document text and extraction of file metadata,
enriching documents before they are embedded and stored.
"""

import re
import sys
import yaml
from typing import Any
import hashlib
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DOCUMENTS_DIRPATH = ROOT / "data" / "input" / "documents"
PDFS_DIRPATH = ROOT / "data" / "input" / "pdfs"
PARAMS_FILEPATH = ROOT / "config" / "params.yml"

from src import console
from src.logger import logging
from src.exception import MyException

# Load topics from centralized config, falling back to empty dict if file is empty
with open(PARAMS_FILEPATH, "r") as f:
    params = yaml.safe_load(f) or {}

__all__ = ["enrich_metadata", "infer_topics"]

TOPICS: list[str] = params.get("topics", [])


def infer_topics(text: str) -> list[str]:
    """
    Infers relevant topics from the given text by matching against a
    predefined list of topic keywords using case-insensitive word-boundary regex.

    Args:
        text (str): The text content to analyze for topic inference.

    Returns:
        list[str]:
            - A list of matched topic strings from the predefined TOPICS list.
            - An empty list if no topics are found in the text.

    Raises:
        MyException: If the topic inference process fails.
    """
    try:
        logging.info("Inferring topics...")

        normalized_text: str = text.lower()
        inferred_topics: list[str] = []

        for topic in TOPICS:
            pattern: str = rf"\b{re.escape(topic.lower())}\b"

            if re.search(pattern, normalized_text):
                inferred_topics.append(topic)

        logging.info("Topics inferred.")
        return inferred_topics

    except Exception as e:
        logging.error(f"Failed to infer topics: {e}")
        raise MyException(e, sys) from e


def enrich_metadata(path: Path, text: str) -> dict[str, Any]:
    """
    Enriches a document with metadata extracted from its file system properties
    and content analysis, including file stats, word counts, topics, and a
    content hash.

    Args:
        path (Path): The file path of the document to enrich.
        text (str): The full text content of the document.

    Returns:
        dict:
            - A metadata dictionary containing:
                - "source" (str): The file path as a string.
                - "title" (str): The file stem formatted as a title.
                - "extension" (str): The lowercase file extension.
                - "created_date" (str): ISO-formatted creation date.
                - "modified_date" (str): ISO-formatted last modification date.
                - "file_size" (int): File size in bytes.
                - "character_count" (int): Total character count of the text.
                - "word_count" (int): Total word count of the text.
                - "topics" (list[str]): Inferred topics from the text.
                - "content_hash" (str): SHA-256 hash of the text content.

    Raises:
        MyException: If metadata extraction fails.
    """
    try:
        logging.info("Enriching metadata...")

        if not path:
            return {}

        stats = path.stat()
        metadata: dict[str, Any] = {
            "source": str(path),
            "title": path.stem.replace("_", " ").replace("-", " ").title(),
            "extension": path.suffix.lower(),
            # st_birthtime is macOS-specific; fall back to st_ctime on Linux
            "created_date": datetime.datetime.fromtimestamp(
                getattr(stats, "st_birthtime", stats.st_ctime), datetime.UTC
            )
            .date()
            .isoformat(),
            "modified_date": datetime.datetime.fromtimestamp(
                getattr(stats, "st_mtime", stats.st_ctime), datetime.UTC
            )
            .date()
            .isoformat(),
            "file_size": stats.st_size,
            "character_count": len(text),
            "word_count": len(text.split()),
            "topics": infer_topics(text=text),
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

        logging.info("Metadata enriched.")
        return metadata

    except Exception as e:
        logging.error(f"Failed to enrich metadata: {e}")
        raise MyException(e, sys) from e


def main() -> None:
    """
    Demonstrates the metadata enrichment pipeline by reading all markdown,
    text, and PDF files from input directories and printing their enriched
    metadata.

    Returns:
        None

    Raises:
        MyException: If file reading or metadata enrichment fails.
    """
    try:
        logging.info("Running metadata enrichment pipeline...")

        files: list[Path] = sorted(
            [
                *DOCUMENTS_DIRPATH.glob("*.md"),
                *DOCUMENTS_DIRPATH.glob("*.txt"),
                *PDFS_DIRPATH.glob("*.pdf"),
            ]
        )

        for file in files:
            text: str = file.read_text(encoding="utf-8", errors="ignore")

            metadata: dict[str, Any] = enrich_metadata(path=file, text=text)
            console.print_json(data=metadata)

        logging.info("Metadata enrichment pipeline completed.")

    except Exception as e:
        logging.error(f"Failed to run metadata enrichment pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
