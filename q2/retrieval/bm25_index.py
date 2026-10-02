import math
import re
from typing import List, Dict, Optional, Tuple, Set

from q2.models.chunk import KnowledgeChunk

STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
    "which", "this", "that", "these", "those", "then", "just", "so", "than",
    "such", "both", "through", "about", "for", "is", "of", "while", "during",
    "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "can", "will", "just", "should",
    "now", "i", "we", "our", "you", "your", "he", "she", "it", "they", "them"
}


def tokenize(text: str) -> List[str]:
    """
    Tokenizes text while preserving percentage symbols, currency markers, and financial numbers.
    e.g. '5.99%', '$25,000', '680', 'sba-7a', 'ach'
    """
    # Normalize currency commas
    clean = text.replace(",", "")
    # Find words, numbers with percentages or decimals, acronyms
    raw_tokens = re.findall(r"\b[\w\.\$%+-]+(?:%|\b)", clean.lower())
    # Filter stopwords and 1-letter non-alphanumeric noise
    return [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 1]


class BM25Index:
    """
    In-memory Okapi BM25 sparse inverted index.
    Optimized for exact keyword lookup on financial figures, interest rates, and loan terms.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: Dict[str, KnowledgeChunk] = {}
        # term -> {chunk_id: frequency}
        self.inverted_index: Dict[str, Dict[str, int]] = {}
        # chunk_id -> document length
        self.doc_lengths: Dict[str, int] = {}
        self.total_docs: int = 0
        self.avg_doc_length: float = 0.0

    def add_chunk(self, chunk: KnowledgeChunk):
        """Indexes a single KnowledgeChunk."""
        self.add_chunks([chunk])

    def add_chunks(self, chunks: List[KnowledgeChunk]):
        """Indexes a batch of KnowledgeChunks."""
        for chunk in chunks:
            chunk_id = chunk.chunk_id
            self.chunks[chunk_id] = chunk

            # Index full contextual text (context header + content)
            searchable_text = chunk.full_context_text
            tokens = tokenize(searchable_text)
            self.doc_lengths[chunk_id] = len(tokens)

            # Term frequencies
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            for t, freq in tf.items():
                if t not in self.inverted_index:
                    self.inverted_index[t] = {}
                self.inverted_index[t][chunk_id] = freq

        self.total_docs = len(self.chunks)
        if self.total_docs > 0:
            self.avg_doc_length = sum(self.doc_lengths.values()) / self.total_docs

    def search(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None,
        product: Optional[str] = None,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        Executes BM25 score ranking against indexed chunks with optional metadata filtering.
        Returns List of (KnowledgeChunk, bm25_score) sorted descending.
        """
        if not query.strip() or self.total_docs == 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[str, float] = {}

        for q in query_tokens:
            if q not in self.inverted_index:
                continue

            posting = self.inverted_index[q]
            df = len(posting)
            # IDF formula with floor guard
            idf = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))

            for chunk_id, freq in posting.items():
                chunk = self.chunks[chunk_id]

                # Metadata filtering
                if category and (not chunk.category or chunk.category.lower() != category.lower()):
                    continue
                if product and (not chunk.product or product.lower() not in chunk.product.lower()):
                    continue

                doc_len = self.doc_lengths.get(chunk_id, 1)
                # BM25 term frequency saturation
                num = freq * (self.k1 + 1.0)
                den = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / max(self.avg_doc_length, 1.0)))
                term_score = idf * (num / den)

                scores[chunk_id] = scores.get(chunk_id, 0.0) + term_score

        # Sort descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.chunks[cid], score) for cid, score in ranked]

    def clear(self):
        """Resets the index."""
        self.chunks.clear()
        self.inverted_index.clear()
        self.doc_lengths.clear()
        self.total_docs = 0
        self.avg_doc_length = 0.0


bm25_index = BM25Index()
