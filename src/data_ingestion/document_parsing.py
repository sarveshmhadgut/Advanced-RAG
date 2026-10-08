"""
Provides functionality to parse markdown-style documents into structured,
hierarchical sections based on heading markers.
"""

import re
import sys
from typing import Any
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src import console
from src.logger import logging
from src.exception import MyException

DOCUMENTS_DIRPATH = ROOT / "data" / "input" / "documents"
PDFS_DIRPATH = ROOT / "data" / "input" / "pdfs"

__all__ = ["parse_document"]


def parse_document(path: Path, text: str) -> list[dict[str, Any]]:
    """
    Parses a markdown-style document into structured sections by splitting
    on heading markers (e.g., #, ##, ###) and building a hierarchical title.

    Args:
        path (Path): The file path of the document being parsed.
        text (str): The full text content of the document.

    Returns:
        list[dict]:
            - A list of section dictionaries, each containing:
                - "path" (str): The source file path.
                - "title" (str): The hierarchical heading trail joined by " > ".
                - "text" (str): The body content under that heading.
            - An empty list if the input text is empty or None.

    Raises:
        MyException: If any error occurs during the document parsing process.
    """
    try:
        logging.info("Parsing document...")

        if not text:
            return []

        sections: list[dict[str, Any]] = []
        headings: list[str] = []
        body: list[str] = []

        # Flush accumulated body lines into a section entry
        def emit() -> None:
            body_content = "\n".join(body).strip()
            if body_content:
                sections.append(
                    {
                        "path": str(path),
                        "title": " > ".join(headings),
                        "text": body_content,
                    }
                )
            body.clear()

        for line in text.splitlines():
            match = re.match(r"^(#+)\s+(.*)$", line)
            if match:
                # Flush previous section before starting a new heading
                emit()

                # Determine heading depth and trim breadcrumb trail accordingly
                sub = len(match.group(1))
                header = match.group(2).title()
                headings = headings[: sub - 1] + [header]
            else:
                body.append(line)

        # Flush any remaining content after the last heading
        emit()
        logging.info("Document parsed.")
        return sections

    except Exception as e:
        logging.error(f"Failed to parse document: {e}")
        raise MyException(e, sys) from e


def main() -> None:
    """
    Demonstrates the document parsing pipeline by reading all markdown and
    text files from the documents directory and printing their parsed sections.

    Returns:
        None

    Raises:
        MyException: If file reading or parsing fails.
    """
    try:
        logging.info("Running document parsing pipeline...")

        files: list[Path] = sorted(
            [*DOCUMENTS_DIRPATH.glob("*.md"), *DOCUMENTS_DIRPATH.glob("*.txt")]
        )

        for file in files:
            text: str = file.read_text(encoding="utf-8", errors="ignore")
            parsed_document: list[dict[str, Any]] = parse_document(path=file, text=text)
            console.print_json(data=parsed_document)

        logging.info("Document parsing pipeline completed.")

    except Exception as e:
        logging.error(f"Failed to run document parsing pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
