"""
Reusable utility modules providing centralized filesystem paths, terminal display formatting,
and file I/O operations.
"""

from .display import (
    console,
    get_terminal_width,
    print_divider,
    print_header,
    theme,
)
from .embeddings import (
    get_embedding_model,
    get_similarities_scores,
)
from .io import (
    compute_content_hash,
    generate_uuid,
    load_yaml_file,
    read_text_file,
)
from .paths import (
    CONFIG_DIRPATH,
    DATA_DIRPATH,
    DOCUMENTS_DIRPATH,
    LOGS_DIRPATH,
    PARAMS_FILEPATH,
    PDFS_DIRPATH,
    ROOT,
)
from .text import (
    extract_pdf_text,
    get_nlp,
    get_paragraphs,
    get_sentences,
    get_spacy_sentences,
    remove_stopwords,
)
from .time import get_current_timestamp

__all__: list[str] = [
    "CONFIG_DIRPATH",
    "DATA_DIRPATH",
    "DOCUMENTS_DIRPATH",
    "LOGS_DIRPATH",
    "PARAMS_FILEPATH",
    "PDFS_DIRPATH",
    "ROOT",
    "compute_content_hash",
    "console",
    "extract_pdf_text",
    "generate_uuid",
    "get_current_timestamp",
    "get_embedding_model",
    "get_nlp",
    "get_paragraphs",
    "get_sentences",
    "get_similarities_scores",
    "get_spacy_sentences",
    "get_terminal_width",
    "load_yaml_file",
    "print_divider",
    "print_header",
    "read_text_file",
    "remove_stopwords",
    "theme",
]
