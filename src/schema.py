"""
Shared domain data schemas and TypedDict definitions for documents, ingestion, and splitting.
"""

from typing import Any, TypedDict

__all__: list[str] = [
    "DocumentMetadata",
    "DocumentSection",
    "HierarchicalRecord",
    "RegistryNode",
    "SplitRecord",
]


class RegistryNode(TypedDict, total=False):
    """
    Representation of a hierarchical registry node (page or paragraph).
    """

    type: str
    text: str
    page_id: str
    metadata: dict[str, Any]


class HierarchicalRecord(TypedDict, total=False):
    """
    Representation of a child sentence split record with parent references.
    """

    id: str
    sentence_id: str
    text: str
    paragraph_id: str
    page_id: str
    metadata: dict[str, Any]


class SplitRecord(TypedDict):
    """
    Representation of a heading-based structural text split.
    """

    id: str
    title: str
    text: str
    metadata: dict[str, Any]


class DocumentSection(TypedDict):
    """
    Structured document section parsed from Markdown or text documents.
    """

    id: str
    text: str
    metadata: dict[str, Any]


class DocumentMetadata(TypedDict):
    """
    Enriched metadata extracted from filesystem properties and content analysis.
    """

    source: str
    title: str
    extension: str
    created_date: str
    modified_date: str
    file_size: int
    character_count: int
    word_count: int
    topics: list[str]
    content_hash: str
