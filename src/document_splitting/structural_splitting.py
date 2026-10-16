"""
Provides structural document splitting functionality based on hierarchical
markdown-style headings and breadcrumb trails.
"""

import sys
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.document_ingestion.document_cleaning import clean_document
from src.document_ingestion.document_parsing import parse_document
from src.document_ingestion.metadata_enrichment import enrich_metadata
from src.exception import DocumentParsingError, MyException, ValidationError
from src.logger import logging
from src.schema import DocumentMetadata, DocumentSection, SplitRecord
from src.utils import (
    DOCUMENTS_DIRPATH,
    PARAMS_FILEPATH,
    console,
    generate_uuid,
    get_terminal_width,
    load_yaml_file,
    print_divider,
    print_header,
)

try:
    WIDTH: int = get_terminal_width()
    PARAMS: dict[str, Any] = (
        load_yaml_file(PARAMS_FILEPATH)
        .get("document_splitting", {})
        .get("structural", {})
    )
    DEFAULT_MAX_SPLIT_SIZE: int = int(PARAMS.get("max_split_size", 50))
    DEFAULT_OVERLAP: int = int(PARAMS.get("overlap", 10))
    FILE_NAMES: list[str] = list(
        PARAMS.get("file_names", ["ai_engineering.md", "products_and_pricing.md"])
    )
except Exception as e:
    logging.info(f"Failed to initialize structural splitting module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["SplitRecord", "get_structural_splits"]


def get_structural_splits(
    document: list[DocumentSection],
    max_split_size: int = DEFAULT_MAX_SPLIT_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[SplitRecord]:
    """
    Split a structured document into heading-based text splits using a sliding window.

    Each section from the document is split into overlapping word windows while preserving
    its hierarchical heading breadcrumbs and enriched document metadata.

    Args:
        document (list[DocumentSection]): List of structured document sections to split.
        max_split_size (int, optional): Maximum number of words allowed per split.
            Defaults to DEFAULT_MAX_SPLIT_SIZE.
        overlap (int, optional): Number of overlapping words between consecutive splits.
            Defaults to DEFAULT_OVERLAP.

    Returns:
        list[SplitRecord]: A list of split dictionaries, each containing:
            - "id" (str): Deterministic UUID identifying the split.
            - "title" (str): Hierarchical section breadcrumb trail.
            - "text" (str): Split text content.
            - "metadata" (dict): Section metadata including section_id and document attributes.
            Returns an empty list if document is empty.

    Raises:
        ValidationError: If document is None, not a list, max_split_size is non-positive,
            or overlap is negative or greater than or equal to max_split_size.
        DocumentParsingError: If structural splitting fails.
    """
    try:
        logging.info("Generating structural splits...")

        if document is None:
            raise ValidationError("document cannot be None", sys)

        if not isinstance(document, list):
            raise ValidationError(
                f"document must be a list of DocumentSection, got {type(document).__name__}",
                sys,
            )

        if max_split_size <= 0:
            raise ValidationError(
                f"max_split_size must be greater than zero, got {max_split_size}",
                sys,
            )

        if overlap < 0 or overlap >= max_split_size:
            raise ValidationError(
                f"overlap must be non-negative and less than max_split_size ({max_split_size}), got {overlap}",
                sys,
            )

        if not document:
            logging.info("Document section list is empty; returning empty splits.")
            return []

        splits: list[SplitRecord] = []
        step: int = max_split_size - overlap

        for section in document:
            section_id: str = section.get("id", "")
            section_metadata: dict[str, Any] = section.get("metadata", {})
            body: str = section.get("text", "")
            section_data: dict[str, Any] = dict(
                section_metadata.get("section_metadata") or {}
            )
            breadcrumb: str = str(
                section.get("title")
                or section_metadata.get("title")
                or section_data.get("title", "")
            )
            words: list[str] = body.split()

            if not words:
                continue

            if len(words) <= max_split_size:
                split_text: str = " ".join(words)
                splits.append(
                    {
                        "id": generate_uuid(
                            name=f"{section_id}_{breadcrumb}_{split_text}", as_hex=True
                        ),
                        "title": breadcrumb,
                        "text": split_text,
                        "metadata": {
                            "split_metadata": {
                                "character_count": len(split_text),
                                "word_count": len(split_text.split()),
                            },
                            "section_metadata": {
                                "section_id": section_id,
                                **section_data,
                            },
                            "document_metadata": section_metadata.get(
                                "document_metadata", {}
                            ),
                        },
                    }
                )
                continue

            i: int = 0
            n: int = len(words)

            while i < n:
                split_words: list[str] = words[i : i + max_split_size]
                split_text = " ".join(split_words)
                splits.append(
                    {
                        "id": generate_uuid(
                            name=f"{section_id}_{breadcrumb}_{split_text}", as_hex=True
                        ),
                        "title": breadcrumb,
                        "text": split_text,
                        "metadata": {
                            "split_metadata": {
                                "character_count": len(split_text),
                                "word_count": len(split_text.split()),
                            },
                            "section_metadata": {
                                "section_id": section_id,
                                **section_data,
                            },
                            "document_metadata": section_metadata.get(
                                "document_metadata", {}
                            ),
                        },
                    }
                )
                if i + max_split_size >= n:
                    break
                i += step

        logging.info(f"Generated {len(splits)} structural splits successfully.")
        return splits

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to generate structural splits: {e}")
        raise DocumentParsingError(e, sys) from e


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
        files: list[Path] = [DOCUMENTS_DIRPATH / file_name for file_name in FILE_NAMES]

        for file in files:
            if not file.exists():
                logging.info(f"File not found: {file}")
                continue

            text: str = file.read_text(encoding="utf-8")
            cleaned_text: str = clean_document(text=text)
            metadata: DocumentMetadata = enrich_metadata(path=file, text=cleaned_text)
            parsed_document: list[DocumentSection] = parse_document(
                path=file, text=cleaned_text, metadata=metadata
            )
            splits: list[SplitRecord] = get_structural_splits(document=parsed_document)

            print_header(file.name)
            for split in splits:
                console.print_json(data=dict(split))
            print_divider()

        logging.info("Structural splitting pipeline completed.")

    except Exception as e:
        logging.info(f"Failed to run structural splitting pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
