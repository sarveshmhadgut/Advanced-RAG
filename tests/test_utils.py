"""
Unit tests for the centralized utils package (I/O, text processing, time, and paths).
"""

import re
from pathlib import Path

import pytest

from src.exception import MyException
from src.utils.display import get_terminal_width
from src.utils.io import (
    compute_content_hash,
    generate_uuid,
    load_yaml_file,
    read_text_file,
)
from src.utils.paths import (
    CONFIG_DIRPATH,
    DATA_DIRPATH,
    DOCUMENTS_DIRPATH,
    LOGS_DIRPATH,
    PARAMS_FILEPATH,
    PDFS_DIRPATH,
    ROOT,
)
from src.utils.text import (
    get_nlp,
    get_paragraphs,
    get_sentences,
    remove_stopwords,
)
from src.utils.time import get_current_timestamp

# I/O Utilities Tests


def test_load_yaml_file_valid(tmp_path: Path) -> None:
    """
    Test loading a valid YAML file into a dictionary.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
    """
    yaml_file: Path = tmp_path / "test_config.yml"
    yaml_file.write_text("key1: value1\nnested:\n  item: 123\n", encoding="utf-8")

    data: dict[str, object] = load_yaml_file(yaml_file)
    assert data["key1"] == "value1"
    assert isinstance(data["nested"], dict)


def test_load_yaml_file_missing_raises(tmp_path: Path) -> None:
    """
    Test that a non-existent YAML path raises an Exception (FileNotFoundError wrapped).

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
    """
    with pytest.raises(MyException):
        load_yaml_file(tmp_path / "does_not_exist.yml")


def test_read_text_file(tmp_path: Path) -> None:
    """
    Test reading text content from a valid file.

    Args:
        tmp_path (Path): Pytest temporary directory fixture.
    """
    txt_file: Path = tmp_path / "hello.txt"
    txt_file.write_text("Hello Advanced RAG!", encoding="utf-8")

    content: str = read_text_file(txt_file)
    assert content == "Hello Advanced RAG!"


def test_compute_content_hash() -> None:
    """
    Test deterministic content hashing.
    """
    text: str = "Deterministic text content for hash verification."
    hash1: str = compute_content_hash(text)
    hash2: str = compute_content_hash(text)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256


def test_generate_uuid_deterministic() -> None:
    """
    Test deterministic UUID5 generation from names.
    """
    id1: str = generate_uuid(name="test_name_1")
    id2: str = generate_uuid(name="test_name_1")
    id3: str = generate_uuid(name="test_name_2")

    assert id1 == id2
    assert id1 != id3


def test_generate_uuid_as_hex() -> None:
    """
    Test that as_hex=True returns a 32-character hexadecimal string without hyphens.
    """
    hex_id: str = generate_uuid(name="test_name_hex", as_hex=True)
    assert "-" not in hex_id
    assert len(hex_id) == 32


# Text Processing Utilities Tests


def test_get_paragraphs() -> None:
    """
    Test paragraph segmentation separated by blank lines.
    """
    text: str = "Paragraph 1 line.\n\nParagraph 2 line.\n\n\nParagraph 3 line."
    paragraphs: list[str] = get_paragraphs(text)

    assert len(paragraphs) == 3
    assert paragraphs[0] == "Paragraph 1 line."
    assert paragraphs[1] == "Paragraph 2 line."
    assert paragraphs[2] == "Paragraph 3 line."


def test_get_paragraphs_empty() -> None:
    """
    Test that empty or whitespace strings return an empty list of paragraphs.
    """
    assert get_paragraphs("") == []
    assert get_paragraphs("    \n\n   ") == []


def test_get_sentences_spacy() -> None:
    """
    Test sentence segmentation using the spaCy pipeline.
    """
    text: str = "First sentence here. Second sentence follows. Third sentence finishes."
    sentences: list[str] = get_sentences(text)

    assert len(sentences) == 3
    assert sentences[0] == "First sentence here."
    assert sentences[1] == "Second sentence follows."
    assert sentences[2] == "Third sentence finishes."


def test_remove_stopwords() -> None:
    """
    Test stopword removal while ensuring negation words ('not') are preserved.
    """
    text: str = "This model is not performing as expected."
    cleaned: str = remove_stopwords(text)

    assert "not" in cleaned.split()
    assert "is" not in cleaned.split()


def test_get_nlp_cached() -> None:
    """
    Test that the spaCy model loader returns a valid Language instance and is cached.
    """
    nlp1 = get_nlp()
    nlp2 = get_nlp()
    assert nlp1 is nlp2


# Time & Paths Utilities Tests


def test_get_current_timestamp() -> None:
    """
    Test that the timestamp matches the expected DD-Mon-YY_HH-MM-SS format.
    """
    ts: str = get_current_timestamp()
    pattern: str = r"^\d{2}-[A-Za-z]{3}-\d{2}_\d{2}-\d{2}-\d{2}$"
    assert re.match(pattern, ts) is not None


def test_paths_are_path_instances() -> None:
    """
    Test that all centralized path constants are Path instances.
    """
    for path_obj in [
        ROOT,
        CONFIG_DIRPATH,
        DATA_DIRPATH,
        DOCUMENTS_DIRPATH,
        LOGS_DIRPATH,
        PARAMS_FILEPATH,
        PDFS_DIRPATH,
    ]:
        assert isinstance(path_obj, Path)


def test_get_terminal_width() -> None:
    """
    Test that get_terminal_width returns a positive integer.
    """
    width: int = get_terminal_width()
    assert isinstance(width, int)
    assert width > 0
