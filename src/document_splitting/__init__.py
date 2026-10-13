"""
Document Splitting Module.

This module provides structural (heading-based), semantic (embedding-similarity-based),
and hierarchical (parent-child page/paragraph/sentence) splitting strategies to split
documents for embedding and retrieval in RAG pipelines.
"""

from .hierarchical_splitting import (
    Record,
    RegistryItem,
    get_hierarchical_splits,
)
from .semantic_splitting import get_semantic_splits
from .structural_splitting import (
    SplitRecord,
    get_structural_splits,
)

__all__: list[str] = [
    "Record",
    "RegistryItem",
    "SplitRecord",
    "get_hierarchical_splits",
    "get_semantic_splits",
    "get_structural_splits",
]
