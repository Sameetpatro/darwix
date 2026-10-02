import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import psycopg
from dotenv import load_dotenv

from q2.models.knowledge_record import KnowledgeRecord
from app.logging_config import logger

load_dotenv()

CLEANED_DIR = Path("data/cleaned_knowledge")
CLEANED_DIR.mkdir(parents=True, exist_ok=True)


class KnowledgeStore:
    """
    Manages dual-tier persistence for enterprise knowledge records:
    1. Local JSON files for reproducible inspection and fast file-based tests.
    2. Cloud PostgreSQL (Neon DB) table with JSONB attributes and indexing.
    """

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self._init_db_schema()

    def _init_db_schema(self):
        """Initializes database schema and indexes in Neon PostgreSQL."""
        if not self.db_url:
            logger.warning("[KNOWLEDGE-STORE] No DATABASE_URL provided. Operating in JSON-only mode.")
            return

        try:
            with psycopg.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS knowledge_records (
                            record_id VARCHAR(64) PRIMARY KEY,
                            source_doc_id VARCHAR(64) NOT NULL,
                            title TEXT NOT NULL,
                            cleaned_content TEXT NOT NULL,
                            original_content_hash VARCHAR(64) NOT NULL,
                            cleaned_content_hash VARCHAR(64) NOT NULL,
                            category VARCHAR(32) NOT NULL,
                            product VARCHAR(64),
                            source TEXT NOT NULL,
                            source_location JSONB,
                            version VARCHAR(32),
                            effective_date VARCHAR(32),
                            normalized_entities JSONB,
                            pii_audit JSONB,
                            conflicts JSONB,
                            is_duplicate BOOLEAN DEFAULT FALSE,
                            duplicate_of VARCHAR(64),
                            created_at DOUBLE PRECISION NOT NULL
                        );

                        CREATE INDEX IF NOT EXISTS idx_krec_category ON knowledge_records(category);
                        CREATE INDEX IF NOT EXISTS idx_krec_product ON knowledge_records(product);
                        CREATE INDEX IF NOT EXISTS idx_krec_cleaned_hash ON knowledge_records(cleaned_content_hash);
                    """)
                    conn.commit()
            logger.info("[KNOWLEDGE-STORE] Initialized PostgreSQL 'knowledge_records' table.")
        except Exception as exc:
            logger.error("[KNOWLEDGE-STORE] Database initialization failed: %s", exc)

    def save_record(self, record: KnowledgeRecord) -> str:
        """Saves record to local JSON and Neon PostgreSQL."""
        # 1. Save to JSON file
        json_path = CLEANED_DIR / f"{record.record_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2, ensure_ascii=False)

        # 2. Save to PostgreSQL if available
        if self.db_url:
            try:
                with psycopg.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO knowledge_records (
                                record_id, source_doc_id, title, cleaned_content,
                                original_content_hash, cleaned_content_hash, category,
                                product, source, source_location, version, effective_date,
                                normalized_entities, pii_audit, conflicts, is_duplicate,
                                duplicate_of, created_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (record_id) DO UPDATE SET
                                cleaned_content = EXCLUDED.cleaned_content,
                                normalized_entities = EXCLUDED.normalized_entities,
                                pii_audit = EXCLUDED.pii_audit,
                                conflicts = EXCLUDED.conflicts,
                                is_duplicate = EXCLUDED.is_duplicate,
                                duplicate_of = EXCLUDED.duplicate_of;
                        """, (
                            record.record_id,
                            record.source_doc_id,
                            record.title,
                            record.cleaned_content,
                            record.original_content_hash,
                            record.cleaned_content_hash,
                            record.category,
                            record.product,
                            record.source,
                            json.dumps(record.source_location),
                            record.version,
                            record.effective_date,
                            json.dumps(record.normalized_entities.model_dump()),
                            json.dumps(record.pii_audit),
                            json.dumps([c.model_dump() for c in record.conflicts]),
                            record.is_duplicate,
                            record.duplicate_of,
                            record.created_at,
                        ))
                        conn.commit()
            except Exception as exc:
                logger.warning("[KNOWLEDGE-STORE] PostgreSQL save error for record %s: %s", record.record_id, exc)

        return str(json_path)

    def save_batch(self, records: List[KnowledgeRecord]) -> List[str]:
        """Saves a batch of records using a single database connection and transaction."""
        paths = []
        # 1. Save local JSON files
        for r in records:
            json_path = CLEANED_DIR / f"{r.record_id}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(r.to_dict(), f, indent=2, ensure_ascii=False)
            paths.append(str(json_path))

        # 2. Batch insert/upsert into PostgreSQL in one transaction
        if self.db_url and records:
            try:
                with psycopg.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        query = """
                            INSERT INTO knowledge_records (
                                record_id, source_doc_id, title, cleaned_content,
                                original_content_hash, cleaned_content_hash, category,
                                product, source, source_location, version, effective_date,
                                normalized_entities, pii_audit, conflicts, is_duplicate,
                                duplicate_of, created_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (record_id) DO UPDATE SET
                                cleaned_content = EXCLUDED.cleaned_content,
                                normalized_entities = EXCLUDED.normalized_entities,
                                pii_audit = EXCLUDED.pii_audit,
                                conflicts = EXCLUDED.conflicts,
                                is_duplicate = EXCLUDED.is_duplicate,
                                duplicate_of = EXCLUDED.duplicate_of;
                        """
                        params = [
                            (
                                r.record_id,
                                r.source_doc_id,
                                r.title,
                                r.cleaned_content,
                                r.original_content_hash,
                                r.cleaned_content_hash,
                                r.category,
                                r.product,
                                r.source,
                                json.dumps(r.source_location),
                                r.version,
                                r.effective_date,
                                json.dumps(r.normalized_entities.model_dump()),
                                json.dumps(r.pii_audit),
                                json.dumps([c.model_dump() for c in r.conflicts]),
                                r.is_duplicate,
                                r.duplicate_of,
                                r.created_at,
                            )
                            for r in records
                        ]
                        cur.executemany(query, params)
                        conn.commit()
            except Exception as exc:
                logger.warning("[KNOWLEDGE-STORE] PostgreSQL batch save error: %s", exc)

        return paths

    def get_by_id(self, record_id: str) -> Optional[KnowledgeRecord]:
        """Fetches a record by ID with fast local cache priority."""
        if hasattr(self, "_records_cache") and record_id in self._records_cache:
            return self._records_cache[record_id]

        # Check local JSON first (instantaneous, no network latency)
        json_path = CLEANED_DIR / f"{record_id}.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    rec = KnowledgeRecord.model_validate(data)
                    if not hasattr(self, "_records_cache"):
                        self._records_cache = {}
                    self._records_cache[record_id] = rec
                    return rec
            except Exception:
                pass

        # Check database if not found locally
        if self.db_url:
            try:
                with psycopg.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT * FROM knowledge_records WHERE record_id = %s", (record_id,))
                        row = cur.fetchone()
                        if row:
                            rec = self._row_to_record(cur, row)
                            if not hasattr(self, "_records_cache"):
                                self._records_cache = {}
                            self._records_cache[record_id] = rec
                            return rec
            except Exception as exc:
                logger.warning("[KNOWLEDGE-STORE] DB fetch error: %s", exc)

        return None

    def get_all(self) -> List[KnowledgeRecord]:
        """Returns all knowledge records."""
        records = []
        if self.db_url:
            try:
                with psycopg.connect(self.db_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT * FROM knowledge_records ORDER BY created_at ASC")
                        rows = cur.fetchall()
                        for row in rows:
                            records.append(self._row_to_record(cur, row))
                        if records:
                            return records
            except Exception as exc:
                logger.warning("[KNOWLEDGE-STORE] DB list error: %s", exc)

        # Fallback to local JSON files
        for p in CLEANED_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    records.append(KnowledgeRecord.model_validate(data))
            except Exception:
                pass
        return records

    def _row_to_record(self, cur, row) -> KnowledgeRecord:
        col_names = [d[0] for d in cur.description]
        row_dict = dict(zip(col_names, row))
        return KnowledgeRecord.model_validate(row_dict)


knowledge_store = KnowledgeStore()
