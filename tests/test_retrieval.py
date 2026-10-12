import pytest
from src.retrieval.hybrid import HybridRetriever
from src.graph.manager import KnowledgeGraphManager

class MockVectorStore:
    def similarity_search(self, query, top_k=5):
        return [{
            "chunk_id": "chunk1",
            "content": "Contenido de prueba sobre VLANs.",
            "metadata": {"source_path": "test.md", "title": "Doc 1"},
            "distance": 0.1
        }]

def test_hybrid_retriever():
    vs = MockVectorStore()
    gm = KnowledgeGraphManager()
    gm.add_document_node("Doc 1", {"source_path": "test.md"})
    gm.add_document_node("Doc 2", {"source_path": "test2.md"})
    gm.add_relation("Doc 1", "Doc 2", relation_type="wiki_link")

    retriever = HybridRetriever(vector_store=vs, graph_manager=gm)
    results = retriever.retrieve("VLANs", top_k=1)

    assert len(results) >= 1
    assert results[0]["chunk_id"] == "chunk1"
