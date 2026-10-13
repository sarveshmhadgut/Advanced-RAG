"""
Provides semantic document splitting functionality using spaCy sentence segmentation
and Google Generative AI embeddings similarity thresholds.
"""

import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langsmith import traceable

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document_ingestion.metadata_enrichment import enrich_metadata
from src.document_ingestion.pdf_cleaning import clean_pdf
from src.document_ingestion.pdf_parsing import parse_pdf
from src.exception import EmbeddingError, MyException, ValidationError
from src.logger import logging
from src.schema import DocumentMetadata, DocumentSection, SplitRecord
from src.utils import (
    PARAMS_FILEPATH,
    PDFS_DIRPATH,
    console,
    extract_pdf_text,
    generate_uuid,
    get_embedding_model,
    get_similarities_scores,
    get_spacy_sentences,
    get_terminal_width,
    load_yaml_file,
    print_divider,
    print_header,
)

try:
    load_dotenv()

    WIDTH: int = get_terminal_width()
    PARAMS: dict[str, Any] = (
        load_yaml_file(PARAMS_FILEPATH)
        .get("document_splitting", {})
        .get("semantic", {})
    )

    SIMILARITY_THRESHOLD: float = float(PARAMS.get("similarity_threshold", 0.8))
    MAX_SPLIT_SIZE: int = int(PARAMS.get("max_split_size", 600))
    START_PAGE: int | None = (
        int(PARAMS["start_page"]) if PARAMS.get("start_page") is not None else None
    )
    END_PAGE: int | None = (
        int(PARAMS["end_page"]) if PARAMS.get("end_page") is not None else None
    )
    PDF_NAME: str | None = (
        str(PARAMS.get("pdf_name")) if PARAMS.get("pdf_name") else None
    )

except Exception as e:
    logging.info(f"Failed to initialize semantic splitting module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["get_semantic_splits"]


@traceable(name="get_semantic_splits")
def get_semantic_splits(
    document: list[DocumentSection] | str,
    metadata: DocumentMetadata | None = None,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    max_split_size: int = MAX_SPLIT_SIZE,
    model: GoogleGenerativeAIEmbeddings | None = None,
) -> list[SplitRecord]:
    """
    Split a structured document or raw text into semantically cohesive splits based
    on sentence embedding similarity and maximum split size limit, embedding document
    and split metadata into each returned record.

    Args:
        document (list[DocumentSection] | str): List of parsed document sections or raw text.
        metadata (DocumentMetadata | None, optional): Enriched document-level metadata to embed.
            Defaults to None.
        similarity_threshold (float, optional): Cosine similarity threshold below which a split
            boundary is triggered. Defaults to SIMILARITY_THRESHOLD.
        max_split_size (int, optional): Maximum character length of a split.
            Defaults to MAX_SPLIT_SIZE.
        model (GoogleGenerativeAIEmbeddings | None, optional): Embedding model to use.
            Defaults to the lazily initialized default model.

    Returns:
        list[SplitRecord]: A list of semantically cohesive text splits with embedded metadata.
            Returns an empty list if the document is empty or contains no extractable sentences.

    Raises:
        ValidationError: If inputs are invalid.
        EmbeddingError: If semantic splitting fails.
    """
    try:
        logging.info(
            f"Generating semantic splits (similarity_threshold={similarity_threshold}, max_split_size={max_split_size})..."
        )

        if document is None:
            raise ValidationError("document cannot be None", sys)

        if not (0.0 <= similarity_threshold <= 1.0):
            raise ValidationError(
                f"similarity_threshold must be between 0.0 and 1.0, got {similarity_threshold}",
                sys,
            )

        if max_split_size <= 0:
            raise ValidationError(
                f"max_split_size must be greater than zero, got {max_split_size}",
                sys,
            )

        document_metadata: dict[str, Any] = dict(metadata or {})
        if not document_metadata and isinstance(document, list) and document:
            first_document = document[0]
            if isinstance(first_document, dict):
                first_meta: dict[str, Any] = first_document.get("metadata", {})
                document_metadata = dict(first_meta.get("document_metadata") or {})

        sections: list[DocumentSection]
        if isinstance(document, str):
            sections = [
                {
                    "id": "",
                    "text": document.strip(),
                    "metadata": {
                        "section_metadata": {},
                        "document_metadata": document_metadata,
                    },
                }
            ]
        elif isinstance(document, list):
            sections = document
        else:
            raise ValidationError(
                f"document must be a list of DocumentSection or str, got {type(document).__name__}",
                sys,
            )

        sentences: list[tuple[str, str, str, dict[str, Any]]] = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            text: str = str(section.get("text", "")).strip()
            if not text:
                continue

            section_id: str = str(section.get("id", ""))
            entry_metadata: dict[str, Any] = section.get("metadata", {})
            section_metadata: dict[str, Any] = dict(
                entry_metadata.get("section_metadata") or {}
            )
            if not section_metadata and "document_metadata" not in entry_metadata:
                section_metadata = dict(entry_metadata)

            document_metadata = dict(
                entry_metadata.get("document_metadata") or document_metadata
            )
            breadcrumb: str = str(
                section.get("title")
                or section_metadata.get("title")
                or document_metadata.get("title", "")
            )
            section_metadata = {
                "section_metadata": section_metadata,
                "document_metadata": document_metadata,
            }

            for sentence in get_spacy_sentences(text=text):
                sentences.append((sentence, section_id, breadcrumb, section_metadata))

        if not sentences:
            logging.info("No sentences found in document; returning empty splits list.")
            return []

        if len(sentences) == 1:
            logging.info(
                "Single sentence document; returning sentence as single split."
            )
            split_text, section_id, breadcrumb, section_metadata = sentences[0]
            return [
                {
                    "id": generate_uuid(name=f"{section_id}_{breadcrumb}_{split_text}"),
                    "title": breadcrumb,
                    "text": split_text,
                    "metadata": {
                        "split_metadata": {
                            "character_count": len(split_text),
                            "word_count": len(split_text.split()),
                        },
                        "section_metadata": {
                            "section_id": section_id,
                            **(section_metadata.get("section_metadata") or {}),
                        },
                        "document_metadata": section_metadata.get(
                            "document_metadata", {}
                        ),
                    },
                }
            ]

        sentences_list: list[str] = [sentence for sentence, _, _, _ in sentences]
        active_model: GoogleGenerativeAIEmbeddings = model or get_embedding_model()
        similarities: list[float] = get_similarities_scores(
            sentences=sentences_list, model=active_model
        )
        splits: list[SplitRecord] = []
        current_split: str = sentences_list[0]
        current_section_id: str = sentences[0][1]
        current_breadcrumb: str = sentences[0][2]
        current_section_metadata: dict[str, Any] = sentences[0][3]

        for similarity, (sentence, section_id, breadcrumb, section_metadata) in zip(
            similarities, sentences[1:]
        ):
            split_size: int = len(current_split) + len(sentence) + 1

            if similarity < similarity_threshold or split_size > max_split_size:
                split_text = current_split
                section_id = current_section_id
                breadcrumb = current_breadcrumb
                section_metadata = current_section_metadata
                splits.append(
                    {
                        "id": generate_uuid(
                            name=f"{section_id}_{breadcrumb}_{split_text}"
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
                                **(section_metadata.get("section_metadata") or {}),
                            },
                            "document_metadata": section_metadata.get(
                                "document_metadata", {}
                            ),
                        },
                    }
                )

                current_split = sentence
                current_section_id = section_id
                current_breadcrumb = breadcrumb
                current_section_metadata = section_metadata

            else:
                current_split += " " + sentence

        if current_split:
            split_text = current_split
            section_id = current_section_id
            breadcrumb = current_breadcrumb
            section_metadata = current_section_metadata
            splits.append(
                {
                    "id": generate_uuid(name=f"{section_id}_{breadcrumb}_{split_text}"),
                    "title": breadcrumb,
                    "text": split_text,
                    "metadata": {
                        "split_metadata": {
                            "character_count": len(split_text),
                            "word_count": len(split_text.split()),
                        },
                        "section_metadata": {
                            "section_id": section_id,
                            **(section_metadata.get("section_metadata") or {}),
                        },
                        "document_metadata": section_metadata.get(
                            "document_metadata", {}
                        ),
                    },
                }
            )

        logging.info(f"Generated {len(splits)} semantic splits successfully.")
        return splits

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to generate semantic splits: {e}")
        raise EmbeddingError(e, sys) from e


def main() -> None:
    """
    Demonstrates semantic splitting pipeline on extracted PDF documents.

    Reads PDF files from the configured PDF directory, cleans extracted text,
    enriches metadata, parses pages into structured blocks, splits them semantically
    using embedding similarity, and prints the generated split records.

    Returns:
        None

    Raises:
        MyException: If the semantic splitting pipeline fails.
    """
    try:
        logging.info("Running semantic splitting pipeline...")

        if not PDFS_DIRPATH.exists():
            raise FileNotFoundError(f"PDF directory does not exist: {PDFS_DIRPATH}")

        files: list[Path]
        if PDF_NAME:
            target_file: Path = PDFS_DIRPATH / PDF_NAME
            if not target_file.exists():
                raise FileNotFoundError(
                    f"Configured PDF file does not exist: {target_file}"
                )
            files = [target_file]
        else:
            files = sorted(PDFS_DIRPATH.glob("*.pdf"))

        if not files:
            logging.info(f"No PDF files found in {PDFS_DIRPATH}.")
            return

        for file in files:
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
            splits: list[SplitRecord] = get_semantic_splits(
                document=parsed_pdf, metadata=metadata
            )

            print_header(file.name)
            console.print_json(
                data={
                    "total splits": len(splits),
                    "splits": [s for s in splits[:5]],
                }
            )
            print_divider()

        logging.info("Semantic splitting pipeline completed successfully.")

    except Exception as e:
        logging.info(f"Failed to run semantic splitting pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
