import hashlib
import re
from typing import Dict, List, Optional, Tuple, Set


import difflib


def compute_content_hash(text: str) -> str:
    """Computes a deterministic SHA-256 hash of normalized text."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def tokenize_shingles(text: str, n: int = 2) -> Set[str]:
    """Generates character/word n-gram shingles and unigrams for similarity comparison."""
    words = re.findall(r"\w+", text.lower())
    shingles = set(words)  # include unigrams
    if len(words) >= n:
        shingles.update(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))
    return shingles


def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Computes Jaccard similarity between two shingle sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return intersection / union if union > 0 else 0.0


def compute_text_similarity(text_a: str, set_a: Set[str], text_b: str, set_b: Set[str]) -> float:
    """Computes combined Jaccard and SequenceMatcher similarity score."""
    jacc = jaccard_similarity(set_a, set_b)
    seq_ratio = difflib.SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio()
    return max(jacc, seq_ratio)


class Deduplicator:
    """
    Manages exact and near-duplicate detection across knowledge records.
    Maintains index of seen content hashes and token shingles.
    """

    def __init__(self, near_duplicate_threshold: float = 0.85):
        self.near_duplicate_threshold = near_duplicate_threshold
        # hash -> record_id
        self._exact_hash_index: Dict[str, str] = {}
        # record_id -> (text, shingles)
        self._shingle_index: Dict[str, Tuple[str, Set[str]]] = {}

    def check_and_register(
        self, record_id: str, content: str
    ) -> Tuple[bool, Optional[str], float, str]:
        """
        Checks if the content is an exact or near duplicate of an existing record.
        If unique, registers the record into the index.

        Returns:
            (is_duplicate, duplicate_of_record_id, similarity_score, content_hash)
        """
        content_hash = compute_content_hash(content)

        # 1. Exact match
        if content_hash in self._exact_hash_index:
            existing_id = self._exact_hash_index[content_hash]
            return True, existing_id, 1.0, content_hash

        # 2. Near-duplicate match
        shingles = tokenize_shingles(content)
        highest_sim = 0.0
        best_match_id = None

        for existing_id, (existing_text, existing_shingles) in self._shingle_index.items():
            sim = compute_text_similarity(content, shingles, existing_text, existing_shingles)
            if sim > highest_sim:
                highest_sim = sim
                best_match_id = existing_id

        if highest_sim >= self.near_duplicate_threshold and best_match_id:
            return True, best_match_id, round(highest_sim, 4), content_hash

        # 3. Unique -> Register
        self._exact_hash_index[content_hash] = record_id
        self._shingle_index[record_id] = (content, shingles)
        return False, None, round(highest_sim, 4), content_hash

    def reset(self):
        """Clears in-memory index."""
        self._exact_hash_index.clear()
        self._shingle_index.clear()


deduplicator = Deduplicator()
