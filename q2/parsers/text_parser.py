import re
from pathlib import Path
from typing import List, Union
from q2.models.raw_document import RawDocument
from q2.parsers.base_parser import BaseParser
from app.logging_config import logger


class TextParser(BaseParser):
    """
    Parses Plain Text (.txt) and Markdown (.md) documents.
    Detects section headers (#, ##, Section X:) and extracts structured sections.
    """

    def can_parse(self, file_path: Union[str, Path]) -> bool:
        path = Path(file_path)
        return path.suffix.lower() in [".txt", ".md", ".text", ".rst"]

    def parse(self, file_path: Union[str, Path]) -> List[RawDocument]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            clean_text = content.strip()
            if not clean_text:
                return [
                    RawDocument(
                        source_type="text",
                        source=path.name,
                        title=path.stem.replace("_", " ").title(),
                        raw_content="",
                        extraction_status="failed",
                        metadata={"error": "Text file is empty"},
                    )
                ]

            # Detect sections by H2 or H1 headers (## or #) or 'Section \d+:'
            raw_sections = re.split(r"\n(?=#{1,3}\s+|Section\s+\d+:)", content)
            documents: List[RawDocument] = []

            for idx, sec in enumerate(raw_sections, 1):
                sec_clean = sec.strip()
                if not sec_clean:
                    continue

                lines = sec_clean.split("\n")
                first_line = lines[0].strip("# \t")
                sec_title = first_line if len(first_line) < 80 else f"Section {idx}"
                body = "\n".join(lines[1:]).strip() if len(lines) > 1 else sec_clean

                documents.append(
                    RawDocument(
                        source_type="text",
                        source=path.name,
                        page=idx,
                        section=sec_title,
                        title=f"{path.stem.replace('_', ' ').title()} — {sec_title}",
                        raw_content=sec_clean,
                        extraction_status="success",
                        metadata={
                            "section_index": idx,
                            "character_count": len(sec_clean),
                            "word_count": len(sec_clean.split()),
                        },
                    )
                )

            if not documents:
                documents.append(
                    RawDocument(
                        source_type="text",
                        source=path.name,
                        page=1,
                        section="Full Document",
                        title=path.stem.replace("_", " ").title(),
                        raw_content=clean_text,
                        extraction_status="success",
                        metadata={"word_count": len(clean_text.split())},
                    )
                )

            logger.info("[TEXT-PARSER] Parsed '%s' into %d section documents", path.name, len(documents))
            return documents

        except Exception as exc:
            logger.error("[TEXT-PARSER] Failed parsing text %s: %s", path.name, exc)
            return [
                RawDocument(
                    source_type="text",
                    source=path.name,
                    title=path.stem.title(),
                    raw_content="",
                    extraction_status="failed",
                    metadata={"error": str(exc)},
                )
            ]
