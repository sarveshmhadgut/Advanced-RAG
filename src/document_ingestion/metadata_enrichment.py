"""
Handles inference of topics from document text and extraction of file metadata,
enriching documents before they are embedded and stored.
"""

import datetime
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exception import DocumentParsingError, MyException, ValidationError
from src.logger import logging
from src.schema import DocumentMetadata
from src.utils import (
    DOCUMENTS_DIRPATH,
    PARAMS_FILEPATH,
    PDFS_DIRPATH,
    compute_content_hash,
    console,
    load_yaml_file,
    print_divider,
    print_header,
)

try:
    PARAMS: dict[str, Any] = load_yaml_file(PARAMS_FILEPATH)
    TOPICS: list[str] = list(PARAMS.get("topics", []))
except Exception as e:
    logging.info(f"Failed to initialize metadata enrichment module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["DocumentMetadata", "enrich_metadata"]


def infer_topics(text: str) -> list[str]:
    """
    Infers relevant topics from the given text by matching against a
    predefined list of topic keywords using case-insensitive word-boundary regex.

    Args:
        text (str): The text content to analyze for topic inference.

    Returns:
        list[str]:
            - A list of matched topic strings from the predefined TOPICS list.
            - An empty list if no topics are found in the text or if text is empty.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If topic inference fails.
    """
    try:
        logging.info("Inferring topics...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        if not text:
            return []

        normalized_text: str = text.lower()
        inferred_topics: list[str] = []

        for topic in TOPICS:
            if re.search(rf"\b{re.escape(topic.lower())}\b", normalized_text):
                inferred_topics.append(topic)

        logging.info(f"Inferred {len(inferred_topics)} topics.")
        return inferred_topics

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to infer topics: {e}")
        raise DocumentParsingError(e, sys) from e


def enrich_metadata(
    path: Path,
    text: str,
) -> DocumentMetadata:
    """
    Enriches a document with metadata extracted from its file system properties
    and content analysis, including file stats, word counts, topics, and a
    content hash.

    Args:
        path (Path): The file path of the document to enrich.
        text (str): The full text content of the document.

    Returns:
        DocumentMetadata:
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
        ValidationError: If inputs are invalid.
        DocumentParsingError: If metadata extraction fails.
    """
    try:
        logging.info(f"Enriching metadata for: {path.name if path else 'unknown'}...")

        if not path:
            raise ValidationError("path must be provided", sys)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        stats: os.stat_result = path.stat()
        title: str = path.stem.replace("_", " ").replace("-", " ").title()
        # st_birthtime is macOS-specific; fall back to st_ctime on Linux
        created_date: str = (
            datetime.datetime.fromtimestamp(
                getattr(stats, "st_birthtime", stats.st_ctime), datetime.UTC
            )
            .date()
            .isoformat()
        )
        modified_date: str = (
            datetime.datetime.fromtimestamp(
                getattr(stats, "st_mtime", stats.st_ctime), datetime.UTC
            )
            .date()
            .isoformat()
        )
        topics: list[str] = infer_topics(text=text)
        content_hash: str = compute_content_hash(content=text)

        metadata: DocumentMetadata = {
            "source": str(path),
            "title": title,
            "extension": path.suffix.lower(),
            "created_date": created_date,
            "modified_date": modified_date,
            "file_size": stats.st_size,
            "character_count": len(text),
            "word_count": len(text.split()),
            "topics": topics,
            "content_hash": content_hash,
        }

        logging.info("Metadata enriched successfully.")
        return metadata

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to enrich metadata: {e}")
        raise DocumentParsingError(e, sys) from e


def main() -> None:
    """
    Demonstrates the metadata enrichment pipeline by reading all markdown,
    text, and PDF files from input directories and printing their enriched
    metadata.

    Returns:
        None

    Raises:
        MyException: If the metadata enrichment pipeline fails.
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
            metadata: DocumentMetadata = enrich_metadata(
                path=file,
                text=file.read_text(encoding="utf-8", errors="ignore"),
            )

            print_header(file.name)
            console.print_json(data=dict(metadata))
            print_divider()

        logging.info("Metadata enrichment pipeline completed.")

    except Exception as e:
        logging.info(f"Failed to run metadata enrichment pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
