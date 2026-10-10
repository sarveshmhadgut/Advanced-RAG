"""
Provides functionality to parse markdown-style documents into structured,
hierarchical sections based on heading markers.
"""

import re
import shutil
import sys
from pathlib import Path
from typing import Any

from termcolor import colored

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import console
from src.exception import MyException
from src.logger import logging

try:
    width = shutil.get_terminal_size().columns
    DOCUMENTS_DIRPATH: Path = ROOT / "data" / "input" / "documents"
    PDFS_DIRPATH: Path = ROOT / "data" / "input" / "pdfs"
except Exception as e:
    logging.error(f"Failed to initialize semantic splitting module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["parse_document"]


def parse_document(
    path: Path,
    text: str,
) -> list[dict[str, Any]]:
    """
    Parses a markdown-style document into structured sections by splitting
    on heading markers (e.g., #, ##, ###) and building a hierarchical title.

    Args:
        path (Path): The file path of the document being parsed.
        text (str): The full text content of the document.

    Returns:
        list[dict[str, Any]]:
            - A list of section dictionaries, each containing:
                - "path" (str): The source file path.
                - "title" (str): The hierarchical heading trail joined by " > ".
                - "text" (str): The body content under that heading.
            - An empty list if the input text is empty.

    Raises:
        MyException: If inputs are invalid or document parsing fails.
    """
    try:
        logging.info("Parsing document...")

        if not path:
            raise ValueError("path must be provided")

        if text is None:
            raise ValueError("text cannot be None")

        if not text:
            return []

        sections: list[dict[str, Any]] = []
        breadcrumbs: list[str] = []
        body: list[str] = []

        # Flush accumulated body lines into a section entry
        def flush() -> None:
            body_content = "\n".join(body).strip()
            if body_content:
                sections.append(
                    {
                        "path": str(path),
                        "title": " > ".join(breadcrumbs) if breadcrumbs else "Root",
                        "text": body_content,
                    }
                )
            body.clear()

        for line in text.splitlines():
            match = re.match(r"^(#+)\s+(.*)$", line)
            if match:
                # Flush previous section before starting a new heading
                flush()

                # Determine heading depth and trim breadcrumb trail accordingly
                sub = len(match.group(1))
                breadcrumb = match.group(2).title()
                breadcrumbs = breadcrumbs[: sub - 1] + [breadcrumb]
            else:
                body.append(line)

        # Flush any remaining content after the last heading
        flush()
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
            [
                *DOCUMENTS_DIRPATH.glob("*.md"),
                *DOCUMENTS_DIRPATH.glob("*.txt"),
            ]
        )

        for file in files:
            filename = file.name
            if not filename in ["products_and_pricing.md", "ai_engineering.md"]:
                continue

            text: str = file.read_text(encoding="utf-8", errors="ignore")
            parsed_document: list[dict[str, Any]] = parse_document(path=file, text=text)

            print(colored("_" * width, "grey"), colored(filename.center(width), "blue"))
            for doc in parsed_document:
                console.print_json(data=doc)
            print(colored("_" * width, "grey"))

        logging.info("Document parsing pipeline completed.")

    except Exception as e:
        logging.error(f"Failed to run document parsing pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
