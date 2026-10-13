"""
Embedding model instantiation and vector similarity scoring utilities.
"""

import sys
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

ROOT: Path = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.exception import EmbeddingError, MyException, ValidationError
from src.logger import logging
from src.utils.io import load_yaml_file
from src.utils.paths import PARAMS_FILEPATH

try:
    load_dotenv()
    PARAMS: dict[str, Any] = (
        load_yaml_file(PARAMS_FILEPATH)
        .get("document_splitting", {})
        .get("semantic", {})
    )
    DEFAULT_EMBEDDING_MODEL: str = str(
        PARAMS.get("embedding_model", "gemini-embedding-001")
    )
    DEFAULT_EMBEDDING_DIM: int = int(PARAMS.get("embedding_dimension", 384))
except Exception as e:
    logging.info(f"Failed to initialize embedding utility dependencies: {e}")
    raise MyException(e, sys) from e

__all__: list[str] = [
    "get_embedding_model",
    "get_similarities_scores",
]


@cache
def get_embedding_model(
    model_name: str | None = None,
    output_dimensionality: int | None = None,
) -> GoogleGenerativeAIEmbeddings:
    """
    Lazily initialize and cache the Google Generative AI embeddings model.

    Args:
        model_name (str | None, optional): Model name to use. Defaults to configured model name.
        output_dimensionality (int | None, optional): Output vector dimension.
            Defaults to configured dimension.

    Returns:
        GoogleGenerativeAIEmbeddings: An initialized embeddings model instance.

    Raises:
        EmbeddingError: If initializing the embeddings model fails.
    """
    try:
        m_name: str = model_name or DEFAULT_EMBEDDING_MODEL
        dim: int = output_dimensionality or DEFAULT_EMBEDDING_DIM
        logging.info(f"Initializing embedding model '{m_name}' (dim={dim})...")
        return GoogleGenerativeAIEmbeddings(
            model=m_name,
            output_dimensionality=dim,
        )
    except Exception as e:
        logging.info(f"Failed to initialize embedding model: {e}")
        raise EmbeddingError(e, sys) from e


def get_similarities_scores(
    sentences: list[str],
    model: GoogleGenerativeAIEmbeddings | None = None,
) -> list[float]:
    """
    Calculate consecutive pair-wise cosine similarity scores across a list of sentences.

    Args:
        sentences (list[str]): List of sentences to compare consecutively.
        model (GoogleGenerativeAIEmbeddings | None, optional): Embedding model instance.
            Defaults to the lazily initialized default embedding model.

    Returns:
        list[float]: A list of float cosine similarity scores between consecutive pairs.
            Returns an empty list if fewer than 2 sentences are provided.

    Raises:
        ValidationError: If sentences is None.
        EmbeddingError: If similarity score computation fails.
    """
    try:
        logging.info(
            f"Calculating similarity scores for {len(sentences) if sentences is not None else 0} sentences..."
        )

        if sentences is None:
            raise ValidationError("sentences cannot be None", sys)

        active_model: GoogleGenerativeAIEmbeddings = model or get_embedding_model()

        if len(sentences) < 2:
            logging.info(
                f"Fewer than 2 sentences provided ({len(sentences)}); returning empty similarity list."
            )
            return []

        raw_embeddings: list[list[float]] = active_model.embed_documents(sentences)
        embeddings: np.ndarray = np.asarray(raw_embeddings, dtype=np.float32)

        norms: np.ndarray = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings: np.ndarray = embeddings / np.maximum(norms, 1e-12)

        similarities: np.ndarray = np.sum(
            normalized_embeddings[:-1] * normalized_embeddings[1:], axis=1
        )
        similarity_scores: list[float] = [float(s) for s in similarities.tolist()]
        logging.info(
            f"Computed {len(similarity_scores)} similarity scores successfully."
        )

        return similarity_scores

    except MyException:
        raise
    except Exception as e:
        logging.info(f"Failed to get similarity scores: {e}")
        raise EmbeddingError(e, sys) from e
