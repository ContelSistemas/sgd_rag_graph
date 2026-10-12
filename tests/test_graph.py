import pytest
from src.graph.manager import KnowledgeGraphManager

def test_knowledge_graph_operations():
    gm = KnowledgeGraphManager()
    
    gm.add_document_node("doc1", {"title": "Doc 1"})
    gm.add_document_node("doc2", {"title": "Doc 2"})
    gm.add_document_node("doc3", {"title": "Doc 3"})
    
    gm.add_relation("doc1", "doc2", relation_type="wiki_link")
    gm.add_relation("doc2", "doc3", relation_type="wiki_link")
    
    neighbors_doc1 = gm.get_neighbors("doc1", radius=1)
    assert "doc2" in neighbors_doc1
    assert "doc3" not in neighbors_doc1
    
    neighbors_doc1_r2 = gm.get_neighbors("doc1", radius=2)
    assert "doc2" in neighbors_doc1_r2
    assert "doc3" in neighbors_doc1_r2
    
    subgraph_ctx = gm.get_subgraph_context("doc1", radius=1)
    assert len(subgraph_ctx["nodes"]) == 2
    assert len(subgraph_ctx["edges"]) == 1
