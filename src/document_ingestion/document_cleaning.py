"""
Utilities for cleaning and normalizing markdown and text documents while preserving structural elements.
"""

import re
import sys
from pathlib import Path

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exception import DocumentParsingError, MyException, ValidationError
from src.logger import logging
from src.utils import (
    DOCUMENTS_DIRPATH,
    console,
    get_terminal_width,
    print_divider,
    print_header,
)

try:
    WIDTH: int = get_terminal_width()
except Exception as e:
    logging.info(f"Failed to initialize document cleaning module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = [
    "clean_document",
    "normalize_characters",
    "normalize_whitespace",
]


def normalize_characters(text: str) -> str:
    """
    Normalize control characters, null bytes, special whitespace, and line endings.

    Args:
        text (str): Raw document text.

    Returns:
        str: Text with unified newlines, removed control characters, and normalized whitespace symbols.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If character normalization fails.
    """
    try:
        logging.info("Normalizing document characters...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        # Remove null bytes and non-printable control characters.
        text = text.replace("\x00", "")
        text = re.sub(
            r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]",
            "",
            text,
        )

        # Normalize special whitespace characters and BOM.
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

        # Unify line endings to \n.
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        logging.info("Document characters normalized successfully.")
        return text

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to normalize document characters: {e}")
        raise DocumentParsingError(e, sys) from e


def normalize_whitespace(text: str, preserve_markdown: bool = True) -> str:
    """
    Normalize whitespace while optionally preserving Markdown structural elements and paragraph breaks.

    When preserve_markdown is True, preserves headings (#), lists (- / * / 1.), blockquotes (>),
    tables (|), code fences (```), and blank-line paragraph boundaries.
    When False, collapses soft line wraps within paragraphs into single spaces (ideal for PDF extractions).

    Args:
        text (str): Document text with inconsistent whitespace.
        preserve_markdown (bool, optional): Whether to preserve Markdown structural elements.
            Defaults to True.

    Returns:
        str: Text with normalized intra-line spacing and clean paragraph separation.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If whitespace normalization fails.
    """
    try:
        logging.info("Normalizing document whitespace...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        # Ensure line endings are standard.
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Strip trailing spaces from each line.
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

        if preserve_markdown:
            # Ensure headings have isolated blank lines around them.
            text = re.sub(r"(?m)^([ \t]*#+.*)$", r"\n\n\1\n\n", text)

        # Normalize multiple blank lines to double newlines (paragraph boundary).
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Process paragraph by paragraph.
        paragraphs: list[str] = [p.strip() for p in text.split("\n\n") if p.strip()]

        cleaned_paragraphs: list[str] = []
        for paragraph in paragraphs:
            lines: list[str] = paragraph.splitlines()

            # If preserve_markdown is enabled and it's a code block or multi-line list/table, preserve line structure.
            if preserve_markdown and any(
                re.match(r"^\s*(#+|-|\*|\+|\d+\.|>|\||```)", line) for line in lines
            ):
                cleaned_lines: list[str] = [
                    re.sub(r"[ \t]{2,}", " ", line.rstrip()) for line in lines
                ]
                cleaned_paragraphs.append("\n".join(cleaned_lines))
            else:
                # Regular paragraph: normalize intra-paragraph spaces while joining lines.
                single_para: str = re.sub(r"[ \t]*\n[ \t]*", " ", paragraph)
                single_para = re.sub(r"[ \t]{2,}", " ", single_para)
                single_para = re.sub(r"[ \t]+([,.;:!?])", r"\1", single_para)
                cleaned_paragraphs.append(single_para.strip())

        result: str = "\n\n".join(cleaned_paragraphs)
        logging.info("Document whitespace normalized successfully.")
        return result

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to normalize document whitespace: {e}")
        raise DocumentParsingError(e, sys) from e


def clean_document(text: str) -> str:
    """
    Clean and normalize a markdown or text document while preserving all structural elements.

    Args:
        text (str): Raw document text.

    Returns:
        str: Cleaned text with normalized characters, spacing, and structural boundaries.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If document cleaning fails.
    """
    try:
        logging.info("Cleaning document text...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        if not text:
            return ""

        text = normalize_characters(text)
        text = normalize_whitespace(text)

        logging.info("Document text cleaned successfully.")
        return text

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to clean document text: {e}")
        raise DocumentParsingError(e, sys) from e


def main() -> None:
    """
    Demonstrates the document cleaning pipeline on sample markdown documents.

    Returns:
        None

    Raises:
        MyException: If running the document cleaning demonstration fails.
    """
    try:
        logging.info("Running document cleaning pipeline demonstration...")

        files: list[Path] = sorted(
            [
                *DOCUMENTS_DIRPATH.glob("*.md"),
                *DOCUMENTS_DIRPATH.glob("*.txt"),
            ]
        )
        for file in files:
            if not file.exists():
                logging.info(f"Sample file not found at {file}")
                continue

            raw_text: str = file.read_text(encoding="utf-8")
            cleaned_text: str = clean_document(text=raw_text)

            print_header(f"Cleaned: {file.name}")
            console.print(cleaned_text, markup=False)
            print_divider()

            print_header("Stats")
            console.print_json(
                data={
                    "File": file.name,
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

        logging.info("Document cleaning pipeline demonstration completed.")

    except Exception as e:
        logging.info(f"Failed to run document cleaning pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
