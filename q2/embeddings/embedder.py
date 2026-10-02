import hashlib
from typing import List, Dict, Optional
from fastembed import TextEmbedding

from app.logging_config import logger


class Embedder:
    """
    Unified dense vector embedding provider.
    Uses FastEmbed (BAAI/bge-small-en-v1.5) ONNX model by default (384 dimensions).
    Provides high-throughput batching and in-memory LRU-style hashing cache.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self.dimension = 384
        logger.info("[EMBEDDER] Initializing FastEmbed model '%s'...", model_name)
        self._model = TextEmbedding(model_name)
        self._cache: Dict[str, List[float]] = {}

    def embed_text(self, text: str) -> List[float]:
        """Generates embedding for a single string."""
        text = text.strip()
        if not text:
            return [0.0] * self.dimension

        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text_hash in self._cache:
            return self._cache[text_hash]

        embeddings = list(self._model.embed([text]))
        vec = embeddings[0].tolist()
        self._cache[text_hash] = vec
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of strings efficiently."""
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for idx, t in enumerate(texts):
            clean_t = t.strip()
            if not clean_t:
                results[idx] = [0.0] * self.dimension
                continue

            h = hashlib.sha256(clean_t.encode("utf-8")).hexdigest()
            if h in self._cache:
                results[idx] = self._cache[h]
            else:
                uncached_indices.append(idx)
                uncached_texts.append(clean_t)

        if uncached_texts:
            computed_embeddings = list(self._model.embed(uncached_texts))
            for i, emb in enumerate(computed_embeddings):
                vec = emb.tolist()
                orig_idx = uncached_indices[i]
                orig_text = uncached_texts[i]
                h = hashlib.sha256(orig_text.encode("utf-8")).hexdigest()
                self._cache[h] = vec
                results[orig_idx] = vec

        return [r for r in results if r is not None]


embedder = Embedder()
