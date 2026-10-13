"""
Provides hierarchical document splitting functionality across pages, paragraphs,
and sentences with deterministic UUID5 identifiers and parent lookup registry.
"""

import sys
from pathlib import Path
from typing import Any

from termcolor import colored

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document_ingestion.metadata_enrichment import enrich_metadata
from src.document_ingestion.pdf_cleaning import clean_pdf
from src.exception import DocumentParsingError, MyException, ValidationError
from src.logger import logging
from src.schema import DocumentMetadata, HierarchicalRecord, RegistryNode
from src.utils import (
    PARAMS_FILEPATH,
    PDFS_DIRPATH,
    extract_pdf_text,
    generate_uuid,
    get_paragraphs,
    get_sentences,
    get_terminal_width,
    load_yaml_file,
    print_divider,
    print_header,
)

Record = HierarchicalRecord
RegistryItem = RegistryNode

try:
    WIDTH: int = get_terminal_width()
    PARAMS: dict[str, Any] = (
        load_yaml_file(PARAMS_FILEPATH)
        .get("document_splitting", {})
        .get("hierarchical", {})
    )
    DEFAULT_START_PAGE: int = int(PARAMS.get("start_page", 426))
except Exception as e:
    logging.info(
        f"Failed to initialize hierarchical splitting module dependencies: {e}"
    )
    raise MyException(e, sys) from e

__all__: list[str] = [
    "Record",
    "RegistryItem",
    "get_hierarchical_splits",
]


def get_hierarchical_splits(
    pages: list[str],
    metadata: DocumentMetadata | None = None,
    start_page: int = DEFAULT_START_PAGE,
) -> tuple[dict[str, RegistryItem], list[Record]]:
    """
    Generate hierarchical document splits and parent registry across pages, paragraphs, and sentences.

    Creates deterministic UUID5 identifiers for pages, paragraphs, and sentences,
    populates a parent lookup registry, embeds split, section, and document metadata,
    and returns child sentence records linked to their parent paragraph and page identifiers.

    Args:
        pages (list[str]): A list of document page text strings.
        metadata (DocumentMetadata | None, optional): Enriched document-level metadata to embed.
            Defaults to None.
        start_page (int, optional): 1-indexed start page number. Defaults to DEFAULT_START_PAGE.

    Returns:
        tuple[dict[str, RegistryItem], list[Record]]: A tuple containing:
            - registry: Mapping from node UUID string to RegistryItem containing node type, text, and metadata.
            - splits: List of child Record items with sentence text, identifiers, and embedded metadata.
            Returns an empty registry and empty splits list if pages is empty.

    Raises:
        ValidationError: If pages is None or not a list.
        DocumentParsingError: If hierarchical splitting fails.
    """
    try:
        logging.info(
            f"Generating hierarchical splits for {len(pages) if pages is not None else 0} pages..."
        )

        if pages is None:
            raise ValidationError("pages cannot be None", sys)

        if not isinstance(pages, list):
            raise ValidationError(
                f"pages must be a list, got {type(pages).__name__}", sys
            )

        if not pages:
            logging.info("Pages list is empty; returning empty registry and splits.")
            return {}, []

        document_metadata: dict[str, Any] = dict(metadata or {})
        registry: dict[str, RegistryItem] = {}
        splits: list[Record] = []

        for page_offset, page in enumerate(pages):
            if page is None:
                raise ValidationError("page element cannot be None", sys)

            if not page.strip():
                continue

            current_page_no: int = start_page + page_offset
            page_id: str = generate_uuid(name=page, as_hex=True)
            registry[page_id] = {
                "type": "page",
                "text": page,
                "metadata": {
                    "split_metadata": {
                        "character_count": len(page),
                        "word_count": len(page.split()),
                    },
                    "section_metadata": {
                        "page_id": page_id,
                        "page_no": current_page_no,
                    },
                    "document_metadata": document_metadata,
                },
            }

            paragraphs: list[str] = get_paragraphs(text=page)
            for paragraph_index, paragraph in enumerate(paragraphs, 1):
                paragraph_id: str = generate_uuid(
                    name=f"{page_id}_{paragraph}",
                    as_hex=True,
                )
                registry[paragraph_id] = {
                    "type": "paragraph",
                    "text": paragraph,
                    "page_id": page_id,
                    "metadata": {
                        "split_metadata": {
                            "character_count": len(paragraph),
                            "word_count": len(paragraph.split()),
                        },
                        "section_metadata": {
                            "page_id": page_id,
                            "paragraph_id": paragraph_id,
                            "page_no": current_page_no,
                            "paragraph_no": paragraph_index,
                        },
                        "document_metadata": document_metadata,
                    },
                }

                sentences: list[str] = get_sentences(text=paragraph)
                for sentence_idx, sentence in enumerate(sentences, 1):
                    sentence_id: str = generate_uuid(
                        name=f"{page_id}_{paragraph_id}_{sentence}",
                        as_hex=True,
                    )
                    splits.append(
                        {
                            "id": sentence_id,
                            "sentence_id": sentence_id,
                            "text": sentence,
                            "paragraph_id": paragraph_id,
                            "page_id": page_id,
                            "metadata": {
                                "split_metadata": {
                                    "character_count": len(sentence),
                                    "word_count": len(sentence.split()),
                                },
                                "section_metadata": {
                                    "page_id": page_id,
                                    "paragraph_id": paragraph_id,
                                    "sentence_id": sentence_id,
                                    "page_no": current_page_no,
                                    "paragraph_no": paragraph_index,
                                    "sentence_no": sentence_idx,
                                },
                                "document_metadata": document_metadata,
                            },
                        }
                    )

        logging.info(
            f"Hierarchical splitting complete: {len(splits)} splits, {len(registry)} registry entries."
        )
        return registry, splits

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to generate hierarchical splits: {e}")
        raise DocumentParsingError(e, sys) from e


def main() -> None:
    """
    Demonstrate hierarchical splitting pipeline on extracted PDF document pages.

    Reads a sample PDF document from the configured PDF directory, cleans extracted text,
    enriches metadata, generates hierarchical splits and parent registry with embedded metadata,
    prints pipeline statistics, and displays formatted hierarchical sentence-paragraph-page
    relationships in the terminal.

    Returns:
        None

    Raises:
        MyException: If the hierarchical splitting pipeline fails.
    """
    try:
        logging.info("Running hierarchical splitting pipeline...")

        if not PDFS_DIRPATH.exists():
            raise FileNotFoundError(f"PDF directory does not exist: {PDFS_DIRPATH}")

        pdf_files: list[Path] = sorted(PDFS_DIRPATH.glob("*.pdf"))
        if not pdf_files:
            logging.info(f"No PDF files found in {PDFS_DIRPATH}.")
            return

        file: Path = pdf_files[0]
        logging.info(f"Processing PDF file: {file.name} (page {DEFAULT_START_PAGE})...")

        pages: list[str] = extract_pdf_text(
            file=file,
            start_page=DEFAULT_START_PAGE,
            end_page=DEFAULT_START_PAGE,
        )
        cleaned_pages: list[str] = [clean_pdf(text=page) for page in pages]
        metadata: DocumentMetadata = enrich_metadata(
            path=file,
            text=" ".join(cleaned_pages),
        )

        registry: dict[str, RegistryItem]
        splits: list[Record]
        registry, splits = get_hierarchical_splits(
            pages=cleaned_pages,
            metadata=metadata,
            start_page=DEFAULT_START_PAGE,
        )

        if not splits:
            logging.info("No splits generated from extracted pages.")
            return

        sample_splits: list[Record] = splits[2:4] if len(splits) >= 4 else splits[:2]
        for child in sample_splits:
            sentence: str = child["text"]
            highlighted_sentence: str = colored(sentence, "yellow")

            print_header("Sentence", line_color="white")
            print(f"\n{highlighted_sentence}\n")

            paragraph_item: RegistryItem = registry[child["paragraph_id"]]
            paragraph: str = paragraph_item["text"]
            highlighted_paragraph: str = paragraph.replace(
                sentence, highlighted_sentence, 1
            )

            print_header("Paragraph", line_color="white")
            print(f"\n{highlighted_paragraph}\n")

            page_item: RegistryItem = registry[child["page_id"]]
            page: str = page_item["text"]

            highlighted_page: str = page.replace(
                paragraph, colored(paragraph, "yellow"), 1
            )

            print_header("Page", line_color="white")
            print(f"\n{highlighted_page}\n")
            print_divider(color="white")

        logging.info("Hierarchical splitting pipeline completed successfully.")

    except Exception as e:
        logging.info(f"Failed to run hierarchical splitting pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
