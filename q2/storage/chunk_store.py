import os
import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import psycopg
from dotenv import load_dotenv

from q2.models.chunk import KnowledgeChunk
from app.logging_config import logger

load_dotenv()

INDEXED_CHUNKS_DIR = Path("data/indexed_chunks")
INDEXED_CHUNKS_DIR.mkdir(parents=True, exist_ok=True)


class ChunkStore:
    """
    Manages persistence and dense vector retrieval for KnowledgeChunks:
    1. Neon PostgreSQL with pgvector (384 dimensions) and HNSW cosine distance indexing.
    2. Local JSON files in data/indexed_chunks/ for local caching and offline testing.
    3. In-memory cosine similarity fallback.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._memory_chunks: Dict[str, KnowledgeChunk] = {}
        self._init_db_schema()

    def _init_db_schema(self):
        """Initializes pgvector extension and knowledge_chunks table in Neon PostgreSQL."""
        if not self.db_url:
            logger.warning("[CHUNK-STORE] No DATABASE_URL provided. Operating in JSON/memory-only mode.")
            return

        try:
            with psycopg.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS knowledge_chunks (
                            chunk_id VARCHAR(64) PRIMARY KEY,
                            record_id VARCHAR(64) NOT NULL,
                            chunk_index INT NOT NULL,
                            title TEXT NOT NULL,
                            content TEXT NOT NULL,
                            context_header TEXT NOT NULL,
                            category VARCHAR(32) NOT NULL,
                            product VARCHAR(64),
                            source TEXT NOT NULL,
                            source_location JSONB,
                            embedding vector(384),
                            metadata JSONB,
                            created_at DOUBLE PRECISION NOT NULL
                        );

                        CREATE INDEX IF NOT EXISTS idx_chunks_record_id ON knowledge_chunks(record_id);
                        CREATE INDEX IF NOT EXISTS idx_chunks_category ON knowledge_chunks(category);
                        CREATE INDEX IF NOT EXISTS idx_chunks_product ON knowledge_chunks(product);
                    """)
                    # Create HNSW index if table has data or create conditionally
                    try:
                        cur.execute("""
                            CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
                            ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
                        """)
                    except Exception:
                        pass
                    conn.commit()
            logger.info("[CHUNK-STORE] Initialized PostgreSQL 'knowledge_chunks' pgvector table.")
        except Exception as exc:
            logger.error("[CHUNK-STORE] Database initialization failed: %s", exc)

    def save_chunks(self, chunks: List[KnowledgeChunk]) -> List[str]:
        """
        Saves a batch of chunks to local JSON files, in-memory cache, and Neon PostgreSQL.
        """
        paths = []
        for c in chunks:
            # 1. Update in-memory cache
            self._memory_chunks[c.chunk_id] = c

            # 2. Save local JSON file
            json_path = INDEXED_CHUNKS_DIR / f"{c.chunk_id}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(c.to_dict(), f, indent=2, ensure_ascii=False)
            paths.append(str(json_path))

        # 3. Batch insert into PostgreSQL
        if self.db_url and chunks:
            try:
                with psycopg.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        query = """
                            INSERT INTO knowledge_chunks (
                                chunk_id, record_id, chunk_index, title, content,
                                context_header, category, product, source,
                                source_location, embedding, metadata, created_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s
                            )
                            ON CONFLICT (chunk_id) DO UPDATE SET
                                content = EXCLUDED.content,
                                context_header = EXCLUDED.context_header,
                                embedding = EXCLUDED.embedding,
                                metadata = EXCLUDED.metadata;
                        """
                        params = [
                            (
                                c.chunk_id,
                                c.record_id,
                                c.chunk_index,
                                c.title,
                                c.content,
                                c.context_header,
                                c.category,
                                c.product,
                                c.source,
                                json.dumps(c.source_location),
                                str(c.embedding) if c.embedding else None,
                                json.dumps(c.metadata),
                                c.created_at,
                            )
                            for c in chunks
                        ]
                        cur.executemany(query, params)
                        conn.commit()
            except Exception as exc:
                logger.warning("[CHUNK-STORE] PostgreSQL batch insert error: %s", exc)

        return paths

    def query_dense(
        self,
        query_vector: List[float],
        top_k: int = 10,
        category: Optional[str] = None,
        product: Optional[str] = None,
        use_pgvector: bool = False,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """
        Executes vector cosine similarity search.
        Defaults to high-speed in-memory vector cosine similarity (<5ms)
        and supports direct Neon PostgreSQL pgvector querying when use_pgvector=True.
        """
        if not use_pgvector:
            # Ensure memory cache is populated
            if not self._memory_chunks:
                self.get_all_chunks()
            if self._memory_chunks:
                return self._query_dense_memory(query_vector, top_k, category, product)

        # Direct Neon PostgreSQL pgvector query
        if self.db_url:
            try:
                with psycopg.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        vec_str = str(query_vector)
                        sql = """
                            SELECT chunk_id, record_id, chunk_index, title, content,
                                   context_header, category, product, source,
                                   source_location, metadata, created_at,
                                   1.0 - (embedding <=> %s::vector) AS cosine_similarity
                            FROM knowledge_chunks
                            WHERE (%s::text IS NULL OR category = %s)
                              AND (%s::text IS NULL OR product = %s)
                            ORDER BY embedding <=> %s::vector ASC
                            LIMIT %s;
                        """
                        cur.execute(sql, (vec_str, category, category, product, product, vec_str, top_k))
                        rows = cur.fetchall()
                        results = []
                        for r in rows:
                            chunk = KnowledgeChunk(
                                chunk_id=r[0],
                                record_id=r[1],
                                chunk_index=r[2],
                                title=r[3],
                                content=r[4],
                                context_header=r[5],
                                category=r[6],
                                product=r[7],
                                source=r[8],
                                source_location=r[9] if isinstance(r[9], dict) else {},
                                metadata=r[10] if isinstance(r[10], dict) else {},
                                created_at=r[11],
                            )
                            score = float(r[12]) if r[12] is not None else 0.0
                            results.append((chunk, score))
                        if results:
                            return results
            except Exception as exc:
                logger.warning("[CHUNK-STORE] pgvector search failed: %s. Falling back to memory.", exc)

        return self._query_dense_memory(query_vector, top_k, category, product)

    def _query_dense_memory(
        self,
        query_vector: List[float],
        top_k: int = 10,
        category: Optional[str] = None,
        product: Optional[str] = None,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        """Computes in-memory cosine similarity across all cached chunks."""
        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        scored = []
        for chunk in self._memory_chunks.values():
            if category and (not chunk.category or chunk.category.lower() != category.lower()):
                continue
            if product and (not chunk.product or product.lower() not in chunk.product.lower()):
                continue
            if not chunk.embedding:
                continue

            c_vec = np.array(chunk.embedding, dtype=np.float32)
            c_norm = np.linalg.norm(c_vec)
            if c_norm == 0:
                continue

            cos_sim = float(np.dot(q_vec, c_vec) / (q_norm * c_norm))
            scored.append((chunk, cos_sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_all_chunks(self) -> List[KnowledgeChunk]:
        """Returns all chunks from memory or local files."""
        if self._memory_chunks:
            return list(self._memory_chunks.values())

        chunks = []
        for p in INDEXED_CHUNKS_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    c = KnowledgeChunk.model_validate(data)
                    self._memory_chunks[c.chunk_id] = c
                    chunks.append(c)
            except Exception:
                pass
        return chunks


chunk_store = ChunkStore()
