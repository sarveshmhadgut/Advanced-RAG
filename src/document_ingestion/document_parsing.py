"""
Provides functionality to parse markdown-style documents into structured,
hierarchical sections based on heading markers.
"""

import re
import sys
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.document_ingestion.document_cleaning import clean_document
from src.document_ingestion.metadata_enrichment import enrich_metadata
from src.exception import DocumentParsingError, MyException, ValidationError
from src.logger import logging
from src.schema import DocumentMetadata, DocumentSection
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
        .get("document_ingestion", {})
        .get("document_parsing", {})
    )
    FILE_NAMES: list[str] = list(PARAMS.get("file_names", []))
except Exception as e:
    logging.info(f"Failed to initialize document parsing module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = ["DocumentSection", "parse_document"]


def parse_document(
    path: Path,
    text: str,
    metadata: DocumentMetadata,
) -> list[DocumentSection]:
    """
    Parses a markdown-style document into structured sections by splitting
    on heading markers (e.g., #, ##, ###) and building a hierarchical title.

    Args:
        path (Path): The file path of the document being parsed.
        text (str): The full text content of the document.
        metadata (DocumentMetadata): Enriched document metadata to embed.

    Returns:
        list[DocumentSection]: A list of section dictionaries, each containing:
            - "id" (str): Deterministic UUID derived from path, title, and content.
            - "text" (str): The body content under that heading.
            - "metadata" (dict[str, Any]): Section and document metadata.
            Returns an empty list if the input text is empty.

    Raises:
        ValidationError: If path or text are invalid.
        DocumentParsingError: If document parsing fails.
    """
    try:
        logging.info(f"Parsing document: {path.name if path else 'unknown'}...")

        if not path:
            raise ValidationError("path must be provided", sys)

        if text is None:
            raise ValidationError("text cannot be None", sys)

        if not text:
            return []

        sections: list[DocumentSection] = []
        breadcrumbs: list[str] = []
        body: list[str] = []

        def flush() -> None:
            body_content: str = "\n".join(body).strip()
            body_content = re.sub(r"\n{3,}", "\n\n", body_content)

            if body_content:
                title: str = " > ".join(breadcrumbs) if breadcrumbs else "Root"
                sections.append(
                    {
                        "id": generate_uuid(
                            name=f"{path}_{title}_{body_content}", as_hex=True
                        ),
                        "text": body_content,
                        "metadata": {
                            "section_metadata": {
                                "title": title,
                                "character_count": len(body_content),
                                "word_count": len(body_content.split()),
                            },
                            "document_metadata": metadata or {},
                        },
                    }
                )
            body.clear()

        for line in text.splitlines():
            match = re.match(r"^\s*(#+)\s+(.*?)\s*$", line)
            if match:
                flush()
                sub: int = len(match.group(1))
                breadcrumb: str = match.group(2).strip()
                breadcrumbs = breadcrumbs[: sub - 1] + [breadcrumb]
            else:
                body.append(line)

        flush()
        logging.info(f"Parsed {len(sections)} sections from document.")
        return sections

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to parse document: {e}")
        raise DocumentParsingError(e, sys) from e


def main() -> None:
    """
    Demonstrates the document parsing pipeline on sample documents.

    Returns:
        None

    Raises:
        MyException: If the document parsing pipeline fails.
    """
    try:
        logging.info("Running document parsing pipeline...")

        files: list[Path] = [DOCUMENTS_DIRPATH / file_name for file_name in FILE_NAMES]

        for file in files:
            if not file.exists():
                logging.info(f"File not found: {file}")
                continue

            text: str = file.read_text(encoding="utf-8")
            cleaned_text: str = clean_document(text=text)
            metadata: DocumentMetadata = enrich_metadata(path=file, text=cleaned_text)
            parsed_doc: list[DocumentSection] = parse_document(
                path=file, text=cleaned_text, metadata=metadata
            )

            print_header(file.name)
            for section in parsed_doc:
                console.print_json(data=dict(section))
            print_divider()

        logging.info("Document parsing pipeline completed.")

    except Exception as e:
        logging.info(f"Failed to run document parsing pipeline: {e}")
        raise MyException(e, sys) from e


if __name__ == "__main__":
    main()
