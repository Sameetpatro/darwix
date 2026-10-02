import time
from typing import List, Dict, Any

from q2.models.chunk import KnowledgeChunk
from q2.storage.knowledge_store import knowledge_store
from q2.retrieval.hybrid_search import hybrid_search_engine
from app.logging_config import logger


def index_all_knowledge() -> Dict[str, Any]:
    """
    Loads all cleaned KnowledgeRecords from storage and indexes them
    into dense vectors (Neon pgvector), BM25, and local chunk store.
    """
    start_time = time.time()
    records = knowledge_store.get_all()
    logger.info("[INDEXER] Found %d knowledge records to index.", len(records))

    if not records:
        logger.warning("[INDEXER] No knowledge records found in store.")
        return {
            "status": "empty",
            "total_records": 0,
            "total_chunks": 0,
            "duration_ms": 0,
        }

    chunks = hybrid_search_engine.index_records(records)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(
        "[INDEXER] Successfully indexed %d chunks across %d records in %.2fms.",
        len(chunks),
        len(records),
        duration_ms,
    )

    return {
        "status": "success",
        "total_records": len(records),
        "total_chunks": len(chunks),
        "duration_ms": duration_ms,
    }
