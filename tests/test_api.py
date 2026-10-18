import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "Graph RAG Base del Conocimiento API"}

@patch("src.api.main.KnowledgeBaseIndexer")
def test_index_endpoint(mock_indexer_cls):
    mock_indexer = MagicMock()
    mock_indexer.run_indexing.return_value = 10
    mock_indexer.graph_manager = MagicMock()
    mock_indexer_cls.return_value = mock_indexer

    response = client.post("/index")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_chunks"] == 10

@patch("src.api.main.HybridRetriever.retrieve")
@patch("src.generation.local_llm.LocalLLMClient.generate_response")
def test_query_endpoint(mock_generate, mock_retrieve):
    mock_retrieve.return_value = [
        {"type": "vector_hit", "chunk_id": "c1", "content": "Contenido test", "metadata": {"title": "Doc"}, "distance": 0.1}
    ]
    mock_generate.return_value = "Respuesta generada por API"

    response = client.post("/query", json={
        "query": "¿Cuál es la VLAN?",
        "backend": "llamacpp",
        "base_url": "http://localhost:8080",
        "timeout": 120
    })

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "¿Cuál es la VLAN?"
    assert data["response"] == "Respuesta generada por API"
    assert len(data["contexts"]) == 1
