import csv
from pathlib import Path
from typing import List, Union
from q2.models.raw_document import RawDocument, TableData
from q2.parsers.base_parser import BaseParser
from app.logging_config import logger


class TableParser(BaseParser):
    """
    Parses CSV, TSV, and tabular data files.
    Generates structured TableData and human/RAG-readable markdown table representations.
    """

    def can_parse(self, file_path: Union[str, Path]) -> bool:
        path = Path(file_path)
        return path.suffix.lower() in [".csv", ".tsv"]

    def parse(self, file_path: Union[str, Path]) -> List[RawDocument]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Table file not found: {path}")

        try:
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
            rows: List[List[str]] = []

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f, delimiter=delimiter)
                for r in reader:
                    if any(cell.strip() for cell in r):
                        rows.append([cell.strip() for cell in r])

            if not rows:
                return [
                    RawDocument(
                        source_type="table",
                        source=path.name,
                        title=path.stem.replace("_", " ").title(),
                        raw_content="",
                        extraction_status="failed",
                        metadata={"error": "Table file is empty"},
                    )
                ]

            headers = rows[0]
            data_rows = rows[1:]
            table_obj = TableData(
                headers=headers,
                rows=data_rows,
                row_count=len(data_rows),
                column_count=len(headers),
            )

            # Build markdown table representation
            md_lines = []
            title = path.stem.replace("_", " ").title()
            md_lines.append(f"# {title}\n")
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in data_rows:
                # Pad row if incomplete
                padded = row + [""] * (len(headers) - len(row))
                md_lines.append("| " + " | ".join(padded[:len(headers)]) + " |")

            # Also generate row-by-row natural language descriptions for optimal hybrid RAG retrieval
            md_lines.append("\n## Table Entries Detail:\n")
            for idx, r in enumerate(data_rows, 1):
                item_desc = ", ".join(f"{h}: {val}" for h, val in zip(headers, r) if val)
                md_lines.append(f"- Entry {idx}: {item_desc}")

            text_content = "\n".join(md_lines)

            doc = RawDocument(
                source_type="csv",
                source=path.name,
                page=1,
                section="Table Data",
                title=title,
                raw_content=text_content,
                tables=[table_obj],
                extraction_status="success",
                metadata={
                    "row_count": len(data_rows),
                    "column_count": len(headers),
                    "headers": headers,
                    "delimiter": delimiter,
                },
            )

            logger.info("[TABLE-PARSER] Parsed '%s' with %d rows and %d columns", path.name, len(data_rows), len(headers))
            return [doc]

        except Exception as exc:
            logger.error("[TABLE-PARSER] Failed parsing table %s: %s", path.name, exc)
            return [
                RawDocument(
                    source_type="table",
                    source=path.name,
                    title=path.stem.title(),
                    raw_content="",
                    extraction_status="failed",
                    metadata={"error": str(exc)},
                )
            ]
