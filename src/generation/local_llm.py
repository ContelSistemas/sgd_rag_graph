import requests
import time
from typing import List, Dict, Any, Optional

from src.config import get_settings

class LocalLLMClient:
    """Cliente para conexión con LLMs locales (Ollama / Llama.cpp server) para síntesis RAG on-premise."""

    def __init__(self, backend: Optional[str] = None, base_url: Optional[str] = None, model_name: Optional[str] = None, timeout: Optional[int] = None, max_retries: Optional[int] = None, base_delay: Optional[float] = None):
        settings = get_settings()
        self.backend = (backend or settings.llm_backend).lower()
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model_name = model_name or settings.llm_model_name
        self.timeout = timeout if timeout is not None else settings.llm_timeout
        self.max_retries = max_retries if max_retries is not None else settings.llm_max_retries
        self.base_delay = base_delay if base_delay is not None else settings.llm_base_delay

    def _build_prompt(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        context_text = "\n\n".join([
            f"--- Referencia [{c.get('metadata', {}).get('title', 'SGD')} | {c.get('metadata', {}).get('source_path', '')}] ---\n{c['content']}"
            for c in context_chunks
        ])
        return f"""Eres un asistente experto para el Sistema de Gestión Documental (SGD). Responde a la pregunta del usuario basándote exclusivamente en el contexto provisto. Si la información no está en el contexto, indícalo claramente. Cita las referencias originales de los documentos utilizados.

Contexto:
{context_text}

Pregunta:
{query}

Respuesta:"""

    def _request_with_retry(self, url: str, payload: Dict[str, Any]) -> requests.Response:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    return response
                if response.status_code >= 500:
                    last_error = f"Server error {response.status_code}: {response.text}"
                else:
                    return response
            except requests.Timeout:
                last_error = f"Timeout after {self.timeout}s"
            except requests.ConnectionError as e:
                last_error = f"Connection error: {e}"
            except Exception as e:
                last_error = f"Unexpected error: {e}"

            if attempt < self.max_retries - 1:
                delay = self.base_delay * (2 ** attempt)
                time.sleep(delay)
        
        raise requests.RequestException(f"Failed after {self.max_retries} retries. Last error: {last_error}")

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        prompt = self._build_prompt(query, context_chunks)

        try:
            if self.backend == "llamacpp":
                response = self._request_with_retry(
                    f"{self.base_url}/completion",
                    {"prompt": prompt, "n_predict": 512}
                )
                return response.json().get("content", "No se pudo generar respuesta.")
            else:
                response = self._request_with_retry(
                    f"{self.base_url}/api/generate",
                    {"model": self.model_name, "prompt": prompt, "stream": False}
                )
                return response.json().get("response", "No se pudo generar respuesta.")
        except requests.RequestException as e:
            return f"No se pudo conectar con el motor LLM local ({self.base_url} [{self.backend}]): {e}. Asegúrate de que el servicio está activo."
