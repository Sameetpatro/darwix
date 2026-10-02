import re
from pathlib import Path
from typing import List, Union
from bs4 import BeautifulSoup

from q2.models.raw_document import RawDocument, TableData
from q2.parsers.base_parser import BaseParser
from app.logging_config import logger


class HTMLParser(BaseParser):
    """
    Extracts text, headings, sections, and structured tables from HTML documents.
    Strips noise (scripts, styles, navigation, cookies, footers) and preserves section hierarchy.
    """

    def can_parse(self, file_path: Union[str, Path]) -> bool:
        path = Path(file_path)
        return path.suffix.lower() in [".html", ".htm", ".xhtml"]

    def parse(self, file_path: Union[str, Path]) -> List[RawDocument]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"HTML file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")
            doc_title = soup.title.string.strip() if soup.title and soup.title.string else path.stem.replace("_", " ").title()

            # Remove unwanted boilerplate elements
            for tag in soup.find_all(["script", "style", "nav", "footer", "aside"]):
                tag.decompose()

            for banner in soup.find_all(class_=re.compile(r"cookie|banner|ad-|advertisement", re.IGNORECASE)):
                banner.decompose()

            documents: List[RawDocument] = []

            # 1. Extract HTML tables
            all_tables: List[TableData] = []
            for t_idx, table_tag in enumerate(soup.find_all("table")):
                headers = [th.get_text(strip=True) for th in table_tag.find_all("th")]
                rows = []
                for tr in table_tag.find_all("tr"):
                    tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                    if tds:
                        rows.append(tds)
                if headers or rows:
                    all_tables.append(
                        TableData(
                            headers=headers,
                            rows=rows,
                            row_count=len(rows),
                            column_count=len(headers) if headers else (len(rows[0]) if rows else 0),
                        )
                    )

            # 2. Section-based chunking on <section>, <article>, or <h2>/<h3> headers
            sections = soup.find_all(["section", "article"])
            if sections:
                for sec_idx, sec in enumerate(sections, 1):
                    # Section heading
                    h_tag = sec.find(["h1", "h2", "h3", "h4"])
                    sec_title = h_tag.get_text(strip=True) if h_tag else f"Section {sec_idx}"
                    text = sec.get_text(separator="\n", strip=True)

                    if len(text) < 15:
                        continue

                    # Tables within this section
                    sec_tables = []
                    for t in sec.find_all("table"):
                        headers = [th.get_text(strip=True) for th in t.find_all("th")]
                        rows = [[td.get_text(strip=True) for td in tr.find_all("td")] for tr in t.find_all("tr") if tr.find_all("td")]
                        sec_tables.append(TableData(headers=headers, rows=rows, row_count=len(rows), column_count=len(headers)))

                    documents.append(
                        RawDocument(
                            source_type="html",
                            source=path.name,
                            page=sec_idx,
                            section=sec_title,
                            title=f"{doc_title} — {sec_title}",
                            raw_content=text,
                            tables=sec_tables,
                            extraction_status="success",
                            metadata={
                                "html_tag": sec.name,
                                "character_count": len(text),
                                "word_count": len(text.split()),
                                "has_tables": len(sec_tables) > 0,
                            },
                        )
                    )

            # Fallback if no <section> tags exist: parse full body with headings
            if not documents:
                body_tag = soup.body or soup
                full_text = body_tag.get_text(separator="\n", strip=True)
                documents.append(
                    RawDocument(
                        source_type="html",
                        source=path.name,
                        page=1,
                        section="Main Body",
                        title=doc_title,
                        raw_content=full_text,
                        tables=all_tables,
                        extraction_status="success",
                        metadata={
                            "character_count": len(full_text),
                            "word_count": len(full_text.split()),
                            "has_tables": len(all_tables) > 0,
                        },
                    )
                )

            logger.info("[HTML-PARSER] Parsed '%s' into %d section documents", path.name, len(documents))
            return documents

        except Exception as exc:
            logger.error("[HTML-PARSER] Failed parsing HTML %s: %s", path.name, exc)
            return [
                RawDocument(
                    source_type="html",
                    source=path.name,
                    page=1,
                    title=path.stem.title(),
                    raw_content="",
                    extraction_status="failed",
                    metadata={"error": str(exc)},
                )
            ]
