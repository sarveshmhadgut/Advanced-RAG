"""
Provides semantic document splitting functionality using spaCy sentence segmentation
and Google Generative AI embeddings similarity thresholds.

Includes utilities for stopword filtering with negation retention, sentence
segmentation, pairwise similarity scoring, and LangSmith tracing observability.
"""

import shutil
import sys
from pathlib import Path

import numpy as np
import spacy
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langsmith import traceable
from spacy.tokens import Doc
from termcolor import colored

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import console
from src.document_ingestion.document_cleaning import clean_document
from src.document_ingestion.pdf_parsing import extract_pdf_text
from src.exception import MyException
from src.logger import logging

try:
    load_dotenv()

    WIDTH: int = shutil.get_terminal_size().columns
    PAGE_NO: int = 13
    PDFS_DIRPATH: Path = ROOT / "data" / "input" / "pdfs"
    DOCUMENTS_DIRPATH: Path = ROOT / "data" / "input" / "documents"

    nlp: spacy.Language = spacy.load("en_core_web_sm")
    nlp.Defaults.stop_words.discard("not")

    EMBEDDING_MODEL: GoogleGenerativeAIEmbeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        output_dimensionality=384,
    )
except Exception as e:
    logging.error(f"Failed to initialize semantic splitting module dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = [
    "EMBEDDING_MODEL",
    "get_semantic_splits",
    "get_sentences",
    "get_similarities_scores",
    "remove_stopwords",
]


@traceable(name="remove_stopwords")
def remove_stopwords(text: str) -> str:
    """
    Remove English stopwords from text while retaining negation words like 'not'.

    Args:
        text (str): The input text to process.

    Returns:
        str: Text with stopwords removed. Returns an empty string if input is empty.

    Raises:
        MyException: If text is None or stopword removal fails.
    """
    try:
        logging.info("Removing stopwords from text...")

        if text is None:
            raise ValueError("text cannot be None")

        if not text.strip():
            logging.info("Input text is empty; returning empty string.")
            return ""

        doc: Doc = nlp(text=text)
        doc.vocab["not"].is_stop = False

        filtered_text: str = " ".join([token.text for token in doc if not token.is_stop])
        logging.info("Stopwords removed successfully.")
        return filtered_text

    except Exception as exc:
        logging.error(f"Failed to remove stopwords: {exc}")
        raise MyException(exc, sys) from exc


@traceable(name="get_sentences")
def get_sentences(text: str) -> list[str]:
    """
    Segment input text into individual sentences using spaCy sentence boundary detection.

    Args:
        text (str): The input text to segment into sentences.

    Returns:
        list[str]: A list of non-empty sentence strings. Returns an empty list if text is empty.

    Raises:
        MyException: If text is None or sentence segmentation fails.
    """
    try:
        logging.info("Segmenting text into sentences...")

        if text is None:
            raise ValueError("text cannot be None")

        if not text.strip():
            logging.info("Input text is empty; returning empty sentence list.")
            return []

        doc: Doc = nlp(text=text)
        sentences: list[str] = [sentence.text.strip() for sentence in doc.sents if sentence.text.strip()]

        logging.info(f"Segmented {len(sentences)} sentences successfully.")
        return sentences

    except Exception as exc:
        logging.error(f"Failed to segment sentences: {exc}")
        raise MyException(exc, sys) from exc


@traceable(name="get_similarities_scores")
def get_similarities_scores(
    sentences: list[str],
    model: GoogleGenerativeAIEmbeddings,
) -> list[float]:
    """
    Calculate consecutive pair-wise cosine similarity scores across a list of sentences.

    Args:
        sentences (list[str]): List of sentences to compare consecutively.
        model (GoogleGenerativeAIEmbeddings): Embedding model instance used to generate vectors.

    Returns:
        list[float]: A list of float cosine similarity scores between consecutive pairs.
            Returns an empty list if fewer than 2 sentences are provided.

    Raises:
        MyException: If inputs are invalid or similarity score computation fails.
    """
    try:
        logging.info(f"Calculating similarity scores for {len(sentences) if sentences is not None else 0} sentences...")

        if sentences is None:
            raise ValueError("sentences cannot be None")

        if model is None:
            raise ValueError("model cannot be None")

        if len(sentences) < 2:
            logging.info(f"Fewer than 2 sentences provided ({len(sentences)}); returning empty similarity list.")
            return []

        raw_embeddings: list[list[float]] = model.embed_documents(sentences)
        embeddings: np.ndarray = np.asarray(raw_embeddings, dtype=np.float32)

        norms: np.ndarray = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings: np.ndarray = embeddings / np.maximum(norms, 1e-12)

        similarities: np.ndarray = np.sum(normalized_embeddings[:-1] * normalized_embeddings[1:], axis=1)
        similarity_scores: list[float] = [float(s) for s in similarities.tolist()]
        logging.info(f"Computed {len(similarity_scores)} similarity scores successfully.")

        return similarity_scores

    except Exception as exc:
        logging.error(f"Failed to get similarity scores: {exc}")
        raise MyException(exc, sys) from exc


@traceable(name="get_semantic_splits")
def get_semantic_splits(
    text: str,
    similarity_threshold: float = 0.8,
    max_split_size: int = 600,
) -> list[str]:
    """
    Split text into semantically cohesive chunks based on sentence embedding similarity and size limit.

    Args:
        text (str): The document text to split.
        similarity_threshold (float, optional): Cosine similarity threshold below which a split
            boundary is triggered. Defaults to 0.8.
        max_split_size (int, optional): Maximum character length of a split chunk. Defaults to 600.

    Returns:
        list[str]: A list of semantic text chunks. Returns an empty list if text is empty.

    Raises:
        MyException: If inputs are invalid or semantic splitting fails.
    """
    try:
        logging.info(f"Generating semantic splits (similarity_threshold={similarity_threshold}, max_split_size={max_split_size})...")

        if text is None:
            raise ValueError("text cannot be None")

        if not (0.0 <= similarity_threshold <= 1.0):
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")

        if max_split_size <= 0:
            raise ValueError("max_split_size must be greater than zero")

        if not text.strip():
            logging.info("Input text is empty; returning empty splits list.")
            return []

        sentences: list[str] = get_sentences(text=text)
        if not sentences:
            logging.info("No sentences extracted from text; returning empty splits list.")
            return []

        similarities: list[float] = get_similarities_scores(sentences=sentences, model=EMBEDDING_MODEL)

        splits: list[str] = []
        current_split: str = sentences[0]

        for similarity, sentence in zip(similarities, sentences[1:]):
            split_size: int = len(current_split) + len(sentence) + 1

            if similarity < similarity_threshold or split_size > max_split_size:
                splits.append(current_split)
                current_split = sentence
            else:
                current_split += " " + sentence

        if current_split:
            splits.append(current_split)

        logging.info(f"Generated {len(splits)} semantic splits successfully.")
        return splits

    except Exception as exc:
        logging.error(f"Failed to generate semantic splits: {exc}")
        raise MyException(exc, sys) from exc


def main() -> None:
    """
    Demonstrates semantic splitting pipeline on extracted PDF documents.

    Reads PDF files from the configured PDF directory, cleans extracted text,
    splits text semantically using embedding similarity, and prints sample splits.

    Returns:
        None

    Raises:
        MyException: If the semantic splitting demonstration pipeline fails.
    """
    try:
        logging.info("Running semantic splitting pipeline demonstration...")

        if not PDFS_DIRPATH.exists():
            raise FileNotFoundError(f"PDF directory does not exist: {PDFS_DIRPATH}")

        pdfs: list[Path] = sorted(PDFS_DIRPATH.glob("*.pdf"))[:2]
        if not pdfs:
            logging.warning(f"No PDF files found in {PDFS_DIRPATH}.")
            return

        for pdf in pdfs:
            logging.info(f"Processing PDF file: {pdf.name} (pages up to {PAGE_NO})...")
            text: str = extract_pdf_text(file=pdf, end_page=PAGE_NO)
            clean_text: str = clean_document(text=text)

            splits: list[str] = get_semantic_splits(text=clean_text)

            print(
                colored("_" * WIDTH, "grey"),
                colored(f"{pdf.name}".center(WIDTH), "blue"),
            )
            console.print_json(
                data={
                    "total splits": len(splits),
                    "splits": splits[:5],
                }
            )
            print(colored("_" * WIDTH, "grey"))

        logging.info("Semantic splitting pipeline demonstration completed successfully.")

    except Exception as exc:
        logging.error(f"Failed to run semantic splitting pipeline: {exc}")
        raise MyException(exc, sys) from exc


if __name__ == "__main__":
    main()
