"""
Document Ingestion Module.

This module provides pipelines and utilities for extracting, cleaning,
parsing, and enriching text data from raw documents (PDFs, Markdown, TXT).
"""

from src.utils import extract_pdf_text

from .document_cleaning import clean_document
from .document_parsing import DocumentSection, parse_document
from .metadata_enrichment import DocumentMetadata, enrich_metadata
from .pdf_cleaning import clean_pdf
from .pdf_parsing import parse_pdf

__all__: list[str] = [
    "DocumentMetadata",
    "DocumentSection",
    "clean_document",
    "clean_pdf",
    "enrich_metadata",
    "extract_pdf_text",
    "parse_document",
    "parse_pdf",
]
