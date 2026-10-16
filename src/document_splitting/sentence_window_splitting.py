"""
Provides sentence-window document splitting functionality.

Splits document sections into individual sentences, augmented with surrounding
contextual sentences (the sentence window) for enhanced retrieval fidelity.
"""

import sys
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document_ingestion.metadata_enrichment import enrich_metadata
from src.document_ingestion.pdf_cleaning import clean_pdf
from src.document_ingestion.pdf_parsing import parse_pdf
from src.exception import DocumentParsingError, MyException, ValidationError
from src.logger import logging
from src.schema import DocumentMetadata, DocumentSection, SplitRecord
from src.utils import (
    PARAMS_FILEPATH,
    PDFS_DIRPATH,
    console,
    extract_pdf_text,
    generate_uuid,
    get_sentences,
    load_yaml_file,
    print_divider,
    print_header,
)

try:
    PARAMS: dict[str, Any] = load_yaml_file(PARAMS_FILEPATH).get(
        "document_splitting", {}
    ).get("sentence_window", {}) or load_yaml_file(PARAMS_FILEPATH).get(
        "document_splitting", {}
    ).get("sentence_window", {})

    START_PAGE: int | None = (
        int(PARAMS["start_page"]) if PARAMS.get("start_page") is not None else None
    )
    END_PAGE: int | None = (
        int(PARAMS["end_page"]) if PARAMS.get("end_page") is not None else None
    )
    PDF_NAME: str | None = (
        str(PARAMS.get("pdf_name")) if PARAMS.get("pdf_name") is not None else None
    )
    DEFAULT_WINDOW_SIZE: int = int(PARAMS.get("window_size", 1))
except Exception as e:
    logging.info(f"Failed to initialize sentence window splitting configuration: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["get_sentence_window_splits"]


def get_sentence_window_splits(
    document: list[DocumentSection],
    metadata: DocumentMetadata | None = None,
    window: int = DEFAULT_WINDOW_SIZE,
) -> list[SplitRecord]:
    """
    Split document sections into sentence-window records containing a focus sentence and its surrounding window.

    Args:
        document (list[DocumentSection]): The parsed document sections to segment.
        metadata (DocumentMetadata | None, optional): Optional document metadata payload. Defaults to None.
        window (int, optional): The number of contextual sentences before and after each focus sentence. Defaults to 1.

    Returns:
        list[SplitRecord]: A list of split records with sentence text, window text, and metadata.

    Raises:
        ValidationError: If document is None or window is negative.
        DocumentParsingError: If sentence window splitting fails.
    """
    try:
        logging.info("Generating sentence-window splits...")

        if document is None:
            raise ValidationError("document cannot be None", sys)

        if window < 0:
            raise ValidationError(
                f"window must be greater than or equal to 0, got: {window}", sys
            )

        splits: list[SplitRecord] = []
        for section in document:
            section_id: str = section["id"]
            section_metadata: dict[str, Any] = section.get("metadata", {}).get(
                "section_metadata", {}
            )

            section_text: str = section["text"]
            section_sentences: list[str] = get_sentences(text=section_text)

            document_metadata: dict[str, Any] = (
                dict(metadata)
                if metadata is not None
                else section.get("metadata", {}).get("document_metadata", {})
            )

            n: int = len(section_sentences)
            for index, sentence in enumerate(section_sentences):
                start: int = max(0, index - window)
                end: int = min(n, index + window + 1)

                window_text: str = " ".join(section_sentences[start:end])
                splits.append(
                    {
                        "id": generate_uuid(name=f"{sentence}", as_hex=True),
                        "text": sentence,
                        "window_text": window_text,
                        "metadata": {
                            "split_metadata": {
                                "text_character_count": len(sentence),
                                "text_word_count": len(sentence.split()),
                                "window_character_count": len(window_text),
                                "window_word_count": len(window_text.split()),
                            },
                            "section_metadata": {
                                "section_id": section_id,
                                **section_metadata,
                            },
                            "document_metadata": document_metadata,
                        },
                    }
                )

        logging.info(
            f"Successfully generated {len(splits)} sentence-window splits across {len(document)} sections."
        )
        return splits

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to generate sentence window splits: {e}")
        raise DocumentParsingError(e, sys) from e


def main() -> None:
    """
    Demonstrate sentence-window splitting on a configured PDF document.

    Returns:
        None

    Raises:
        MyException: If the sentence-window splitting pipeline fails.
    """
    try:
        logging.info("Starting sentence-window splitting pipeline...")

        if not PDF_NAME:
            raise ValidationError(
                "PDF_NAME is not configured in params.yml under document_splitting.sentence_window_splitting.pdf_name",
                sys,
            )

        file: Path = PDFS_DIRPATH / PDF_NAME
        if not file.exists():
            raise FileNotFoundError(f"PDF file not found: {file}")

        pages: list[str] = extract_pdf_text(
            file=file,
            start_page=START_PAGE,
            end_page=END_PAGE,
        )
        cleaned_pages: list[str] = [clean_pdf(text=page) for page in pages]
        metadata: DocumentMetadata = enrich_metadata(
            path=file, text=" ".join(cleaned_pages)
        )
        parsed_pdf: list[DocumentSection] = parse_pdf(
            path=file,
            pages=cleaned_pages,
            metadata=metadata,
            start_page=START_PAGE or 1,
        )
        splits: list[SplitRecord] = get_sentence_window_splits(
            document=parsed_pdf, metadata=metadata
        )

        print_header(file.name)
        console.print_json(
            data={
                "total splits": len(splits),
                "splits": [dict(s) for s in splits[:5]],
            }
        )
        print_divider()
        logging.info("Sentence-window splitting pipeline completed successfully.")

    except Exception as e:
        logging.info(f"Failed to execute sentence-window splitting pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
