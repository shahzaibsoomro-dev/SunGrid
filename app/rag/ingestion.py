from app.config import get_env, root_dir
from app.rag.embeddings import async_embed
import asyncio
import hashlib
import json
from pathlib import Path
import numpy as np

BATCH_SIZE = 16


def vector_store_dir() -> Path:
    """Folder that holds chunks.json, metadata.json, and index.faiss."""
    return root_dir() / "data" / "vector_store"


def embedding_input(chunk: dict[str, str | list[str]]) -> str:
    """Text sent to the embedding model: section heading, then chunk text."""
    return f"{chunk['section']}\n{chunk['text']}"


def load_stored_chunks(folder: Path) -> list[dict[str, str | list[str]]]:
    """Read the chunk records that were saved for the vector store."""
    path = folder / "chunks.json"
    chunks = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(chunks, list) or not chunks:
        raise RuntimeError(f"{path} must contain a non-empty list of chunks.")
    return chunks


def embedding_fingerprint(chunks: list[dict[str, str | list[str]]]) -> str:
    """Hash the model and the embedding inputs, in chunk order."""
    payload = json.dumps(
        {
            "model": get_env("OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
            "inputs": [embedding_input(chunk) for chunk in chunks],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stored_fingerprint(folder: Path) -> str | None:
    """Return the fingerprint written beside the index, if there is one."""
    path = folder / "metadata.json"
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    fingerprint = document.get("fingerprint")
    if isinstance(fingerprint, str):
        return fingerprint
    return None


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts in concurrent batches and keep input order."""
    batches = [texts[start : start + BATCH_SIZE] for start in range(0, len(texts), BATCH_SIZE)]
    if not batches:
        return []
    results = await asyncio.gather(*(async_embed(batch) for batch in batches))
    vectors = [vector for batch in results for vector in batch]
    if len(vectors) != len(texts):
        raise RuntimeError(f"Expected {len(texts)} embeddings, got {len(vectors)}.")
    return vectors


def embedding_matrix(vectors: list[list[float]]) -> np.ndarray:
    """Return one L2-normalized row per chunk, ready for a cosine index."""
    matrix = np.asarray(vectors, dtype="float32")
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise RuntimeError("No vectors to index.")
    if len({len(vector) for vector in vectors}) != 1:
        raise RuntimeError("Embedding dimensions differ across chunks.")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    np.maximum(norms, 1e-12, out=norms)
    return np.ascontiguousarray(matrix / norms)


def write_faiss(path: Path, matrix: np.ndarray) -> None:
    """Write an inner-product index. Row i is matrix[i]."""
    import faiss

    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    faiss.write_index(index, str(path))


def metadata_document(
    chunks: list[dict[str, str | list[str]]],
    dimensions: int,
    fingerprint: str,
) -> dict[str, object]:
    """Retrieval sidecar. The list position is the FAISS row."""
    return {
        "model": get_env("OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
        "dimensions": dimensions,
        "similarity": "cosine",
        "fingerprint": fingerprint,
        "count": len(chunks),
        "chunks": [
            {
                "row": row,
                "id": chunk["id"],
                "source": chunk["source"],
                "section": chunk["section"],
                "text": chunk["text"],
                "section_categories": chunk["section_categories"],
                "chunk_categories": chunk["chunk_categories"],
            }
            for row, chunk in enumerate(chunks)
        ],
    }


def write_metadata(
    folder: Path,
    chunks: list[dict[str, str | list[str]]],
    dimensions: int,
    fingerprint: str,
) -> None:
    """Write metadata.json next to the FAISS index."""
    document = metadata_document(chunks, dimensions, fingerprint)
    (folder / "metadata.json").write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_stored_matrix(folder: Path, fingerprint: str, count: int) -> np.ndarray | None:
    """Load embeddings.npy when it still matches the current chunks."""
    path = folder / "embeddings.npy"
    if not path.is_file() or stored_fingerprint(folder) != fingerprint:
        return None
    matrix = np.load(path)
    if matrix.ndim != 2 or matrix.shape[0] != count:
        return None
    return np.ascontiguousarray(matrix, dtype="float32")


async def build_vector_store(folder: Path | None = None) -> tuple[int, int, bool]:
    """Embed chunks.json once, then reuse the saved vectors while the inputs match.

    Returns the row count, the vector dimension, and whether the stored
    embeddings were reused instead of calling the embedding API.
    """
    store = folder or vector_store_dir()
    chunks = load_stored_chunks(store)
    fingerprint = embedding_fingerprint(chunks)
    matrix = load_stored_matrix(store, fingerprint, len(chunks))
    reused = matrix is not None
    if matrix is None:
        matrix = embedding_matrix(await embed_texts([embedding_input(chunk) for chunk in chunks]))
        np.save(store / "embeddings.npy", matrix)
    write_metadata(store, chunks, int(matrix.shape[1]), fingerprint)
    try:
        write_faiss(store / "index.faiss", matrix)
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "Saved embeddings.npy and metadata.json. index.faiss was not written because "
            "faiss.dll is blocked. Allow that file and run this again; the embedding API "
            "will not be called."
        ) from exc
    return int(matrix.shape[0]), int(matrix.shape[1]), reused


def main() -> None:
    """Build the vector store from the saved chunks."""
    count, dimensions, reused = asyncio.run(build_vector_store())
    if reused:
        print(f"Reused stored embeddings for {count} chunks at dimension {dimensions}.")
        return
    print(f"Indexed {count} chunks at dimension {dimensions}.")


if __name__ == "__main__":
    main()
