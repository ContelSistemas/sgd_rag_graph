import requests
from typing import List, Dict, Any, Optional

class LocalLLMClient:
    """Cliente para conexión con LLMs locales (Ollama / Llama.cpp server) para síntesis RAG on-premise."""

    def __init__(self, backend: str = "ollama", base_url: str = "http://localhost:11434", model_name: str = "llama3", timeout: int = 300):
        self.backend = backend.lower()
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> str:
        context_text = "\n\n".join([
            f"--- Referencia [{c.get('metadata', {}).get('title', 'SGD')} | {c.get('metadata', {}).get('source_path', '')}] ---\n{c['content']}"
            for c in context_chunks
        ])

        prompt = f"""Eres un asistente experto para el Sistema de Gestión Documental (SGD). Responde a la pregunta del usuario basándote exclusivamente en el contexto provisto. Si la información no está en el contexto, indícalo claramente. Cita las referencias originales de los documentos utilizados.

Contexto:
{context_text}

Pregunta:
{query}

Respuesta:"""

        try:
            if self.backend == "llamacpp":
                response = requests.post(
                    f"{self.base_url}/completion",
                    json={
                        "prompt": prompt,
                        "n_predict": 512
                    },
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    return response.json().get("content", "No se pudo generar respuesta.")
                else:
                    return f"Error en API Llama.cpp (Status {response.status_code}): {response.text}"
            else:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    return response.json().get("response", "No se pudo generar respuesta.")
                else:
                    return f"Error en API Ollama (Status {response.status_code}): {response.text}"
        except Exception as e:
            return f"No se pudo conectar con el motor LLM local ({self.base_url} [{self.backend}]): {e}. Asegúrate de que el servicio está activo."
