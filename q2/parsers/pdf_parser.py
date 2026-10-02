import re
from pathlib import Path
from typing import List, Union, Optional
import pypdf

from q2.models.raw_document import RawDocument, TableData
from q2.parsers.base_parser import BaseParser
from app.logging_config import logger


class PDFParser(BaseParser):
    """
    Extracts text, headings, sections, and tables from PDF documents.
    Tracks exact 1-indexed page numbers and section headers.
    """

    def can_parse(self, file_path: Union[str, Path]) -> bool:
        path = Path(file_path)
        return path.suffix.lower() == ".pdf"

    def parse(self, file_path: Union[str, Path]) -> List[RawDocument]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")

        documents: List[RawDocument] = []
        try:
            reader = pypdf.PdfReader(str(path))
            total_pages = len(reader.pages)
            logger.info("[PDF-PARSER] Parsing '%s' (%d pages)", path.name, total_pages)

            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                try:
                    text = page.extract_text() or ""
                except Exception as exc:
                    logger.warning("[PDF-PARSER] Text extraction warning on page %d: %s", page_num, exc)
                    text = ""

                clean_text = text.strip()
                if not clean_text:
                    continue

                # Heading & Section detection
                lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
                page_title = path.stem.replace("_", " ").title()
                section_title = f"Page {page_num}"

                for line in lines[:5]:
                    # Match patterns like 'Section 1: ...', 'Chapter 2: ...', or bold titles
                    if re.match(r"^(?:Section\s+\d+|Chapter\s+\d+|Part\s+\d+|[A-Z0-9\s]{4,}):?", line, re.IGNORECASE):
                        section_title = line
                        page_title = line
                        break
                    elif len(line) < 70 and not line.endswith("."):
                        page_title = line
                        section_title = line
                        break

                # Detect potential tabular data in page text
                tables = self._extract_text_tables(lines)

                doc = RawDocument(
                    source_type="pdf",
                    source=path.name,
                    page=page_num,
                    section=section_title,
                    title=page_title,
                    raw_content=clean_text,
                    tables=tables,
                    extraction_status="success",
                    metadata={
                        "total_pages": total_pages,
                        "file_size_bytes": path.stat().st_size,
                        "parser": "pypdf",
                        "character_count": len(clean_text),
                        "word_count": len(clean_text.split()),
                    },
                )
                documents.append(doc)

            if not documents:
                # If no text extracted (e.g. scanned or empty), return single flagged record
                documents.append(
                    RawDocument(
                        source_type="pdf",
                        source=path.name,
                        page=1,
                        title=path.stem.title(),
                        raw_content="",
                        extraction_status="failed",
                        metadata={"error": "PDF produced empty text (possible scanned/raster image)"},
                    )
                )

        except Exception as exc:
            logger.error("[PDF-PARSER] Failed parsing PDF %s: %s", path.name, exc)
            documents.append(
                RawDocument(
                    source_type="pdf",
                    source=path.name,
                    page=1,
                    title=path.stem.title(),
                    raw_content="",
                    extraction_status="failed",
                    metadata={"error": str(exc)},
                )
            )

        return documents

    def _extract_text_tables(self, lines: List[str]) -> List[TableData]:
        """Detects ASCII/aligned tabular text rows."""
        tables = []
        table_rows = []
        for line in lines:
            # Lines with multiple delimiters or wide spaced columns
            if "|" in line or "\t" in line or re.search(r"\s{3,}", line):
                parts = [p.strip() for p in re.split(r"\||\t|\s{3,}", line) if p.strip()]
                if len(parts) >= 2:
                    table_rows.append(parts)

        if len(table_rows) >= 2:
            headers = table_rows[0]
            rows = table_rows[1:]
            tables.append(
                TableData(
                    headers=headers,
                    rows=rows,
                    row_count=len(rows),
                    column_count=len(headers),
                )
            )
        return tables
