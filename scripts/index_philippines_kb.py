import sys
from pathlib import Path

# Ensure root workspace is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from q2.parsers.text_parser import TextParser
from q2.graph.cleaning_graph import clean_and_structure_document
from q2.retrieval.hybrid_search import HybridSearchEngine
from q2.storage.chunk_store import chunk_store
from app.logging_config import logger

def main():
    logger.info("Starting ingestion, cleaning, and indexing for Philippines Life Insurance knowledge...")
    parser = TextParser()
    
    ph_files = [
        BASE_DIR / "data/raw/ph_life_insurance_handbook.md",
        BASE_DIR / "data/raw/ph_insurance_faqs_objections.md",
    ]
    
    all_records = []
    for fpath in ph_files:
        if not fpath.exists():
            logger.error(f"File not found: {fpath}")
            continue
            
        raw_docs = parser.parse(fpath)
        logger.info(f"Parsed {len(raw_docs)} raw sections from {fpath.name}")
        
        for raw_doc in raw_docs:
            res = clean_and_structure_document(raw_doc)
            rec = res.get("knowledge_record")
            if rec:
                if "handbook" in fpath.name.lower():
                    rec.category = "policy"
                    rec.product = "Philippines Life Insurance"
                else:
                    rec.category = "faq"
                    rec.product = "Philippines Life Insurance"
                all_records.append(rec)
                
    logger.info(f"Cleaned and structured {len(all_records)} KnowledgeRecords.")
    
    # Index via HybridSearchEngine
    hybrid_engine = HybridSearchEngine()
    indexed_chunks = hybrid_engine.index_records(all_records)
    logger.info(f"Successfully indexed {len(indexed_chunks)} chunks for Philippines Life Insurance!")

    # Verify retrieval
    query = "What happens if a policy lapses?"
    hits = hybrid_engine.search(query=query, top_k=2)
    logger.info(f"Verification query: '{query}' -> Top hit: '{hits[0].chunk.title}' (score: {hits[0].fused_score:.4f})")
    for i, h in enumerate(hits):
        logger.info(f"  Hit {i+1}: {h.chunk.title} [fused: {h.fused_score:.4f}, dense: {h.dense_score:.4f}, sparse: {h.sparse_score:.4f}]")
    
if __name__ == "__main__":
    main()
