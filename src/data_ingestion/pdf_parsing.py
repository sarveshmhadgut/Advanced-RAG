"""
Parses PDF files directly using PyMuPDF to extract text along with physical
block metadata, classifying each block as header, table, or paragraph.
"""

import re
import sys
import pymupdf
import yaml
from typing import Any
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src import console
from src.exception import MyException
from src.logger import logging

PDFS_DIRPATH = ROOT / "data" / "input" / "pdfs"
PARAMS_FILEPATH = ROOT / "config" / "params.yml"

# Load topics from centralized config, falling back to empty dict if file is empty
with open(PARAMS_FILEPATH, "r") as f:
    params = yaml.safe_load(f) or {}

PYMUPDF_TEXT_INDEX = params.get("PYMUPDF_TEXT_INDEX", 4)

__all__ = ["label_line", "parse_pdf"]


def label_line(line: str) -> str:
    """
    Classifies a single line of text as a "header", "table", or "paragraph"
    based on heuristics such as token count, casing, and whitespace patterns.

    Args:
        line (str): A single line of text to classify.

    Returns:
        str:
            - "header" if the line has 10+ tokens and is all uppercase or ends with ":".
            - "table" if the line contains 2+ occurrences of multi-spaces or pipe characters.
            - "paragraph" otherwise.

    Raises:
        MyException: If the line classification process fails.
    """
    try:
        logging.info("Labeling line...")

        tokens: list[str] = line.split()

        # Long uppercase or colon-ending lines are likely section headers
        if len(tokens) >= 10 and (line.isupper() or line.endswith(":")):
            return "header"
        # Multiple large whitespace gaps or pipes suggest tabular data
        elif len(re.findall(r"\s{2,}|\|", line)) >= 2:
            return "table"

        logging.info("Line labeled.")
        return "paragraph"

    except Exception as e:
        logging.error(f"Failed to label line: {e}")
        raise MyException(e, sys) from e


def parse_pdf(path: Path) -> list[dict[str, Any]]:
    """
    Parses a PDF file into structured block-level entries with page numbers,
    block numbers, content type classification, and extracted text.

    Args:
        path (Path): The file path to the PDF document to parse.

    Returns:
        list[dict]:
            - A list of entry dictionaries, each containing:
                - "source" (str): The PDF file path as a string.
                - "page" (int): The 1-indexed page number.
                - "block" (int): The 1-indexed block number within the page.
                - "kind" (str): The content type ("header", "table", or "paragraph").
                - "text" (str): The extracted text content of the block.

    Raises:
        MyException: If the PDF cannot be opened or parsed.
    """

    try:
        logging.info("Parsing PDF...")

        entries: list[dict[str, Any]] = []
        with pymupdf.open(path) as f:
            for page_number, page in enumerate(f, 1):
                # Extract sorted text blocks; block[4] holds the text content
                blocks = page.get_text("blocks", sort=True)
                for block_number, block in enumerate(blocks, 1):
                    text: str = block[PYMUPDF_TEXT_INDEX].strip()
                    lines: list[str] = [
                        line for line in text.splitlines() if line.strip()
                    ]
                    kind: str = (
                        "table"
                        if any(label_line(line) for line in lines)
                        else label_line(text)
                    )

                    entry: dict[str, Any] = {
                        "source": str(path),
                        "page": page_number,
                        "block": block_number,
                        "kind": kind,
                        "text": text,
                    }

                    entries.append(entry)

        logging.info("PDF parsed.")
        return entries

    except Exception as e:
        logging.error(f"Failed to parse PDF: {e}")
        raise MyException(e, sys) from e


def main() -> None:
    """
    Demonstrates the PDF parsing pipeline by reading all PDF files from
    the PDFs directory and printing their parsed block-level entries.

    Returns:
        None

    Raises:
        MyException: If PDF reading or parsing fails.
    """
    try:
        logging.info("Running PDF parsing pipeline...")

        pdfs: list[Path] = sorted(PDFS_DIRPATH.glob("*.pdf"))
        for pdf in pdfs:
            console.print_json(data=parse_pdf(pdf))

        logging.info("PDF parsing pipeline completed.")

    except Exception as e:
        logging.error(f"Failed to run PDF parsing pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
