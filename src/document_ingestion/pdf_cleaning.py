"""
Utilities for cleaning and normalizing raw text extracted from PDF documents.
"""

import re
import sys
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document_ingestion.document_cleaning import (
    normalize_characters,
    normalize_whitespace,
)
from src.exception import DocumentParsingError, MyException, ValidationError
from src.logger import logging
from src.utils import (
    PARAMS_FILEPATH,
    PDFS_DIRPATH,
    console,
    extract_pdf_text,
    get_terminal_width,
    load_yaml_file,
    print_divider,
    print_header,
)

try:
    WIDTH: int = get_terminal_width()
    PARAMS: dict[str, Any] = (
        load_yaml_file(PARAMS_FILEPATH)
        .get("document_ingestion", {})
        .get("pdf_cleaning", {})
    )
    START_PAGE: int | None = (
        int(PARAMS["start_page"]) if PARAMS.get("start_page") is not None else None
    )
    END_PAGE: int | None = (
        int(PARAMS["end_page"]) if PARAMS.get("end_page") is not None else None
    )
    PDF_NAME: str = str(
        PARAMS.get("pdf_name", "AI Engineering Building Applications.pdf")
    )
except Exception as e:
    logging.info(f"Failed to initialize PDF cleaning module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = [
    "clean_pdf",
    "normalize_characters",
    "normalize_pdf_whitespace",
    "remove_page_artifacts",
    "repair_hyphenated_line_breaks",
]


def repair_hyphenated_line_breaks(text: str) -> str:
    """
    Join words split across line breaks by hyphens due to PDF layout wrapping.

    Args:
        text (str): The PDF text containing potential hyphenated line breaks.

    Returns:
        str: The repaired text with hyphen-split words reconnected.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If repairing hyphenated breaks fails.
    """
    try:
        logging.info("Repairing hyphenated line breaks in PDF text...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        repaired_text: str = re.sub(
            r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)",
            "",
            text,
        )

        logging.info("Hyphenated line breaks repaired successfully.")
        return repaired_text

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to repair hyphenated line breaks: {e}")
        raise DocumentParsingError(e, sys) from e


def normalize_pdf_whitespace(text: str) -> str:
    """
    Normalize whitespace while collapsing soft line wraps within paragraphs.

    Args:
        text (str): PDF text with inconsistent whitespace or hard line breaks.

    Returns:
        str: Text with collapsed intra-paragraph line breaks and preserved paragraph breaks.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If whitespace normalization fails.
    """
    try:
        logging.info("Normalizing PDF whitespace...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        normalized_text: str = normalize_whitespace(
            text=text,
            preserve_markdown=False,
        )

        logging.info("PDF whitespace normalized successfully.")
        return normalized_text

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to normalize PDF whitespace: {e}")
        raise DocumentParsingError(e, sys) from e


def remove_page_artifacts(text: str) -> str:
    """
    Remove standalone page-number artifacts and common PDF extraction watermarks.

    Args:
        text (str): The PDF text containing page numbers or header/footer artifacts.

    Returns:
        str: Text with page numbers and known watermarks stripped.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If removing page artifacts fails.
    """
    try:
        logging.info("Removing PDF page artifacts...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        # Page X of Y, X of Y, Page X / Y (Arabic or Roman numerals)
        text = re.sub(
            r"(?im)^[ \t]*(?:page|pg)?\.?\s*(?:\d+|[ivxlcdm]+)\s*(?:of|/|out\s+of)\s*(?:\d+|[ivxlcdm]+)[ \t]*$",
            "",
            text,
        )

        # 2Prefixed page numbers: Page 1, Pg. iv, P. 12 (with optional trailing punctuation/brackets)
        text = re.sub(
            r"(?im)^[ \t]*(?:page|pg|p)\.?\s*(?:\d{1,5}|[ivxlcdm]+)[ \t]*[-–—~•|\)\]\}]?[ \t]*$",
            "",
            text,
        )

        # Section/Chapter page combinations: 1-1, A-2
        text = re.sub(
            r"(?im)^[ \t]*(?:(?:chapter|section|[a-z0-9]+)[-–—\.])\d{1,5}[ \t]*$",
            "",
            text,
        )

        # Standalone Arabic numerals with optional decorators: 12, - 12 -, (12), [12], | 12 |
        text = re.sub(
            r"(?m)^[ \t]*[-–—~•|\(\[\{]?[ \t]*\d{1,5}[ \t]*[-–—~•|\)\]\}]?[ \t]*$",
            "",
            text,
        )

        # Standalone Roman numerals with optional decorators: i, ii, - iv -, (vi), [ix]
        text = re.sub(
            r"(?im)^[ \t]*[-–—~•|\(\[\{]?[ \t]*(?=[ivxlcdm]+(?:\s|[-–—~•|\)\]\}]|$))(?:m{0,4}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3}))[ \t]*[-–—~•|\)\]\}]?[ \t]*$",
            "",
            text,
        )

        # Remove repeated dot sequences (such as dot leaders in tables of contents).
        text = re.sub(r"(?:\.[ \t]*){2,}", " ", text)

        # Known standalone watermark.
        text = re.sub(r"(?im)^[ \t]*OceanofPDF\.com[ \t]*$", "", text)

        logging.info("PDF page artifacts removed successfully.")
        return text

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to remove page artifacts: {e}")
        raise DocumentParsingError(e, sys) from e


def clean_pdf(text: str) -> str:
    """
    Clean raw text extracted from a PDF document by repairing ligatures,
    removing artifacts, connecting hyphenated breaks, and normalizing whitespace.

    Args:
        text (str): Raw text extracted from a PDF.

    Returns:
        str: Cleaned text with coherent paragraphs and normalized layout.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If cleaning fails.
    """
    try:
        logging.info("Cleaning PDF text...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        if not text:
            return ""

        text = normalize_characters(text)
        text = repair_hyphenated_line_breaks(text)
        text = remove_page_artifacts(text)
        text = normalize_pdf_whitespace(text)

        logging.info("PDF text cleaned successfully.")
        return text

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to clean PDF text: {e}")
        raise DocumentParsingError(e, sys) from e


def main() -> None:
    """
    Demonstrates the PDF cleaning pipeline on sample text extracted from a PDF.

    Returns:
        None

    Raises:
        MyException: If running the PDF cleaning demonstration fails.
    """
    try:
        logging.info("Running PDF cleaning pipeline demonstration...")

        file: Path = PDFS_DIRPATH / PDF_NAME

        if not file.exists():
            logging.info(f"Sample PDF file not found at {file}")
            return

        pdf_pages: list[str] = extract_pdf_text(
            file=file, start_page=START_PAGE, end_page=END_PAGE
        )
        raw_text: str = "\n\n".join(pdf_pages)
        cleaned_text: str = clean_pdf(text=raw_text)

        print_header(f"Cleaned: {file.name}")
        console.print(cleaned_text, markup=False)
        print_divider()

        print_header("Stats")
        console.print_json(
            data={
                "Lines": {
                    "Before": len(raw_text.splitlines()),
                    "After": len(cleaned_text.splitlines()),
                },
                "Words": {
                    "Before": len(raw_text.split()),
                    "After": len(cleaned_text.split()),
                },
                "Characters": {
                    "Before": len(raw_text),
                    "After": len(cleaned_text),
                },
            }
        )
        print_divider()

        logging.info("PDF cleaning pipeline demonstration completed.")

    except Exception as e:
        logging.info(f"Failed to run PDF cleaning pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
