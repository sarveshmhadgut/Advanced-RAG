"""
Provides utilities to clean raw text extracted from PDFs and other documents,
removing artifacts, fixing line breaks, and normalizing whitespace.
"""

import re
import sys
import pymupdf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src import console, Pretty
from src.exception import MyException
from src.logger import logging

PDFS_DIRPATH = ROOT / "data" / "input" / "pdfs"

__all__ = ["clean_document", "clean_pdf"]


def clean_pdf(text: str) -> str:
    """
    Cleans raw text extracted from a PDF by removing artifacts, normalizing
    whitespace, fixing hyphenated line breaks, and stripping control characters.

    Args:
        text (str): The raw text extracted from a PDF page or document.

    Returns:
        str:
            - The cleaned and normalized text string.
            - An empty string if the input text is empty or None.

    Raises:
        MyException: If any error occurs during the text cleaning process.
    """
    try:
        logging.info("Cleaning PDF text...")

        if not text:
            return ""

        # PDF extractors often inject null bytes and non-printable control chars
        text = text.replace("\x00", "")
        text = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Replace non-breaking spaces, zero-width spaces, and BOM with standard equivalents
        text = text.replace("\u00a0", " ")
        text = text.replace("\u200b", "")
        text = text.replace("\ufeff", "")

        # Strip known watermark artifacts injected by PDF hosting sites
        text = re.sub(r"(?im)^\s*OceanofPDF\.com\s*$", "", text)

        # Normalize line endings to Unix-style
        text = text.replace("\r\n", "").replace("\r", "")

        # Rejoin words that PDF extraction splits across lines with hyphens
        text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

        # Remove trailing spaces at the end of lines
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

        # Collapse excessive spaces within a line
        text = re.sub(r"[ \t]{2,}", " ", text)

        # Reduce multiple blank lines to a single blank line
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove spaces before punctuation marks
        text = re.sub(r"[ \t]+([,.;:!?])", r"\1", text)

        # Remove extra whitespace inside brackets
        text = re.sub(r"([(\[{])\s+", r"\1", text)
        text = re.sub(r"\s+([)\]}])", r"\1", text)

        # Strip leading and trailing whitespace from each line
        text = "\n".join(line.strip() for line in text.splitlines())

        # Final trim of the entire text block
        text = text.strip()

        logging.info("PDF text cleaned.")
        return text

    except Exception as e:
        logging.error(f"Failed to clean PDF text: {e}")
        raise MyException(e, sys) from e


def clean_document(text: str) -> str:
    """
    Cleans a full document's text by applying PDF cleaning and additionally
    removing standalone page numbers and "Page X of Y" patterns.

    Args:
        text (str): The raw text of the entire document.

    Returns:
        str:
            - The fully cleaned document text with page artifacts removed.

    Raises:
        MyException: If any error occurs during the document cleaning process.
    """
    try:
        logging.info("Cleaning document text...")

        text = clean_pdf(text)

        # Lines containing only digits are typically page numbers from PDF extraction
        text = re.sub(r"(?m)^\s*\d+\s*$", "", text)

        # Remove "Page X of Y" patterns
        text = re.sub(r"(?im)^\s*Page\s+\d+\s+of\s+\d+\s*$", "", text)

        # Remove excessive blank lines created by removals
        text = re.sub(r"\n{3,}", "\n\n", text)

        logging.info("Document text cleaned.")
        return text.strip()

    except Exception as e:
        logging.error(f"Failed to clean document text: {e}")
        raise MyException(e, sys) from e


def main() -> None:
    """
    Demonstrates the document cleaning pipeline by extracting text from
    specific pages of a sample PDF and printing before/after statistics.

    Returns:
        None

    Raises:
        MyException: If the PDF cannot be read or cleaning fails.
    """
    try:
        logging.info("Running document cleaning pipeline...")

        file: Path = PDFS_DIRPATH / "AI Engineering Building Applications.pdf"
        text: str = ""

        with pymupdf.open(file) as f:
            for page_number, page in enumerate(f, 1):
                if page_number in range(426, 429):
                    text += "\n\n" + page.get_text(sort=True)

        cleaned_document: str = clean_document(text=text)

        console.print(text, "\n", cleaned_document)
        console.print_json(
            data={
                "Lines": {
                    "Before": len(text.split("\n")),
                    "After": len(cleaned_document.split("\n")),
                },
                "Words": {
                    "Before": len(text.split()),
                    "After": len(cleaned_document.split()),
                },
            }
        )

        logging.info("Document cleaning pipeline completed.")

    except Exception as e:
        logging.error(f"Failed to run document cleaning pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
