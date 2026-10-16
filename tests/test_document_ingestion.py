"""
Unit tests for the document ingestion package, including document cleaning,
PDF cleaning, metadata enrichment, and structural parsing.
"""

from pathlib import Path

import pytest

import src.document_ingestion as di
from src.document_ingestion.document_cleaning import (
    clean_document,
    normalize_characters,
    normalize_whitespace,
)
from src.document_ingestion.document_parsing import parse_document
from src.document_ingestion.metadata_enrichment import enrich_metadata, infer_topics
from src.document_ingestion.pdf_cleaning import (
    clean_pdf,
    remove_page_artifacts,
    repair_hyphenated_line_breaks,
)
from src.document_ingestion.pdf_parsing import label_line, parse_pdf
from src.exception import DocumentParsingError, ValidationError
from src.schema import DocumentMetadata, DocumentSection

# Document Cleaning Tests


def test_normalize_characters_basic() -> None:
    """
    Test normalization of non-printable control characters, ligatures, and unicode spaces.
    """
    raw_text: str = "Hello\x00 world\x0c!\u00a0This is a \ufb01le with ligatures."
    cleaned: str = normalize_characters(raw_text)

    assert "\x00" not in cleaned
    assert "\x0c" not in cleaned
    assert "file with ligatures" in cleaned


def test_normalize_characters_validation_none_raises() -> None:
    """
    Test that None input raises ValidationError in normalize_characters.
    """
    with pytest.raises(ValidationError):
        normalize_characters(None)  # type: ignore[arg-type]


def test_normalize_whitespace_paragraphs() -> None:
    """
    Test whitespace normalization and paragraph separation.
    """
    raw_text: str = (
        "Paragraph one line one.\n  Paragraph one line two.\n\n\n\nParagraph two."
    )
    cleaned: str = normalize_whitespace(raw_text)

    assert "\n\n\n" not in cleaned
    paragraphs: list[str] = cleaned.split("\n\n")
    assert len(paragraphs) == 2


def test_clean_document_pipeline() -> None:
    """
    Test complete clean_document pipeline preserves markdown headings and cleans text.
    """
    raw_doc: str = "# Main Heading\n\nSome body text.\n\n\n## Subheading\n\nMore text."
    cleaned: str = clean_document(raw_doc)

    assert "# Main Heading" in cleaned
    assert "## Subheading" in cleaned
    assert "Some body text." in cleaned


# PDF Cleaning Tests


def test_repair_hyphenated_line_breaks() -> None:
    """
    Test repairing words split across lines by hyphens.
    """
    raw_text: str = "The trans-\nformer architecture revolu-\ntionized NLP."
    repaired: str = repair_hyphenated_line_breaks(raw_text)

    assert "transformer" in repaired
    assert "revolutionized" in repaired


def test_remove_page_artifacts() -> None:
    """
    Test removal of dot leaders and standalone page number artifacts.
    """
    raw_text: str = (
        "Chapter 1 . . . . . . . . . . . . . 15\n\nPage 42\n\nActual content paragraph."
    )
    cleaned: str = remove_page_artifacts(raw_text)

    assert ". . . ." not in cleaned
    assert "Actual content paragraph." in cleaned


def test_clean_pdf_pipeline() -> None:
    """
    Test end-to-end PDF cleaning with hyphen repair, artifact removal, and character normalization.
    """
    raw_pdf_text: str = "Document Header\n\nAdvanced artifi-\ncial intelligence systems.\n\n123\n\nNext paragraph."
    cleaned: str = clean_pdf(raw_pdf_text)

    assert "artificial" in cleaned
    assert "Next paragraph." in cleaned


# Metadata Enrichment Tests


def test_infer_topics_matching() -> None:
    """
    Test topic inference against text content.
    """
    text: str = "Deep learning, transformer models, and artificial intelligence in modern pipelines."
    topics: list[str] = infer_topics(text)

    assert isinstance(topics, list)


def test_infer_topics_validation_none_raises() -> None:
    """
    Test that None input raises ValidationError in infer_topics.
    """
    with pytest.raises(ValidationError):
        infer_topics(None)  # type: ignore[arg-type]


def test_enrich_metadata_valid_file(tmp_path: Path) -> None:
    """
    Test metadata enrichment on a valid filesystem path.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
    """
    sample_file: Path = tmp_path / "sample_test_doc.md"
    sample_content: str = "# Sample Document\nThis covers machine learning topics."
    sample_file.write_text(sample_content, encoding="utf-8")

    metadata: DocumentMetadata = enrich_metadata(path=sample_file, text=sample_content)

    assert metadata["source"] == str(sample_file)
    assert metadata["title"] == "Sample Test Doc"
    assert metadata["extension"] == ".md"
    assert metadata["character_count"] == len(sample_content)
    assert metadata["word_count"] == len(sample_content.split())
    assert isinstance(metadata["content_hash"], str)
    assert len(metadata["content_hash"]) == 64  # SHA-256 hex length


def test_enrich_metadata_validation_missing_file(tmp_path: Path) -> None:
    """
    Test that non-existent file raises DocumentParsingError in enrich_metadata.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
    """
    non_existent: Path = tmp_path / "non_existent.md"
    with pytest.raises(DocumentParsingError):
        enrich_metadata(path=non_existent, text="content")


# Document Parsing Tests


def test_parse_document_markdown(
    tmp_path: Path,
    sample_document_metadata: DocumentMetadata,
) -> None:
    """
    Test structural markdown parsing into DocumentSection entries with heading breadcrumbs.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
        sample_document_metadata (DocumentMetadata): Fixture providing metadata.
    """
    md_file: Path = tmp_path / "test_doc.md"
    md_file.write_text("dummy", encoding="utf-8")

    content: str = "# System Architecture\n\nTop-level architectural description.\n\n## Vector Database\n\nStores high-dimensional embeddings."

    sections: list[DocumentSection] = parse_document(
        path=md_file,
        text=content,
        metadata=sample_document_metadata,
    )

    assert len(sections) == 2
    titles: list[str] = [
        str(sec.get("metadata", {}).get("section_metadata", {}).get("title", ""))
        for sec in sections
    ]
    assert "System Architecture" in titles[0]
    assert "System Architecture > Vector Database" in titles[1]


# PDF Parsing Tests


def test_label_line_heuristics() -> None:
    """
    Test heuristic line classification for headers, tables, and paragraphs.
    """
    header_line: str = "SECTION TITLE IN ALL CAPITAL LETTERS FOR TESTING PURPOSES ONLY"
    table_line: str = "Column A    |    Column B    |    Column C"
    paragraph_line: str = "This is a regular descriptive paragraph line."

    assert label_line(header_line) == "header"
    assert label_line(table_line) == "table"
    assert label_line(paragraph_line) == "paragraph"


def test_label_line_validation_none_raises() -> None:
    """
    Test that None input raises ValidationError in label_line.
    """
    with pytest.raises(ValidationError):
        label_line(None)  # type: ignore[arg-type]


def test_parse_pdf_pages(
    tmp_path: Path,
    sample_document_metadata: DocumentMetadata,
) -> None:
    """
    Test PDF block parsing across multiple pages.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
        sample_document_metadata (DocumentMetadata): Fixture providing metadata.
    """
    pdf_file: Path = tmp_path / "sample.pdf"
    pdf_file.write_text("dummy", encoding="utf-8")

    pages: list[str] = [
        "First page line 1.\n\nFirst page line 2.",
        "Second page line 1.",
    ]

    sections: list[DocumentSection] = parse_pdf(
        path=pdf_file,
        pages=pages,
        metadata=sample_document_metadata,
        start_page=1,
    )

    assert len(sections) > 0
    for sec in sections:
        assert isinstance(sec["id"], str)
        assert isinstance(sec["text"], str)
        assert "section_metadata" in sec["metadata"]


# Package Exports Tests


def test_document_ingestion_package_exports() -> None:
    """
    Test that src.document_ingestion exports all required symbols in __all__.
    """
    for symbol in di.__all__:
        assert hasattr(di, symbol)
