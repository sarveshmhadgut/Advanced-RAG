"""
Data Ingestion Module.

This module provides pipelines and utilities for extracting, cleaning,
parsing, and enriching text data from raw documents (PDFs, Markdown, TXT).
"""

from .document_cleaning import clean_pdf, clean_document
from .document_parsing import parse_document
from .metadata_enrichment import infer_topics, enrich_metadata
from .pdf_parsing import label_line, parse_pdf

__all__ = [
    "clean_document",
    "clean_pdf",
    "enrich_metadata",
    "infer_topics",
    "label_line",
    "parse_document",
    "parse_pdf",
]
