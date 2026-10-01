import os
import re
from pathlib import Path
from typing import List, Optional
from app.kb.models import KBChunk
from app.logging_config import logger

KB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "knowledge_base"


def extract_keywords(text: str) -> List[str]:
    """Extracts alphanumeric words for search indexing."""
    words = re.findall(r"\b[a-zA-Z0-9-]{3,}\b", text.lower())
    stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "are", "have", "you",
        "your", "can", "will", "what", "how", "all", "our", "not", "any", "been",
        "when", "where", "which", "about", "into", "their", "them", "then", "there",
        "tell", "program", "please", "could", "would", "like", "know", "information",
        "details", "help", "much", "many", "get", "want", "need", "buy", "use", "using",
        "take", "make", "also", "just", "does", "did"
    }
    return [w for w in set(words) if w not in stopwords]


def load_knowledge_base(kb_dir: Optional[Path] = None) -> List[KBChunk]:
    """Loads and chunks all markdown documents from data/knowledge_base/."""
    target_dir = kb_dir or KB_DIR
    chunks: List[KBChunk] = []

    if not target_dir.exists():
        logger.warning("[KB] Knowledge base directory %s does not exist", target_dir)
        return chunks

    for file_path in sorted(target_dir.glob("*.md")):
        category = file_path.stem
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Split on H2 headers (## )
            raw_sections = re.split(r"\n(?=##\s+)", content)
            for sec in raw_sections:
                clean_sec = sec.strip()
                if not clean_sec or clean_sec.startswith("# "):
                    continue

                lines = clean_sec.split("\n")
                header_line = lines[0].replace("##", "").strip()

                # Extract Doc ID or Product ID if specified
                id_match = re.search(r"\*\*(?:Doc ID|Product ID|Policy ID)\*\*:\s*`?([a-zA-Z0-9_-]+)`?", clean_sec)
                chunk_id = id_match.group(1) if id_match else f"{category}-{re.sub(r'[^a-zA-Z0-9]', '-', header_line).lower()[:24]}"

                # Body text (remove title line)
                body = "\n".join(lines[1:]).strip()

                chunk = KBChunk(
                    chunk_id=chunk_id,
                    title=header_line,
                    category=category,
                    source_file=file_path.name,
                    content=body,
                    keywords=extract_keywords(f"{header_line} {body}"),
                )
                chunks.append(chunk)

        except Exception as exc:
            logger.error("[KB] Failed loading KB file %s: %s", file_path.name, exc)

    logger.info("[KB] Successfully loaded %d knowledge chunks from %s", len(chunks), target_dir)
    return chunks
