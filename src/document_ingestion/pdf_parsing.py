"""
Parses PDF files directly using PyMuPDF to extract text along with physical
block metadata, classifying each block as header, table, or paragraph.
"""

import re
import shutil
import sys
from pathlib import Path
from typing import Any

import pymupdf
from termcolor import colored

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import console
from src.exception import MyException
from src.logger import logging

try:
    width = shutil.get_terminal_size().columns
    PDFS_DIRPATH: Path = ROOT / "data" / "input" / "pdfs"
    PARAMS_FILEPATH: Path = ROOT / "config" / "params.yml"
    PYMUPDF_TEXT_INDEX: int = 4
except Exception as e:
    logging.error(f"Failed to initialize semantic splitting module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["extract_pdf_text", "label_line", "parse_pdf"]


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
        MyException: If line is None or labeling fails.
    """
    try:
        logging.info("Labeling line...")

        if line is None:
            raise ValueError("line cannot be None")

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
        list[dict[str, Any]]:
            - A list of entry dictionaries, each containing:
                - "source" (str): The PDF file path as a string.
                - "page" (int): The 1-indexed page number.
                - "block" (int): The 1-indexed block number within the page.
                - "kind" (str): The content type ("header", "table", or "paragraph").
                - "text" (str): The extracted text content of the block.

    Raises:
        MyException: If inputs are invalid or PDF cannot be parsed.
    """
    try:
        logging.info("Parsing PDF...")

        if not path:
            raise ValueError("path must be provided")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError(f"File must be a PDF: {path}")

        entries: list[dict[str, Any]] = []
        with pymupdf.open(path) as f:
            for page_number, page in enumerate(f, 1):
                # Extract sorted text blocks; block[4] holds the text content
                blocks: list[Any] = page.get_text("blocks", sort=True)

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


def extract_pdf_text(
    file: Path,
    start_page: int | None = None,
    end_page: int | None = None,
) -> str:
    """
    Extract text block-by-block from a PDF while preserving structural boundaries.

    Args:
        file (Path): The file path to the PDF document.
        start_page (int, optional): 1-indexed starting page number (inclusive). Defaults to None.
        end_page (int, optional): 1-indexed ending page number (inclusive). Defaults to None.

    Returns:
        str: Cleaned and structured text extracted from the specified page range.

    Raises:
        MyException: If inputs are invalid or PDF extraction fails.
    """
    try:
        logging.info("Extracting PDF text...")

        if not file:
            raise ValueError("file must be provided")

        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        if file.suffix.lower() != ".pdf":
            raise ValueError(
                f"Expected a PDF file (.pdf), but got '{file.suffix}': {file.name}"
            )

        if start_page is not None and start_page <= 0:
            raise ValueError("start_page must be greater than zero")

        if end_page is not None and end_page <= 0:
            raise ValueError("end_page must be greater than zero")

        if start_page is not None and end_page is not None and start_page > end_page:
            raise ValueError("start_page cannot be greater than end_page")

        page_texts: list[str] = []

        with pymupdf.open(file) as pdf:
            total_pages: int = len(pdf)

            if start_page is not None and start_page > total_pages:
                raise ValueError(
                    f"start_page ({start_page}) exceeds total document pages ({total_pages})"
                )

            for page_num, page in enumerate(pdf, start=1):
                if start_page and page_num < start_page:
                    continue

                if end_page and page_num > end_page:
                    break

                page_blocks: list[str] = []
                prev_y1 = None

                for block in page.get_text("blocks", sort=True):
                    block_text = block[4].strip()

                    if not block_text:
                        continue

                    y0, y1 = block[1], block[3]
                    if prev_y1 is not None:
                        page_blocks.append("\n" if 0 <= y0 - prev_y1 <= 15 else "\n\n")

                    page_blocks.append(block_text)
                    prev_y1 = y1

                page_texts.append("".join(page_blocks))

        logging.info("PDF text extracted.")
        return "\n\n".join(page_texts)

    except Exception as exc:
        logging.error(f"Failed to extract PDF text: {exc}")
        raise MyException(exc, sys) from exc


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

        pdfs: list[Path] = sorted(PDFS_DIRPATH.glob("*.pdf"))[:2]
        for pdf in pdfs:
            filename = pdf.name
            parsed_pdf = parse_pdf(pdf)[:10]

            print(colored("_" * width, "grey"), colored(filename.center(width), "blue"))
            for doc in parsed_pdf:
                console.print_json(data=doc)
            print(colored("_" * width, "grey"))

        logging.info("PDF parsing pipeline completed.")

    except Exception as e:
        logging.error(f"Failed to run PDF parsing pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
