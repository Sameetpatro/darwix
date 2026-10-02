import re
from typing import List, Optional, Dict, Any

from q2.models.knowledge_record import KnowledgeRecord
from q2.models.chunk import KnowledgeChunk


class SemanticChunker:
    """
    Splits knowledge records into semantically coherent retrieval chunks.
    Preserves document/section provenance headers and markdown table structure.
    """

    def __init__(self, max_chunk_chars: int = 1200, overlap_chars: int = 200):
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars

    def chunk_record(self, record: KnowledgeRecord) -> List[KnowledgeChunk]:
        """
        Chunks a KnowledgeRecord into a list of KnowledgeChunks with context headers.
        """
        content = record.cleaned_content.strip()
        if not content:
            return []

        section_name = record.source_location.get("section") or record.title or "General"
        product_name = record.product or (record.normalized_entities.loan_products[0] if record.normalized_entities.loan_products else "General")
        
        context_header = (
            f"[Document: {record.source}] "
            f"[Product: {product_name}] "
            f"[Category: {record.category}] "
            f"[Section: {section_name}]"
        )

        # 1. If content is within max size, return single chunk
        if len(content) <= self.max_chunk_chars:
            chunk = KnowledgeChunk(
                record_id=record.record_id,
                chunk_index=0,
                title=record.title,
                content=content,
                context_header=context_header,
                category=record.category,
                product=record.product,
                source=record.source,
                source_location=record.source_location,
                metadata={
                    "char_count": len(content),
                    "word_count": len(content.split()),
                    "conflict_count": len(record.conflicts),
                    "version": record.version,
                },
            )
            return [chunk]

        # 2. Check if text contains markdown table
        if "|" in content and "\n| ---" in content:
            return self._chunk_table_content(record, context_header)

        # 3. Text with sections or long paragraphs
        return self._chunk_prose_content(record, context_header)

    def _chunk_table_content(self, record: KnowledgeRecord, context_header: str) -> List[KnowledgeChunk]:
        """
        Splits markdown tables while preserving table headers on every chunk.
        """
        lines = record.cleaned_content.split("\n")
        table_header_lines = []
        table_rows = []
        prose_before = []
        prose_after = []
        in_table = False

        for line in lines:
            if line.strip().startswith("|") and line.strip().endswith("|"):
                in_table = True
                if len(table_header_lines) < 2:
                    table_header_lines.append(line)
                else:
                    table_rows.append(line)
            else:
                if not in_table:
                    prose_before.append(line)
                else:
                    prose_after.append(line)

        chunks: List[KnowledgeChunk] = []
        chunk_idx = 0

        # Chunk prose before table if substantial
        before_text = "\n".join(prose_before).strip()
        if before_text:
            chunks.append(
                KnowledgeChunk(
                    record_id=record.record_id,
                    chunk_index=chunk_idx,
                    title=record.title,
                    content=before_text,
                    context_header=context_header,
                    category=record.category,
                    product=record.product,
                    source=record.source,
                    source_location=record.source_location,
                    metadata={"table_part": "preamble"},
                )
            )
            chunk_idx += 1

        # Chunk table rows in groups of 2-3 rows with header preserved
        rows_per_chunk = 3
        if not table_rows and table_header_lines:
            # Table is just header or 1 row
            table_text = "\n".join(table_header_lines)
            chunks.append(
                KnowledgeChunk(
                    record_id=record.record_id,
                    chunk_index=chunk_idx,
                    title=f"{record.title} (Table)",
                    content=table_text,
                    context_header=context_header,
                    category=record.category,
                    product=record.product,
                    source=record.source,
                    source_location=record.source_location,
                    metadata={"is_table": True},
                )
            )
            chunk_idx += 1
        else:
            for i in range(0, len(table_rows), rows_per_chunk):
                batch_rows = table_rows[i:i + rows_per_chunk]
                table_text = "\n".join(table_header_lines + batch_rows)
                chunks.append(
                    KnowledgeChunk(
                        record_id=record.record_id,
                        chunk_index=chunk_idx,
                        title=f"{record.title} (Table Rows {i + 1}-{i + len(batch_rows)})",
                        content=table_text,
                        context_header=context_header,
                        category=record.category,
                        product=record.product,
                        source=record.source,
                        source_location=record.source_location,
                        metadata={"is_table": True, "row_start": i + 1, "row_end": i + len(batch_rows)},
                    )
                )
                chunk_idx += 1

        # Chunk prose after table
        after_text = "\n".join(prose_after).strip()
        if after_text:
            chunks.append(
                KnowledgeChunk(
                    record_id=record.record_id,
                    chunk_index=chunk_idx,
                    title=f"{record.title} (Notes)",
                    content=after_text,
                    context_header=context_header,
                    category=record.category,
                    product=record.product,
                    source=record.source,
                    source_location=record.source_location,
                    metadata={"table_part": "postamble"},
                )
            )

        return chunks if chunks else [
            KnowledgeChunk(
                record_id=record.record_id,
                chunk_index=0,
                title=record.title,
                content=record.cleaned_content,
                context_header=context_header,
                category=record.category,
                product=record.product,
                source=record.source,
                source_location=record.source_location,
            )
        ]

    def _chunk_prose_content(self, record: KnowledgeRecord, context_header: str) -> List[KnowledgeChunk]:
        """
        Splits narrative text by paragraphs or sliding window with overlap.
        """
        paragraphs = [p.strip() for p in record.cleaned_content.split("\n\n") if p.strip()]
        chunks: List[KnowledgeChunk] = []
        current_text = ""
        chunk_idx = 0

        for p in paragraphs:
            if len(current_text) + len(p) + 2 <= self.max_chunk_chars:
                current_text = f"{current_text}\n\n{p}".strip() if current_text else p
            else:
                if current_text:
                    chunks.append(
                        KnowledgeChunk(
                            record_id=record.record_id,
                            chunk_index=chunk_idx,
                            title=record.title,
                            content=current_text,
                            context_header=context_header,
                            category=record.category,
                            product=record.product,
                            source=record.source,
                            source_location=record.source_location,
                            metadata={"char_count": len(current_text)},
                        )
                    )
                    chunk_idx += 1
                current_text = p

        if current_text:
            chunks.append(
                KnowledgeChunk(
                    record_id=record.record_id,
                    chunk_index=chunk_idx,
                    title=record.title,
                    content=current_text,
                    context_header=context_header,
                    category=record.category,
                    product=record.product,
                    source=record.source,
                    source_location=record.source_location,
                    metadata={"char_count": len(current_text)},
                )
            )

        return chunks


semantic_chunker = SemanticChunker()
