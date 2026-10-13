"""
Text segmentation and manipulation utilities for sentences and paragraphs.
"""

import re
import sys
from functools import cache
from pathlib import Path

import pymupdf
import spacy
from spacy.tokens import Doc

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exception import (
    DocumentParsingError,
    EmbeddingError,
    MyException,
    ValidationError,
)
from src.logger import logging

__all__: list[str] = [
    "extract_pdf_text",
    "get_nlp",
    "get_paragraphs",
    "get_sentences",
    "get_spacy_sentences",
    "remove_stopwords",
]


def get_paragraphs(text: str) -> list[str]:
    """
    Segment input text into individual non-empty paragraphs separated by blank lines.

    Args:
        text (str): The input text to segment into paragraphs.

    Returns:
        list[str]: A list of non-empty paragraph strings. Returns an empty list if
            text is empty or contains only whitespace.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If paragraph segmentation fails.
    """
    try:
        logging.info("Segmenting text into paragraphs...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        if not text.strip():
            logging.info("Input text is empty; returning empty paragraph list.")
            return []

        paragraphs: list[str] = [
            p.replace("\n", " ").strip()
            for p in re.split(r"\n\s*\n", text)
            if p.strip()
        ]

        logging.info(f"Segmented {len(paragraphs)} paragraphs successfully.")
        return paragraphs

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to segment paragraphs: {e}")
        raise DocumentParsingError(e, sys) from e


def get_sentences(text: str) -> list[str]:
    """
    Segment input text into individual sentences based on punctuation boundary patterns.

    Args:
        text (str): The input text to segment into sentences.

    Returns:
        list[str]: A list of non-empty sentence strings. Returns an empty list if
            text is empty or contains only whitespace.

    Raises:
        ValidationError: If text is None.
        DocumentParsingError: If sentence segmentation fails.
    """
    try:
        logging.info("Segmenting text into sentences...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        if not text.strip():
            logging.info("Input text is empty; returning empty sentence list.")
            return []

        sentences: list[str] = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()
        ]

        logging.info(f"Segmented {len(sentences)} sentences successfully.")
        return sentences

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to segment sentences: {e}")
        raise DocumentParsingError(e, sys) from e


@cache
def get_nlp() -> spacy.Language:
    """
    Lazily initialize and cache the spaCy English language pipeline.

    Returns:
        spacy.Language: The loaded and configured spaCy language model.

    Raises:
        EmbeddingError: If the spaCy language model cannot be loaded.
    """
    try:
        logging.info("Loading spaCy model 'en_core_web_sm'...")
        nlp_model: spacy.Language = spacy.load("en_core_web_sm")
        nlp_model.Defaults.stop_words.discard("not")
        logging.info("spaCy language model loaded successfully.")
        return nlp_model
    except Exception as e:
        logging.info(f"Failed to load spaCy language model: {e}")
        raise EmbeddingError(e, sys) from e


def remove_stopwords(text: str) -> str:
    """
    Remove English stopwords from text while retaining negation words like 'not'.

    Args:
        text (str): The input text to process.

    Returns:
        str: Text with stopwords removed. Returns an empty string if input is empty.

    Raises:
        ValidationError: If text is None.
        EmbeddingError: If NLP processing fails.
    """
    try:
        logging.info("Removing stopwords from text...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        if not text.strip():
            logging.info("Input text is empty; returning empty string.")
            return ""

        nlp: spacy.Language = get_nlp()
        doc: Doc = nlp(text=text)
        doc.vocab["not"].is_stop = False

        filtered_text: str = " ".join(
            [token.text for token in doc if not token.is_stop]
        )
        logging.info("Stopwords removed successfully.")
        return filtered_text

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to remove stopwords: {e}")
        raise EmbeddingError(e, sys) from e


def get_spacy_sentences(text: str) -> list[str]:
    """
    Segment input text into individual sentences using spaCy sentence boundary detection.

    Args:
        text (str): The input text to segment into sentences.

    Returns:
        list[str]: A list of non-empty sentence strings. Returns an empty list if text is empty.

    Raises:
        ValidationError: If text is None.
        EmbeddingError: If sentence segmentation fails.
    """
    try:
        logging.info("Segmenting text into sentences with spaCy...")

        if text is None:
            raise ValidationError("text cannot be None", sys)

        if not text.strip():
            logging.info("Input text is empty; returning empty sentence list.")
            return []

        nlp: spacy.Language = get_nlp()
        doc: Doc = nlp(text=text)
        sentences: list[str] = [
            sentence.text.strip() for sentence in doc.sents if sentence.text.strip()
        ]

        logging.info(f"Segmented {len(sentences)} sentences successfully.")
        return sentences

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to segment sentences: {e}")
        raise EmbeddingError(e, sys) from e


def extract_pdf_text(
    file: Path,
    start_page: int | None = None,
    end_page: int | None = None,
) -> list[str]:
    """
    Extract text page-by-page from a PDF while preserving structural boundaries.

    Args:
        file (Path): The file path to the PDF document.
        start_page (int, optional): 1-indexed starting page number (inclusive). Defaults to None.
        end_page (int, optional): 1-indexed ending page number (inclusive). Defaults to None.

    Returns:
        list[str]: Cleaned and structured text per page extracted from the specified page range.

    Raises:
        ValidationError: If page range arguments are invalid.
        DocumentParsingError: If PDF extraction fails.
    """
    try:
        logging.info(f"Extracting PDF text from: {file}...")

        if not file:
            raise ValidationError("file must be provided", sys)

        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        if file.suffix.lower() != ".pdf":
            raise ValidationError(
                f"Expected a PDF file (.pdf), but got '{file.suffix}': {file.name}",
                sys,
            )

        if start_page is not None and start_page <= 0:
            raise ValidationError("start_page must be greater than zero", sys)

        if end_page is not None and end_page <= 0:
            raise ValidationError("end_page must be greater than zero", sys)

        if start_page is not None and end_page is not None and start_page > end_page:
            raise ValidationError("start_page cannot be greater than end_page", sys)

        page_texts: list[str] = []

        with pymupdf.open(file) as pdf:
            total_pages: int = len(pdf)

            if start_page is not None and start_page > total_pages:
                raise ValidationError(
                    f"start_page ({start_page}) exceeds total document pages ({total_pages})",
                    sys,
                )

            for page_num, page in enumerate(pdf, start=1):
                if start_page and page_num < start_page:
                    continue

                if end_page and page_num > end_page:
                    break

                page_blocks: list[str] = []
                prev_y1: float | None = None

                for block in page.get_text("blocks", sort=True):
                    block_text: str = str(block[4]).strip()

                    if not block_text:
                        continue

                    y0, y1 = float(block[1]), float(block[3])
                    if prev_y1 is not None:
                        page_blocks.append("\n" if 0 <= y0 - prev_y1 <= 15 else "\n\n")

                    page_blocks.append(block_text)
                    prev_y1 = y1

                page_texts.append("".join(page_blocks))

        logging.info(f"Extracted text from {len(page_texts)} pages successfully.")
        return page_texts

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to extract PDF text: {e}")
        raise DocumentParsingError(e, sys) from e
