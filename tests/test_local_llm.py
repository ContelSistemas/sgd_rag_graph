import pytest
from unittest.mock import patch, MagicMock
from src.generation.local_llm import LocalLLMClient

@patch("requests.post")
def test_local_llm_ollama(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Respuesta desde Ollama"}
    mock_post.return_value = mock_response

    client = LocalLLMClient(backend="ollama", base_url="http://localhost:11434")
    res = client.generate_response("Pregunta", [{"content": "Contexto", "metadata": {"title": "Doc"}}])
    assert res == "Respuesta desde Ollama"

@patch("requests.post")
def test_local_llm_llamacpp(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"content": "Respuesta desde Llama.cpp"}
    mock_post.return_value = mock_response

    client = LocalLLMClient(backend="llamacpp", base_url="http://localhost:8080", timeout=120)
    res = client.generate_response("Pregunta", [{"content": "Contexto", "metadata": {"title": "Doc"}}])
    assert res == "Respuesta desde Llama.cpp"
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs.get("timeout") == 120
