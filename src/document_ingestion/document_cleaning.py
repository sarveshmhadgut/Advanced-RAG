"""
Utilities for cleaning raw text extracted from PDFs and other documents.
"""

import re
import shutil
import sys
from pathlib import Path

from termcolor import colored

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import console
from src.document_ingestion.pdf_parsing import extract_pdf_text
from src.exception import MyException
from src.logger import logging

try:
    width = shutil.get_terminal_size().columns
    PDFS_DIRPATH: Path = ROOT / "data" / "input" / "pdfs"
    DOCUMENTS_DIRPATH: Path = ROOT / "data" / "input" / "documents"
except Exception as e:
    logging.error(f"Failed to initialize semantic splitting module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["clean_document"]


def normalize_characters(text: str) -> str:
    """
    Normalize common PDF extraction artifacts, ligatures, and line endings.

    Args:
        text (str): The raw text extracted from a document.

    Returns:
        str: The normalized text with standardized ligatures, control characters removed,
            and line endings unified.

    Raises:
        MyException: If text is None or character normalization fails.
    """
    try:
        logging.info("Normalizing characters...")

        if text is None:
            raise ValueError("text cannot be None")

        # Remove null bytes and non-printable control characters.
        text = text.replace("\x00", "")
        text = re.sub(
            r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]",
            "",
            text,
        )

        # Normalize special whitespace characters.
        text = text.replace("\u00a0", " ")
        text = text.replace("\u200b", "")
        text = text.replace("\ufeff", "")

        # Normalize common typographic ligatures.
        ligatures: dict[str, str] = {
            "\ufb00": "ff",
            "\ufb01": "fi",
            "\ufb02": "fl",
            "\ufb03": "ffi",
            "\ufb04": "ffl",
            "\ufb05": "st",
            "\ufb06": "st",
        }

        for original, replacement in ligatures.items():
            text = text.replace(original, replacement)

        # Normalize line endings without deleting line breaks.
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        logging.info("Characters normalized.")
        return text

    except Exception as exc:
        logging.error(f"Failed to normalize characters: {exc}")
        raise MyException(exc, sys) from exc


def repair_hyphenated_line_breaks(text: str) -> str:
    """
    Join words split across line breaks by hyphens.

    Args:
        text (str): The text containing potential hyphenated line breaks.

    Returns:
        str: The repaired text with split words reconnected.

    Raises:
        MyException: If text is None or repairing hyphenated breaks fails.
    """
    try:
        logging.info("Repairing hyphenated line breaks...")

        if text is None:
            raise ValueError("text cannot be None")

        repaired_text: str = re.sub(
            r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)",
            "",
            text,
        )

        logging.info("Hyphenated line breaks repaired.")
        return repaired_text

    except Exception as exc:
        logging.error(f"Failed to repair hyphenated line breaks: {exc}")
        raise MyException(exc, sys) from exc


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace while preserving blank-line paragraph boundaries.

    Args:
        text (str): The text with inconsistent whitespace or excessive blank lines.

    Returns:
        str: Text with collapsed intra-paragraph spaces and preserved paragraph breaks.

    Raises:
        MyException: If text is None or whitespace normalization fails.
    """
    try:
        logging.info("Normalizing whitespace...")

        if text is None:
            raise ValueError("text cannot be None")

        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove trailing spaces from lines.
        text = re.sub(
            r"[ \t]+$",
            "",
            text,
            flags=re.MULTILINE,
        )

        # Normalize repeated spaces and tabs.
        text = re.sub(
            r"[ \t]{2,}",
            " ",
            text,
        )

        # Remove spaces before punctuation.
        text = re.sub(
            r"[ \t]+([,.;:!?])",
            r"\1",
            text,
        )

        # Preserve blank lines as paragraph boundaries.
        text = re.sub(
            r"\n[ \t]*\n+",
            "\n\n",
            text,
        )

        # Join single newlines within paragraphs only.
        paragraphs: list[str] = re.split(
            r"\n\n",
            text,
        )

        cleaned_paragraphs: list[str] = []
        for paragraph in paragraphs:
            paragraph = re.sub(
                r"[ \t]*\n[ \t]*",
                " ",
                paragraph,
            )
            paragraph = re.sub(
                r"[ \t]{2,}",
                " ",
                paragraph,
            )

            paragraph = paragraph.strip()
            if paragraph:
                cleaned_paragraphs.append(paragraph)

        logging.info("Whitespace normalized.")
        return "\n\n".join(cleaned_paragraphs)

    except Exception as exc:
        logging.error(f"Failed to normalize whitespace: {exc}")
        raise MyException(exc, sys) from exc


def remove_page_artifacts(text: str) -> str:
    """
    Remove standalone page-number artifacts and common extraction watermarks.

    Args:
        text (str): The text containing page numbers or header/footer artifacts.

    Returns:
        str: Text with page numbers and known watermarks stripped.

    Raises:
        MyException: If text is None or removing page artifacts fails.
    """
    try:
        logging.info("Removing page artifacts...")

        if text is None:
            raise ValueError("text cannot be None")

        # Standalone page numbers.
        text = re.sub(r"(?m)^[ \t]*\d{1,4}[ \t]*$", "", text)

        # Remove repeated dot sequences (such as dot leaders in tables of contents).
        text = re.sub(r"(?:\.[ \t]*){2,}", " ", text)

        # Page X of Y.
        text = re.sub(r"(?im)^[ \t]*page[ \t]+\d+[ \t]+of[ \t]+\d+[ \t]*$", "", text)

        # Known standalone watermark.
        text = re.sub(r"(?im)^[ \t]*OceanofPDF\.com[ \t]*$", "", text)

        logging.info("Page artifacts removed.")
        return text

    except Exception as exc:
        logging.error(f"Failed to remove page artifacts: {exc}")
        raise MyException(exc, sys) from exc


def clean_document(text: str) -> str:
    """
    Clean a full document extracted from a PDF or text source.

    Args:
        text (str): Raw extracted document text.

    Returns:
        str: Cleaned text with meaningful paragraph boundaries preserved.

    Raises:
        MyException: If text is None or document cleaning fails.
    """
    try:
        logging.info("Cleaning document text...")

        if text is None:
            raise ValueError("text cannot be None")

        if not text:
            return ""

        text = normalize_characters(text)
        text = repair_hyphenated_line_breaks(text)
        text = remove_page_artifacts(text)
        text = normalize_whitespace(text)

        logging.info("Document text cleaned.")
        return text

    except Exception as exc:
        logging.error(f"Failed to clean document text: {exc}")
        raise MyException(exc, sys) from exc


def main() -> None:
    """
    Demonstrates the document cleaning pipeline on sample text with extraction artifacts.

    Returns:
        None

    Raises:
        MyException: If running the document cleaning pipeline fails.
    """
    try:
        logging.info("Running document cleaning pipeline...")

        # file: Path = DOCUMENTS_DIRPATH / "ai_engineering.md"
        file: Path = PDFS_DIRPATH / "AI Engineering Building Applications.pdf"

        if not file.exists():
            logging.warning(f"Sample file not found at {file}")
            return

        raw_text: str
        if file.suffix.lower() == ".pdf":
            raw_text = extract_pdf_text(
                file=file,
                start_page=426,
                end_page=428,
            )
        else:
            raw_text = file.read_text(encoding="utf-8")

        cleaned_text: str = clean_document(text=raw_text)

        print(
            colored("_" * width, "grey"), colored("Cleaned text".center(width), "blue")
        )
        console.print(cleaned_text)
        print(colored("_" * width, "grey"))

        print(colored("_" * width, "grey"), colored("Stats".center(width), "blue"))
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
        print(colored("_" * width, "grey"))

        logging.info("Document cleaning pipeline completed.")

    except Exception as exc:
        logging.error(f"Failed to run document cleaning pipeline: {exc}")
        raise MyException(exc, sys) from exc


if __name__ == "__main__":
    main()
