import pytest
from src.vectorstore.store import VectorStoreManager, HAS_CHROMADB, HAS_SENTENCE_TRANSFORMERS

@pytest.mark.skipif(not (HAS_CHROMADB and HAS_SENTENCE_TRANSFORMERS), reason="ChromaDB o SentenceTransformers no instalados")
def test_vector_store_mock():
    store = VectorStoreManager(persist_directory="data/test_vectorstore")
    
    chunks = [{
        "chunk_id": "test_chunk_1",
        "source_path": "test.md",
        "header_path": "Test Doc > Intro",
        "content": "Este es un documento sobre redes y VLANs en el sistema de gestión documental.",
        "frontmatter": {"title": "Test Doc"},
        "wiki_links": []
    }]
    
    store.add_chunks(chunks)
    results = store.similarity_search("VLANs", top_k=1)
    
    assert len(results) > 0
    assert results[0]["chunk_id"] == "test_chunk_1"
