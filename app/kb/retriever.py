import math
import re
from typing import List, Optional, Tuple
from app.kb.models import KBChunk, SearchResult, RetrievalResponse
from app.kb.loader import load_knowledge_base, extract_keywords
from app.logging_config import logger

STRICT_FALLBACK_TEXT = "I don't have reliable information about that at the moment. I can connect you with a human representative if you'd like."
MIN_CONFIDENCE_THRESHOLD = 0.28


def _stem(word: str) -> str:
    w = word.lower()
    if len(w) > 4:
        if w.endswith("ing"):
            return w[:-3]
        if w.endswith("ed"):
            return w[:-2]
        if w.endswith("es"):
            return w[:-2]
        if w.endswith("s"):
            return w[:-1]
    return w


GENERIC_DOMAIN_WORDS = {"loan", "loans", "darwix", "business"}


class KnowledgeRetriever:
    def __init__(self, chunks: Optional[List[KBChunk]] = None):
        self.chunks = chunks if chunks is not None else load_knowledge_base()
        self._index = self._build_inverted_index()

    def _build_inverted_index(self):
        index = {}
        for chunk in self.chunks:
            tokens = set(chunk.keywords)
            for token in tokens:
                if token not in index:
                    index[token] = []
                index[token].append(chunk)
        return index

    def search(self, query: str, top_k: int = 3) -> List[SearchResult]:
        """
        Executes hybrid TF-IDF keyword, stemming & semantic ranking over knowledge chunks.
        Strictly prevents hallucination on out-of-scope topics.
        """
        query_tokens = extract_keywords(query)
        if not query_tokens:
            return []

        informative_tokens = [
            t for t in query_tokens 
            if t not in GENERIC_DOMAIN_WORDS and _stem(t) not in GENERIC_DOMAIN_WORDS
        ]

        scores = {}
        query_text_lower = query.lower()

        for chunk in self.chunks:
            score = 0.0
            chunk_text = f"{chunk.title} {chunk.content}".lower()

            # 1. Exact phrase boost
            if len(query_text_lower) > 4 and (query_text_lower in chunk_text or any(p in chunk_text for p in query_text_lower.split("?"))):
                score += 4.0

            # 2. Token overlap & IDF weight with stem matching
            matched_tokens = 0
            matched_informative = 0
            for token in query_tokens:
                token_stem = _stem(token)
                token_matched = (
                    token in chunk.keywords 
                    or token in chunk_text 
                    or any(token_stem == _stem(k) for k in chunk.keywords)
                    or (len(token_stem) >= 4 and token_stem in chunk_text)
                )

                if token_matched:
                    matched_tokens += 1
                    if token in informative_tokens or token_stem in informative_tokens:
                        matched_informative += 1
                    doc_freq = len(self._index.get(token, []))
                    idf = math.log((len(self.chunks) + 1.0) / (doc_freq + 1.0)) + 1.2

                    # Title or explicit Question match has significantly higher weight
                    if token in chunk.title.lower() or (len(token_stem) >= 4 and token_stem in chunk.title.lower()):
                        score += 4.5 * idf
                    elif "question:" in chunk_text and (token in chunk_text or token_stem in chunk_text):
                        score += 3.5 * idf
                    else:
                        score += 1.2 * idf

            # If the user query has non-generic informative terms, at least one MUST match
            if informative_tokens and matched_informative == 0:
                continue

            # Normalize by query length and doc length
            if matched_tokens > 0:
                coverage = (matched_informative / len(informative_tokens)) if informative_tokens else (matched_tokens / len(query_tokens))
                normalized_score = (score * coverage) / (math.sqrt(len(chunk.keywords) + 8.0))
                scores[chunk.chunk_id] = (chunk, normalized_score)

        if not scores:
            return []

        sorted_results = sorted(scores.values(), key=lambda x: x[1], reverse=True)[:top_k]

        # Normalize top score to a 0.0 - 1.0 range
        results = []
        for chunk, raw_score in sorted_results:
            normalized_prob = min(round(raw_score / 2.5, 3), 1.0)
            citation = f"Darwix KB: {chunk.source_file} ({chunk.chunk_id})"
            results.append(SearchResult(chunk=chunk, score=normalized_prob, citation=citation))

        return results

    def query_with_fallback(self, query: str) -> RetrievalResponse:
        """
        Retrieves answer from the knowledge base.
        STRICT REQUIREMENT: If information is not in the KB or confidence is below threshold,
        strictly returns: "I don't have reliable information about that at the moment. I can connect you with a human representative if you'd like."
        """
        results = self.search(query, top_k=1)

        if not results or results[0].score < MIN_CONFIDENCE_THRESHOLD:
            logger.info(
                "[KB-RAG] Query '%s' yielded no confident match (Score: %s). Invoking strict fallback.",
                query[:50],
                f"{results[0].score:.2f}" if results else "0.0",
            )
            return RetrievalResponse(
                has_match=False,
                query=query,
                confidence_score=results[0].score if results else 0.0,
                citation=None,
                voice_answer=STRICT_FALLBACK_TEXT,
            )

        top_result = results[0]
        chunk = top_result.chunk

        # Extract clean conversational answer from chunk
        clean_body = re.sub(r"[\*`_]", "", chunk.content)
        lines = [line.strip("- ") for line in clean_body.split("\n") if line.strip()]

        voice_clean = None
        # 1. Prioritize explicit Answer: line in FAQs
        for line in lines:
            if line.lower().startswith("answer:"):
                voice_clean = line.split(":", 1)[1].strip()
                break

        # 2. If chunk has a line matching query keywords, prioritize that line
        if not voice_clean:
            query_tokens = extract_keywords(query)
            topic_lines = [
                line for line in lines 
                if any(qt in line.lower() for qt in query_tokens if len(qt) > 3 and qt not in ["loan", "darwix"])
            ]
            if topic_lines:
                voice_clean = " ".join(topic_lines[:2])

        # 3. Otherwise pick top candidate descriptive bullet lines (excluding IDs/Questions)
        if not voice_clean:
            candidate_lines = []
            for line in lines:
                if not any(line.lower().startswith(p) for p in ["doc id:", "product id:", "policy id:", "question:"]):
                    candidate_lines.append(line)
            voice_clean = " ".join(candidate_lines[:2]) if candidate_lines else chunk.title

        logger.info(
            "[KB-RAG] Query '%s' matched chunk '%s' (Confidence: %.2f) | Citation: %s",
            query[:50],
            chunk.chunk_id,
            top_result.score,
            top_result.citation,
        )

        return RetrievalResponse(
            has_match=True,
            query=query,
            best_chunk=chunk,
            confidence_score=top_result.score,
            citation=top_result.citation,
            voice_answer=voice_clean,
        )


retriever = KnowledgeRetriever()
