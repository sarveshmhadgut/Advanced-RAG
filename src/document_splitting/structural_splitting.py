"""
Provides structural document splitting functionality based on hierarchical
markdown-style headings and breadcrumb trails.
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
except Exception as e:
    logging.error(f"Failed to initialize semantic splitting module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["get_structural_splits", "parse_sections"]


def parse_sections(text: str) -> list[tuple[str, str]]:
    """
    Parses markdown text into hierarchical section tuples of (breadcrumb, body).

    Args:
        text (str): The markdown text content to parse.

    Returns:
        list[tuple[str, str]]: A list of (breadcrumb, body) tuples representing
            each section. Returns an empty list if text is empty.

    Raises:
        MyException: If text is None or an unexpected error occurs during section parsing.
    """
    try:
        logging.info("Parsing markdown sections...")

        if text is None:
            raise ValueError("text cannot be None")

        if not text:
            return []

        breadcrumbs: list[str] = []
        paragraph_lines: list[str] = []
        sections: list[tuple[str, str]] = []

        def flush() -> None:
            if paragraph_lines:
                paragraph_body: str = " ".join(paragraph_lines).strip()

                if paragraph_body:
                    sections.append((" > ".join(breadcrumbs) or "Root", paragraph_body))
                paragraph_lines.clear()

        for line in text.splitlines():
            match: re.Match[str] | None = re.match(r"^(#+)\s+(.*)$", line)
            if match:
                flush()
                sub: int = len(match.group(1))
                breadcrumb: str = match.group(2)
                breadcrumbs = breadcrumbs[: sub - 1] + [breadcrumb]
            else:
                paragraph_lines.append(line.strip())

        flush()
        logging.info("Markdown sections parsed.")
        return sections

    except Exception as exc:
        logging.error(f"Failed to parse sections: {exc}")
        raise MyException(exc, sys) from exc


def get_structural_splits(
    path: Path,
    max_split_size: int = 20,
    overlap: int = 5,
) -> list[dict[str, Any]]:
    """
    Splits a document into structured chunks based on section hierarchy with word limits and overlap.

    Args:
        path (Path): The file path of the document to split.
        max_split_size (int, optional): Maximum number of words allowed per split. Defaults to 200.
        overlap (int, optional): Number of overlapping words between consecutive splits. Defaults to 50.

    Returns:
        list[dict[str, Any]]: A list of chunk dictionaries, each containing:
            - "title" (str): Hierarchical section title trail.
            - "text" (str): Chunk text content.

    Raises:
        MyException: If arguments are invalid, the file does not exist, or splitting fails.
    """
    try:
        logging.info(f"Generating structural splits for {path.name if path else 'unknown'}...")

        if not path:
            raise ValueError("path must be provided")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if max_split_size <= 0:
            raise ValueError("max_split_size must be greater than zero")

        if overlap < 0 or overlap >= max_split_size:
            raise ValueError("overlap must be non-negative and smaller than max_split_size")

        text: str = path.read_text(encoding="utf-8", errors="ignore")
        sections: list[tuple[str, str]] = parse_sections(text=text)

        if not sections:
            return []

        splits: list[dict[str, Any]] = []

        for breadcrumb, body in sections:
            words: list[str] = body.split()

            if len(words) <= max_split_size:
                splits.append(
                    {
                        "title": breadcrumb,
                        "text": " ".join(words),
                    }
                )
                continue

            i: int = 0
            n: int = len(words)
            step: int = max_split_size - overlap

            while i < n:
                chunk_words: list[str] = words[i : i + max_split_size]

                splits.append(
                    {
                        "title": breadcrumb,
                        "text": " ".join(chunk_words),
                    }
                )
                if i + max_split_size >= n:
                    break
                i += step

        logging.info(f"Generated {len(splits)} structural splits.")
        return splits

    except Exception as exc:
        logging.error(f"Failed to generate structural splits: {exc}")
        raise MyException(exc, sys) from exc


def main() -> None:
    """
    Demonstrates structural splitting on markdown documents in the documents directory.

    Returns:
        None

    Raises:
        MyException: If running the structural splitting pipeline fails.
    """
    try:
        logging.info("Running structural splitting pipeline...")
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

            splits: list[dict[str, Any]] = get_structural_splits(path=file)

            print(
                colored("_" * width, "grey"),
                colored(f"{filename}".center(width), "blue"),
            )
            for split in splits:
                console.print_json(data=split)
            print(colored("_" * width, "grey"))

        logging.info("Structural splitting pipeline completed.")

    except Exception as exc:
        logging.error(f"Failed to run structural splitting pipeline: {exc}")
        raise MyException(exc, sys) from exc


if __name__ == "__main__":
    main()
