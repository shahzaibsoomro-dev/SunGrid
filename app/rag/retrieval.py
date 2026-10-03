"""Retrieve chunks by category, then rank them against the query.

The category list is a filter on chunk_categories. section_categories is
not read. Vectors come from the stored embeddings, not a new corpus embed.
"""

import json
from pathlib import Path

import numpy as np

from app.rag.embeddings import async_embed
from app.rag.ingestion import vector_store_dir

SCORE_THRESHOLD = 0.50


async def retrieve(query: str, categories: list[str], folder: Path | None = None) -> list[dict[str, str]]:
    """Return close chunks as text, section, and source."""
    store = folder or vector_store_dir()
    selected = matching_chunks(load_metadata(store), categories)
    if not query.strip() or not selected:
        return []
    query_vector = await embed_query(query)
    matrix = np.load(store / "embeddings.npy")
    rows = [int(chunk["row"]) for chunk in selected]
    scores = matrix[rows] @ query_vector
    return [hit(selected[index]) for index in kept_indexes(scores)]


def kept_indexes(scores: np.ndarray) -> list[int]:
    """Keep scores of at least 50%. If more than three pass, keep the top five."""
    order = np.argsort(-scores)
    passing = [int(index) for index in order if float(scores[int(index)]) >= SCORE_THRESHOLD]
    if len(passing) > 3:
        return passing[:5]
    return passing


def matching_chunks(chunks: list[dict[str, object]], categories: list[str]) -> list[dict[str, object]]:
    """Keep chunks whose chunk_categories overlap the requested labels."""
    wanted = set(categories)
    if not wanted:
        return []
    return [
        chunk
        for chunk in chunks
        if wanted.intersection(chunk.get("chunk_categories") or [])
    ]


def load_metadata(folder: Path) -> list[dict[str, object]]:
    """Read the retrieval records saved beside the embeddings."""
    document = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    chunks = document.get("chunks")
    if not isinstance(chunks, list):
        raise RuntimeError(f"{folder / 'metadata.json'} has no chunk list.")
    return chunks


async def embed_query(query: str) -> np.ndarray:
    """Embed one query and L2-normalize it so a dot product is cosine."""
    vectors = await async_embed([query])
    if len(vectors) != 1:
        raise RuntimeError("The query embedding did not return one vector.")
    vector = np.asarray(vectors[0], dtype="float32")
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise RuntimeError("The query embedding was empty.")
    return vector / norm


def hit(chunk: dict[str, object]) -> dict[str, str]:
    """The fields a caller is allowed to see for one retrieved chunk."""
    return {
        "text": str(chunk["text"]),
        "section": str(chunk["section"]),
        "source": str(chunk["source"]),
    }
