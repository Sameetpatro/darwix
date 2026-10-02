from typing import List, Dict, Optional, Tuple, Any
from q2.models.chunk import KnowledgeChunk, SearchResult
from q2.models.knowledge_record import KnowledgeRecord
from q2.chunking.semantic_chunker import semantic_chunker
from q2.embeddings.embedder import embedder
from q2.retrieval.bm25_index import bm25_index
from q2.storage.chunk_store import chunk_store
from q2.storage.knowledge_store import knowledge_store
from app.logging_config import logger


class HybridSearchEngine:
    """
    State-of-the-art Hybrid Retrieval Engine combining:
    1. Dense Vector Semantic Search (BGE-small 384-dim via Neon pgvector or in-memory)
    2. Sparse BM25 Keyword Search (Exact financial figures, FICO, APR, percentages)
    3. Reciprocal Rank Fusion (RRF) with configurable dense/sparse weighting
    4. Conflict attachment from parent KnowledgeRecord
    """

    def __init__(
        self,
        rrf_k: int = 60,
        default_dense_weight: float = 0.6,
        default_sparse_weight: float = 0.4,
    ):
        self.rrf_k = rrf_k
        self.default_dense_weight = default_dense_weight
        self.default_sparse_weight = default_sparse_weight

    def index_records(self, records: List[KnowledgeRecord]) -> List[KnowledgeChunk]:
        """
        End-to-end indexing pipeline:
        1. Semantic chunking preserving context headers & markdown tables.
        2. High-throughput dense vector embedding generation.
        3. Dual-tier persistence to Neon PostgreSQL (pgvector) and local JSON.
        4. BM25 inverted index population.
        """
        all_chunks: List[KnowledgeChunk] = []

        # 1. Chunk all records
        for rec in records:
            chunks = semantic_chunker.chunk_record(rec)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("[HYBRID-SEARCH] No chunks produced from records.")
            return []

        # 2. Batch embed full contextual text
        texts_to_embed = [c.full_context_text for c in all_chunks]
        embeddings = embedder.embed_batch(texts_to_embed)

        for c, emb in zip(all_chunks, embeddings):
            c.embedding = emb

        # 3. Save chunks to PostgreSQL pgvector and local files
        chunk_store.save_chunks(all_chunks)

        # 4. Populate BM25 index
        bm25_index.add_chunks(all_chunks)

        logger.info("[HYBRID-SEARCH] Successfully indexed %d chunks from %d records.", len(all_chunks), len(records))
        return all_chunks

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        product: Optional[str] = None,
        dense_weight: Optional[float] = None,
        sparse_weight: Optional[float] = None,
        candidate_pool_size: int = 25,
    ) -> List[SearchResult]:
        """
        Executes hybrid retrieval using Reciprocal Rank Fusion.
        """
        query = query.strip()
        if not query:
            return []

        # Auto-populate BM25 index if empty
        if bm25_index.total_docs == 0:
            cached_chunks = chunk_store.get_all_chunks()
            if cached_chunks:
                bm25_index.add_chunks(cached_chunks)

        w_dense = dense_weight if dense_weight is not None else self.default_dense_weight
        w_sparse = sparse_weight if sparse_weight is not None else self.default_sparse_weight

        # 1. Dense retrieval
        q_emb = embedder.embed_text(query)
        dense_hits: List[Tuple[KnowledgeChunk, float]] = chunk_store.query_dense(
            query_vector=q_emb,
            top_k=candidate_pool_size,
            category=category,
            product=product,
        )

        # 2. Sparse BM25 retrieval
        sparse_hits: List[Tuple[KnowledgeChunk, float]] = bm25_index.search(
            query=query,
            top_k=candidate_pool_size,
            category=category,
            product=product,
        )

        # Maps chunk_id -> dict of rank and raw score
        dense_ranks: Dict[str, Tuple[int, float, KnowledgeChunk]] = {
            chunk.chunk_id: (rank + 1, score, chunk)
            for rank, (chunk, score) in enumerate(dense_hits)
        }
        sparse_ranks: Dict[str, Tuple[int, float, KnowledgeChunk]] = {
            chunk.chunk_id: (rank + 1, score, chunk)
            for rank, (chunk, score) in enumerate(sparse_hits)
        }

        # Union of all candidate chunk IDs
        all_chunk_ids = set(dense_ranks.keys()).union(sparse_ranks.keys())
        if not all_chunk_ids:
            return []

        # 3. Reciprocal Rank Fusion (RRF)
        scored_candidates: List[SearchResult] = []

        for cid in all_chunk_ids:
            # Resolve chunk instance
            if cid in dense_ranks:
                d_rank, d_score, chunk = dense_ranks[cid]
            else:
                d_rank, d_score, chunk = 999999, 0.0, sparse_ranks[cid][2]

            if cid in sparse_ranks:
                s_rank, s_score, _ = sparse_ranks[cid]
            else:
                s_rank, s_score = 999999, 0.0

            # Compute RRF score
            rrf_score = 0.0
            if d_rank < 999999:
                rrf_score += w_dense / (self.rrf_k + d_rank)
            if s_rank < 999999:
                rrf_score += w_sparse / (self.rrf_k + s_rank)

            # Look up conflicts from parent KnowledgeRecord
            parent_record = knowledge_store.get_by_id(chunk.record_id)
            conflicts = parent_record.conflicts if parent_record else []

            result = SearchResult(
                chunk=chunk,
                dense_score=round(d_score, 4),
                sparse_score=round(s_score, 4),
                fused_score=round(rrf_score, 6),
                conflicts=conflicts,
            )
            scored_candidates.append(result)

        # 4. Sort by fused score descending
        scored_candidates.sort(key=lambda x: x.fused_score, reverse=True)

        # Assign final 1-indexed ranks
        final_results = scored_candidates[:top_k]
        for idx, res in enumerate(final_results):
            res.rank = idx + 1

        return final_results


hybrid_search_engine = HybridSearchEngine()
