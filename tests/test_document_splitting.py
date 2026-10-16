"""
Unit tests for the document splitting package, covering structural, semantic,
hierarchical, and sentence-window splitting strategies.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import src.document_splitting as ds
from src.document_splitting.hierarchical_splitting import (
    Record,
    RegistryItem,
    get_hierarchical_splits,
)
from src.document_splitting.semantic_splitting import get_semantic_splits
from src.document_splitting.sentence_window_splitting import (
    get_sentence_window_splits,
)
from src.document_splitting.structural_splitting import get_structural_splits
from src.exception import ValidationError
from src.schema import DocumentMetadata, DocumentSection, SplitRecord

# Structural Splitting Tests


def test_get_structural_splits_basic(
    sample_document_sections: list[DocumentSection],
) -> None:
    """
    Test basic structural splitting when word count is within max_split_size.

    Args:
        sample_document_sections (list[DocumentSection]): Fixture providing test sections.
    """
    splits: list[SplitRecord] = get_structural_splits(
        document=sample_document_sections,
        max_split_size=50,
        overlap=10,
    )

    assert len(splits) == 2
    for split in splits:
        assert isinstance(split["id"], str)
        assert isinstance(split["title"], str)
        assert isinstance(split["text"], str)
        assert "metadata" in split

        metadata: dict[str, Any] = split["metadata"]
        assert "split_metadata" in metadata
        assert "section_metadata" in metadata
        assert "document_metadata" in metadata


def test_get_structural_splits_sliding_window() -> None:
    """
    Test that large sections are divided into multiple overlapping chunks.
    """
    large_text: str = " ".join([f"word{i}" for i in range(100)])
    document: list[DocumentSection] = [
        {
            "id": "large-sec",
            "text": large_text,
            "metadata": {
                "title": "Large Section",
                "section_metadata": {"title": "Large Section"},
                "document_metadata": {},
            },
        }
    ]

    splits: list[SplitRecord] = get_structural_splits(
        document=document,
        max_split_size=30,
        overlap=10,
    )

    # 100 words, chunk size 30, step 20 -> chunks start at 0, 20, 40, 60, 80 (5 chunks)
    assert len(splits) == 5
    assert splits[0]["title"] == "Large Section"

    # Check overlap between consecutive splits
    first_split_words: list[str] = splits[0]["text"].split()
    second_split_words: list[str] = splits[1]["text"].split()
    assert first_split_words[20:30] == second_split_words[0:10]


def test_get_structural_splits_empty_document() -> None:
    """
    Test that an empty document list returns an empty list.
    """
    splits: list[SplitRecord] = get_structural_splits(document=[])
    assert splits == []


def test_get_structural_splits_empty_section_text() -> None:
    """
    Test that sections containing only empty or whitespace strings are skipped.
    """
    document: list[DocumentSection] = [
        {
            "id": "empty-sec",
            "text": "   \n\t  ",
            "metadata": {"title": "Empty", "section_metadata": {}},
        }
    ]

    splits: list[SplitRecord] = get_structural_splits(document=document)
    assert splits == []


def test_get_structural_splits_validation_none_document() -> None:
    """
    Test that None as document argument raises a ValidationError.
    """
    with pytest.raises(ValidationError):
        get_structural_splits(document=None)  # type: ignore[arg-type]


def test_get_structural_splits_validation_non_list() -> None:
    """
    Test that a non-list document argument raises a ValidationError.
    """
    with pytest.raises(ValidationError):
        get_structural_splits(document="invalid string")  # type: ignore[arg-type]


def test_get_structural_splits_validation_invalid_max_split_size(
    sample_document_sections: list[DocumentSection],
) -> None:
    """
    Test that non-positive max_split_size raises a ValidationError.

    Args:
        sample_document_sections (list[DocumentSection]): Fixture providing test sections.
    """
    with pytest.raises(ValidationError):
        get_structural_splits(
            document=sample_document_sections,
            max_split_size=0,
        )


def test_get_structural_splits_validation_invalid_overlap(
    sample_document_sections: list[DocumentSection],
) -> None:
    """
    Test that negative overlap or overlap >= max_split_size raises a ValidationError.

    Args:
        sample_document_sections (list[DocumentSection]): Fixture providing test sections.
    """
    with pytest.raises(ValidationError):
        get_structural_splits(
            document=sample_document_sections,
            max_split_size=20,
            overlap=-1,
        )

    with pytest.raises(ValidationError):
        get_structural_splits(
            document=sample_document_sections,
            max_split_size=20,
            overlap=20,
        )


# Semantic Splitting Tests


def test_get_semantic_splits_empty_input() -> None:
    """
    Test that an empty string or empty section list returns an empty list.
    """
    assert get_semantic_splits(document="") == []
    assert get_semantic_splits(document=[]) == []


def test_get_semantic_splits_single_sentence() -> None:
    """
    Test that a single-sentence document immediately returns one split without embedding calls.
    """
    splits: list[SplitRecord] = get_semantic_splits(
        document="Single self-contained sentence for testing."
    )

    assert len(splits) == 1
    assert splits[0]["text"] == "Single self-contained sentence for testing."
    assert "metadata" in splits[0]


def test_get_semantic_splits_similarity_chunking(
    sample_document_metadata: DocumentMetadata,
) -> None:
    """
    Test semantic chunking boundary decisions using mocked similarity scores.

    Args:
        sample_document_metadata (DocumentMetadata): Fixture providing metadata.
    """
    text: str = "Topic A introduction sentence. Topic A elaboration sentence. Topic B completely different subject sentence."

    mock_similarities: list[float] = [0.95, 0.30]

    with patch(
        "src.document_splitting.semantic_splitting.get_similarities_scores",
        return_value=mock_similarities,
    ):
        mock_model: MagicMock = MagicMock()
        splits: list[SplitRecord] = get_semantic_splits(
            document=text,
            metadata=sample_document_metadata,
            similarity_threshold=0.75,
            max_split_size=500,
            model=mock_model,
        )

        assert len(splits) == 2
        assert "Topic A introduction sentence." in splits[0]["text"]
        assert "Topic A elaboration sentence." in splits[0]["text"]
        assert "Topic B completely different subject sentence." in splits[1]["text"]


def test_get_semantic_splits_validation_none_document() -> None:
    """
    Test that None document argument raises a ValidationError.
    """
    with pytest.raises(ValidationError):
        get_semantic_splits(document=None)  # type: ignore[arg-type]


def test_get_semantic_splits_validation_invalid_similarity_threshold() -> None:
    """
    Test that similarity_threshold outside [0.0, 1.0] raises a ValidationError.
    """
    with pytest.raises(ValidationError):
        get_semantic_splits(
            document="Valid sentence.",
            similarity_threshold=-0.1,
        )

    with pytest.raises(ValidationError):
        get_semantic_splits(
            document="Valid sentence.",
            similarity_threshold=1.5,
        )


def test_get_semantic_splits_validation_invalid_max_split_size() -> None:
    """
    Test that non-positive max_split_size raises a ValidationError.
    """
    with pytest.raises(ValidationError):
        get_semantic_splits(
            document="Valid sentence.",
            max_split_size=0,
        )


# Hierarchical Splitting Tests


def test_get_hierarchical_splits_basic(
    sample_pages: list[str],
    sample_document_metadata: DocumentMetadata,
) -> None:
    """
    Test that hierarchical splitting produces structured registries and parent-linked splits.

    Args:
        sample_pages (list[str]): Fixture providing document page text.
        sample_document_metadata (DocumentMetadata): Fixture providing metadata.
    """
    registry: dict[str, RegistryItem]
    splits: list[Record]
    registry, splits = get_hierarchical_splits(
        pages=sample_pages,
        metadata=sample_document_metadata,
        start_page=1,
    )

    assert len(registry) > 0
    assert len(splits) > 0

    node_types: set[str] = {node.get("type", "") for node in registry.values()}
    assert "page" in node_types
    assert "paragraph" in node_types

    for record in splits:
        assert isinstance(record["id"], str)
        assert isinstance(record["text"], str)

        metadata: dict[str, Any] = record["metadata"]
        assert "split_metadata" in metadata
        split_meta: dict[str, Any] = metadata["split_metadata"]

        paragraph_id: str = split_meta["paragraph_id"]
        page_id: str = split_meta["page_id"]

        assert paragraph_id in registry
        assert page_id in registry
        assert registry[paragraph_id]["type"] == "paragraph"
        assert registry[page_id]["type"] == "page"


def test_get_hierarchical_splits_empty_pages() -> None:
    """
    Test that an empty list of pages returns an empty registry and empty splits.
    """
    registry: dict[str, RegistryItem]
    splits: list[Record]
    registry, splits = get_hierarchical_splits(pages=[])
    assert registry == {}
    assert splits == []


def test_get_hierarchical_splits_custom_start_page(
    sample_pages: list[str],
) -> None:
    """
    Test that custom start_page correctly offsets the page identifiers in the registry.

    Args:
        sample_pages (list[str]): Fixture providing document page text.
    """
    registry: dict[str, RegistryItem]
    splits: list[Record]
    registry, splits = get_hierarchical_splits(
        pages=sample_pages,
        start_page=50,
    )

    page_nodes: list[RegistryItem] = [
        node for node in registry.values() if node.get("type") == "page"
    ]
    assert len(page_nodes) == len(sample_pages)


def test_get_hierarchical_splits_validation_none_pages() -> None:
    """
    Test that None pages argument raises a ValidationError.
    """
    with pytest.raises(ValidationError):
        get_hierarchical_splits(pages=None)  # type: ignore[arg-type]


def test_get_hierarchical_splits_validation_none_page_item() -> None:
    """
    Test that a page list containing None raises a ValidationError.
    """
    with pytest.raises(ValidationError):
        get_hierarchical_splits(pages=["Valid page", None])  # type: ignore[list-item]


# Sentence Window Splitting Tests


def test_get_sentence_window_splits_structure(
    sample_document_sections: list[DocumentSection],
    sample_document_metadata: DocumentMetadata,
) -> None:
    """
    Test that sentence-window splits contain all required keys and valid types.

    Args:
        sample_document_sections (list[DocumentSection]): Fixture providing test sections.
        sample_document_metadata (DocumentMetadata): Fixture providing metadata.
    """
    splits: list[SplitRecord] = get_sentence_window_splits(
        document=sample_document_sections,
        metadata=sample_document_metadata,
        window=1,
    )

    assert len(splits) > 0
    for split in splits:
        assert isinstance(split["id"], str)
        assert len(split["id"]) > 0
        assert isinstance(split["text"], str)
        assert len(split["text"]) > 0
        assert isinstance(split["window_text"], str)
        assert len(split["window_text"]) > 0
        assert split["text"] in split["window_text"]

        metadata: dict[str, Any] = split["metadata"]
        assert "split_metadata" in metadata
        assert "section_metadata" in metadata
        assert "document_metadata" in metadata

        split_meta: dict[str, Any] = metadata["split_metadata"]
        assert split_meta["text_character_count"] == len(split["text"])
        assert split_meta["text_word_count"] == len(split["text"].split())
        assert split_meta["window_character_count"] == len(split["window_text"])
        assert split_meta["window_word_count"] == len(split["window_text"].split())


def test_get_sentence_window_splits_window_zero(
    sample_document_sections: list[DocumentSection],
) -> None:
    """
    Test that a window size of 0 produces window_text identical to the focus sentence.

    Args:
        sample_document_sections (list[DocumentSection]): Fixture providing test sections.
    """
    splits: list[SplitRecord] = get_sentence_window_splits(
        document=sample_document_sections,
        window=0,
    )

    for split in splits:
        assert split["text"] == split["window_text"]


def test_get_sentence_window_splits_window_expansion(
    sample_document_sections: list[DocumentSection],
) -> None:
    """
    Test that increasing window sizes expand the contextual window_text.

    Args:
        sample_document_sections (list[DocumentSection]): Fixture providing test sections.
    """
    single_section: list[DocumentSection] = [sample_document_sections[0]]

    splits_w0: list[SplitRecord] = get_sentence_window_splits(
        document=single_section, window=0
    )
    splits_w1: list[SplitRecord] = get_sentence_window_splits(
        document=single_section, window=1
    )
    splits_w2: list[SplitRecord] = get_sentence_window_splits(
        document=single_section, window=2
    )

    assert len(splits_w0) == len(splits_w1) == len(splits_w2)

    middle_idx: int = 1
    w0_text: str = splits_w0[middle_idx]["window_text"] or ""
    w1_text: str = splits_w1[middle_idx]["window_text"] or ""
    w2_text: str = splits_w2[middle_idx]["window_text"] or ""

    assert len(w0_text) < len(w1_text) <= len(w2_text)


def test_get_sentence_window_splits_boundaries() -> None:
    """
    Test boundary handling for first sentence, last sentence, and single sentence sections.
    """
    single_sentence_doc: list[DocumentSection] = [
        {
            "id": "sec-single",
            "text": "This is a single self-contained sentence.",
            "metadata": {"section_metadata": {}, "document_metadata": {}},
        }
    ]

    splits: list[SplitRecord] = get_sentence_window_splits(
        document=single_sentence_doc,
        window=2,
    )

    assert len(splits) == 1
    assert splits[0]["text"] == "This is a single self-contained sentence."
    assert splits[0]["window_text"] == "This is a single self-contained sentence."


def test_get_sentence_window_splits_empty_document() -> None:
    """
    Test that an empty document section list returns an empty list of splits.
    """
    splits: list[SplitRecord] = get_sentence_window_splits(document=[])
    assert splits == []


def test_get_sentence_window_splits_none_document_raises() -> None:
    """
    Test that passing None as the document raises a ValidationError.
    """
    with pytest.raises(ValidationError):
        get_sentence_window_splits(document=None)  # type: ignore[arg-type]


def test_get_sentence_window_splits_negative_window_raises(
    sample_document_sections: list[DocumentSection],
) -> None:
    """
    Test that a negative window value raises a ValidationError.

    Args:
        sample_document_sections (list[DocumentSection]): Fixture providing test sections.
    """
    with pytest.raises(ValidationError):
        get_sentence_window_splits(
            document=sample_document_sections,
            window=-1,
        )


# Package Exports Tests


def test_document_splitting_all_exports() -> None:
    """
    Test that __all__ in src.document_splitting contains expected public APIs.
    """
    expected_exports: list[str] = [
        "Record",
        "RegistryItem",
        "SplitRecord",
        "get_hierarchical_splits",
        "get_semantic_splits",
        "get_sentence_window_splits",
        "get_structural_splits",
    ]

    for export_name in expected_exports:
        assert export_name in ds.__all__
        assert hasattr(ds, export_name)
