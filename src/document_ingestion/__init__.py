"""
Document Ingestion Module.

This module provides pipelines and utilities for extracting, cleaning,
parsing, and enriching text data from raw documents (PDFs, Markdown, TXT).
"""

from .document_cleaning import clean_document
from .document_parsing import parse_document
from .metadata_enrichment import enrich_metadata, infer_topics
from .pdf_parsing import extract_pdf_text, label_line, parse_pdf

__all__ = [
    "clean_document",
    "enrich_metadata",
    "extract_pdf_text",
    "infer_topics",
    "label_line",
    "parse_document",
    "parse_pdf",
]
