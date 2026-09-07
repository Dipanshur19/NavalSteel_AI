"""
Embedding + local vector index (Phase-1 storage).

Two backends are supported, selected via EMBEDDING_BACKEND in .env:

  * "tfidf" (default): scikit-learn TF-IDF vectors. Works fully offline
    after `pip install`, no model download, no API key. Good enough for
    a single-document or small-corpus Phase-1 prototype.

  * "sbert": sentence-transformers embeddings (better semantic recall on
    paraphrased questions). Downloads a small model from Hugging Face on
    first use, so it needs internet access once.

The index itself is a flat NumPy array + pickled metadata, exactly the
"local NumPy index" called for in the report's Phase-1 storage table.
Swapping in FAISS or pgvector later only means replacing this file.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from . import config


class TfidfBackend:
    name = "tfidf"

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
        self._fitted = False

    def fit_transform(self, texts: List[str]) -> np.ndarray:
        mat = self.vectorizer.fit_transform(texts)
        self._fitted = True
        return mat.toarray().astype(np.float32)

    def transform(self, texts: List[str]) -> np.ndarray:
        mat = self.vectorizer.transform(texts)
        return mat.toarray().astype(np.float32)

    def state_dict(self) -> Dict[str, Any]:
        return {"vectorizer": self.vectorizer}

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "TfidfBackend":
        obj = cls.__new__(cls)
        obj.vectorizer = state["vectorizer"]
        obj._fitted = True
        return obj


class SbertBackend:
    name = "sbert"

    def __init__(self, model_name: str = config.SBERT_MODEL_NAME):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def fit_transform(self, texts: List[str]) -> np.ndarray:
        return self.transform(texts)

    def transform(self, texts: List[str]) -> np.ndarray:
        vecs = self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)

    def state_dict(self) -> Dict[str, Any]:
        return {"model_name": self.model_name}

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "SbertBackend":
        return cls(model_name=state["model_name"])


def get_backend(name: str = config.EMBEDDING_BACKEND):
    if name == "tfidf":
        return TfidfBackend()
    if name == "sbert":
        return SbertBackend()
    raise ValueError(f"Unknown embedding backend: {name!r}. Use 'tfidf' or 'sbert'.")


def _cosine_sim(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    m_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9
    m = matrix / m_norms
    return m @ q


def build_index(chunks_json_path: Path, backend_name: str = config.EMBEDDING_BACKEND) -> Dict[str, Any]:
    with open(chunks_json_path, encoding="utf-8") as f:
        doc = json.load(f)

    chunks = doc["chunks"]
    texts = [c["text"] for c in chunks]
    backend = get_backend(backend_name)
    vectors = backend.fit_transform(texts)

    return {
        "backend": backend.name,
        "backend_state": backend.state_dict(),
        "filename": doc["filename"],
        "doc_hash": doc["doc_hash"],
        "vectors": vectors,
        "chunks": chunks,
    }


def save_index(index: Dict[str, Any], out_path: Path) -> None:
    with open(out_path, "wb") as f:
        pickle.dump(index, f)


def load_index(index_path: Path) -> Dict[str, Any]:
    with open(index_path, "rb") as f:
        return pickle.load(f)


def search(index: Dict[str, Any], query: str, top_k: int = config.TOP_K) -> List[Tuple[float, Dict[str, Any]]]:
    backend_name = index["backend"]
    if backend_name == "tfidf":
        backend = TfidfBackend.from_state(index["backend_state"])
    elif backend_name == "sbert":
        backend = SbertBackend.from_state(index["backend_state"])
    else:
        raise ValueError(f"Unknown backend in index: {backend_name!r}")

    query_vec = backend.transform([query])[0]
    sims = _cosine_sim(query_vec, index["vectors"])
    order = np.argsort(-sims)[:top_k]
    return [(float(sims[i]), index["chunks"][i]) for i in order]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build a local embedding index for a chunked document")
    parser.add_argument("--chunks", required=True, help="Path to a *.chunks.json file")
    parser.add_argument("--backend", default=config.EMBEDDING_BACKEND, choices=["tfidf", "sbert"])
    parser.add_argument("--out-dir", default=str(config.INDEX_DIR))
    args = parser.parse_args(argv)

    chunks_path = Path(args.chunks)
    index = build_index(chunks_path, backend_name=args.backend)

    out_path = Path(args.out_dir) / (chunks_path.stem.replace(".chunks", "") + ".index.pkl")
    save_index(index, out_path)

    print(f"Built '{args.backend}' index over {len(index['chunks'])} chunks.")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
