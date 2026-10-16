"""
Parses PDF files directly using PyMuPDF to extract text along with physical
block metadata, classifying each block as header, table, or paragraph.
"""

import re
import sys
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document_ingestion.metadata_enrichment import enrich_metadata
from src.document_ingestion.pdf_cleaning import clean_pdf
from src.exception import DocumentParsingError, MyException, ValidationError
from src.logger import logging
from src.schema import DocumentMetadata, DocumentSection
from src.utils import (
    PARAMS_FILEPATH,
    PDFS_DIRPATH,
    console,
    extract_pdf_text,
    generate_uuid,
    load_yaml_file,
    print_divider,
    print_header,
)

try:
    PARAMS: dict[str, Any] = (
        load_yaml_file(PARAMS_FILEPATH)
        .get("document_ingestion", {})
        .get("pdf_parsing", {})
    )
    PYMUPDF_TEXT_INDEX: int = int(PARAMS.get("pdf_text_index", 4))
except Exception as e:
    logging.info(f"Failed to initialize PDF parsing module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["parse_pdf"]


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
        ValidationError: If line is None.
    """
    try:
        logging.info("Labeling line...")

        if line is None:
            raise ValidationError("line cannot be None", sys)

        tokens: list[str] = line.split()

        # Long uppercase or colon-ending lines are likely section headers
        if len(tokens) >= 10 and (line.isupper() or line.endswith(":")):
            return "header"
        # Multiple large whitespace gaps or pipes suggest tabular data
        elif len(re.findall(r"\s{2,}|\|", line)) >= 2:
            return "table"

        logging.info("Line labeled.")
        return "paragraph"

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to label line: {e}")
        raise DocumentParsingError(e, sys) from e


def parse_pdf(
    path: Path,
    pages: list[str] | None = None,
    metadata: DocumentMetadata | None = None,
    blocks: list[str] | list[list[str]] | None = None,
    start_page: int = 1,
) -> list[DocumentSection]:
    """
    Parses a PDF into structured block-level entries from cleaned pages,
    cleaned blocks, or directly from the document file.

    Args:
        path (Path): The file path to the PDF document.
        pages (list[str] | None, optional): Pre-cleaned page strings to segment into blocks.
            Defaults to None.
        metadata (DocumentMetadata | None, optional): Enriched document metadata.
            Defaults to None.
        blocks (list[str] | list[list[str]] | None, optional): Pre-cleaned block strings
            (either a flat list for a single page or a list of block lists per page).
            Defaults to None.
        start_page (int, optional): 1-indexed starting page number for page indexing.
            Defaults to 1.

    Returns:
        list[DocumentSection]: A list of entry dictionaries, each containing:
            - "id" (str): Deterministic UUID identifying the block.
            - "text" (str): Cleaned block text content.
            - "metadata" (dict[str, Any]): Nested section and document metadata.
            Returns an empty list if no blocks are extracted.

    Raises:
        ValidationError: If path or start_page are invalid.
        DocumentParsingError: If PDF parsing fails.
    """
    try:
        logging.info(f"Parsing PDF: {path}...")

        if path is None:
            raise ValidationError("path cannot be None", sys)

        file_path: Path = Path(path)
        if start_page < 1:
            raise ValidationError(
                f"start_page must be greater than or equal to 1, got: {start_page}",
                sys,
            )

        page_items: list[tuple[int, list[str]]] = []

        if blocks is not None:
            if blocks and isinstance(blocks[0], list):
                for page_offset, page_block_list in enumerate(blocks):
                    current_page: int = start_page + page_offset
                    valid_blocks: list[str] = [
                        str(b).strip() for b in page_block_list if str(b).strip()
                    ]
                    page_items.append((current_page, valid_blocks))
            elif blocks:
                valid_blocks = [str(b).strip() for b in blocks if str(b).strip()]
                page_items.append((start_page, valid_blocks))
        elif pages is not None:
            for page_offset, page_content in enumerate(pages):
                current_page = start_page + page_offset
                if page_content is None:
                    continue
                extracted_blocks: list[str] = [
                    b.strip()
                    for b in re.split(r"\n\s*\n", str(page_content))
                    if b.strip()
                ]
                page_items.append((current_page, extracted_blocks))
        else:
            if not file_path.exists():
                raise ValidationError(f"File not found: {file_path}", sys)
            if file_path.suffix.lower() != ".pdf":
                raise ValidationError(
                    f"Expected a PDF file, got: {file_path.suffix}", sys
                )
            raw_pages: list[str] = extract_pdf_text(file=file_path)
            for page_offset, raw_page in enumerate(raw_pages):
                current_page = start_page + page_offset
                cleaned_page: str = clean_pdf(text=raw_page)
                extracted_blocks = [
                    b.strip() for b in re.split(r"\n\s*\n", cleaned_page) if b.strip()
                ]
                page_items.append((current_page, extracted_blocks))

        entries: list[DocumentSection] = []
        for page_number, block_list in page_items:
            for block_number, text in enumerate(block_list, 1):
                lines: list[str] = [line for line in text.splitlines() if line.strip()]
                kind: str = (
                    "table"
                    if any(label_line(line) == "table" for line in lines)
                    else label_line(text)
                )
                entry: DocumentSection = {
                    "id": generate_uuid(
                        f"{page_number}_{block_number}_{text}", as_hex=True
                    ),
                    "text": text,
                    "metadata": {
                        "section_metadata": {
                            "page_no": page_number,
                            "block_no": block_number,
                            "kind": kind,
                            "character_count": len(text),
                            "word_count": len(text.split()),
                        },
                        "document_metadata": metadata or {},
                    },
                }
                entries.append(entry)

        logging.info(f"Parsed {len(entries)} blocks from PDF: {file_path.name}.")
        return entries

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to parse PDF: {e}")
        raise DocumentParsingError(e, sys) from e


def main() -> None:
    """
    Demonstrates the PDF parsing pipeline by extracting and cleaning pages
    from PDF files and printing their parsed block-level entries.

    Returns:
        None

    Raises:
        MyException: If PDF reading or parsing fails.
    """
    try:
        logging.info("Running PDF parsing pipeline...")

        files: list[Path] = sorted(PDFS_DIRPATH.glob("*.pdf"))
        for file in files:
            pages: list[str] = extract_pdf_text(file=file, start_page=1, end_page=2)
            cleaned_pages: list[str] = [clean_pdf(text=page) for page in pages]
            metadata: DocumentMetadata = enrich_metadata(
                path=file, text=" ".join(cleaned_pages)
            )
            parsed_pdf: list[DocumentSection] = parse_pdf(
                path=file, pages=cleaned_pages, metadata=metadata, start_page=1
            )[:10]

            print_header(file.name)
            for doc in parsed_pdf:
                console.print_json(data=dict(doc))
            print_divider()

        logging.info("PDF parsing pipeline completed.")

    except Exception as e:
        logging.info(f"Failed to run PDF parsing pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
