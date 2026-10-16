"""
Pytest fixtures and test configuration for document splitting and ingestion test suites.
"""

import pytest

from src.schema import DocumentMetadata, DocumentSection


@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    """
    Provide sample DocumentMetadata payload for unit tests.

    Returns:
        DocumentMetadata: A fully-populated mock document metadata dictionary.
    """
    return {
        "source": "tests/data/sample.pdf",
        "title": "Sample AI Engineering Document",
        "extension": ".pdf",
        "created_date": "2026-01-01 10:00:00",
        "modified_date": "2026-01-02 12:00:00",
        "file_size": 2048,
        "character_count": 500,
        "word_count": 80,
        "topics": ["Artificial Intelligence", "RAG"],
        "content_hash": "a1b2c3d4e5f67890123456789abcdef0",
    }


@pytest.fixture
def sample_document_sections(
    sample_document_metadata: DocumentMetadata,
) -> list[DocumentSection]:
    """
    Provide a list of parsed DocumentSection dictionaries for unit tests.

    Args:
        sample_document_metadata (DocumentMetadata): Fixture providing metadata.

    Returns:
        list[DocumentSection]: A list of structured document sections.
    """
    return [
        {
            "id": "section-uuid-1",
            "text": (
                "Artificial intelligence transforms modern computing systems. "
                "Retrieval-Augmented Generation enhances generative model accuracy. "
                "Vector databases index dense semantic embeddings efficiently. "
                "Hierarchical chunking preserves contextual document hierarchy."
            ),
            "metadata": {
                "title": "Introduction to RAG",
                "section_metadata": {
                    "section_id": "section-uuid-1",
                    "title": "Introduction to RAG",
                    "page_number": 1,
                },
                "document_metadata": dict(sample_document_metadata),
            },
        },
        {
            "id": "section-uuid-2",
            "text": (
                "Sentence window retrieval attaches neighboring sentences to queries. "
                "This expands downstream retrieval context for language models."
            ),
            "metadata": {
                "title": "Sentence Window Retrieval",
                "section_metadata": {
                    "section_id": "section-uuid-2",
                    "title": "Sentence Window Retrieval",
                    "page_number": 2,
                },
                "document_metadata": dict(sample_document_metadata),
            },
        },
    ]


@pytest.fixture
def sample_pages() -> list[str]:
    """
    Provide sample multi-paragraph document pages for hierarchical splitting tests.

    Returns:
        list[str]: A list of page text strings separated by paragraphs.
    """
    return [
        (
            "Page 1 Paragraph 1 contains introductory content.\n\n"
            "Page 1 Paragraph 2 discusses advanced retrieval architectures."
        ),
        (
            "Page 2 Paragraph 1 covers evaluation metrics.\n\n"
            "Page 2 Paragraph 2 concludes the overview."
        ),
    ]
