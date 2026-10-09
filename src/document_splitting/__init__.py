"""
Document Splitting Module.

This module provides structural (heading-based) and semantic (embedding-similarity-based)
splitting strategies to chunk documents for embedding and retrieval in RAG pipelines.
"""

from .semantic_splitting import (
    get_semantic_splits,
    get_sentences,
    get_similarities_scores,
    remove_stopwords,
)
from .structural_splitting import get_structural_splits, parse_sections

__all__: list[str] = [
    "get_semantic_splits",
    "get_sentences",
    "get_similarities_scores",
    "get_structural_splits",
    "parse_sections",
    "remove_stopwords",
]
