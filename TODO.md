# TODO.md

## Objetivo actual
Sistema Graph RAG para SGD (v0.9.1) estable tras Sprint 1 y Sprint 1.1: expansión de grafo con contenido real de chunks, cliente LLM con reintentos exponenciales, configuración centralizada en `src/config/settings.py`, validación de parámetros en la API, archivo `.env` para configuración por entorno, y nueva TUI Textual como alternativa a Streamlit.

## Tareas pendientes
- Reindexar documentos: colocar nuevos `.md` en `data/` y ejecutar `POST /index` o `python3 run_demo.py`.
- Validar persistencia del grafo en `data/knowledge_graph.json` tras reindexación.
- Comprobar acceso de escritura a `data/vectorstore/` para ChromaDB.
- Documentar en `docs/` el uso de `PLAN.md`/`TODO.md` para seguimiento de sprints.
- Probar LLM más ligero: Qwen2.5-3B-Instruct Q4_K_M (Qwen2.5-7B va muy lento en dev). Alternativa recordatorio: Llama3.2-3B-Instruct.

## Tareas completadas (esta sesión)
- Crear `.env` con valores por defecto (basado en `src/config/settings.py`)
- Crear `.env.example` como plantilla de variables de entorno
- `.env` ya estaba en `.gitignore` (línea 6)
- Modificar `src/generation/local_llm.py` para leer valores por defecto de `.env` vía `get_settings()`
- Crear `src/ui/tui.py` — nueva TUI con Textual que reusa `LocalLLMClient`, `HybridRetriever`, `KnowledgeGraphManager`, `VectorStoreManager`, `SGDIndexer`
- Agregar `textual>=0.86.0` a `requirements.txt`
- Actualizar `README.md`: sección de configuración `.env` y sección de TUI Textual
- Actualizar `release.md`: nueva versión v0.9.1-alpha con todas las mejoras
- Vaciar `data/knowledge_graph.json` y borrar `.md` de `data/` y `data/vectorstore/` para empezar pruebas desde cero
- Arreglar error `KeyError: 'edges'` en `knowledge_graph.json` (usar `"edges": []` no `"links"`)
- Arreglar error TUI `AttributeError: 'GraphRAGTUI' object has no attribute 'chat_input'` (uso de `query_one` en lugar de acceso directo)
- Arreglar error TUI `TypeError: _query_worker() missing 1 required positional argument` (uso de `functools.partial`)

## Archivos modificados (esta sesión)
- `.env` — variables de entorno por defecto (valores de `src/config/settings.py`)
- `.env.example` — plantilla de variables de entorno
- `src/generation/local_llm.py` — constructor lee valores por defecto de `.env` vía `get_settings()`
- `src/ui/tui.py` — nueva TUI con Textual
- `requirements.txt` — agregada dependencia `textual>=0.86.0`
- `README.md` — secciones de `.env` y TUI Textual
- `release.md` — nueva versión v0.9.1-alpha
- `data/knowledge_graph.json` — vaciado (formato correcto con `"edges"`)
- `data/` — eliminados `.md` y `data/vectorstore/` para reindexación limpia

## Archivos modificados (Sprint 1, v0.9.0)
- `src/config/settings.py` — configuración centralizada con pydantic-settings (lee `.env` automáticamente)
- `src/generation/local_llm.py` — reintentos exponenciales (`max_retries=3`, `base_delay=1s`)
- `src/retrieval/hybrid.py` — expansión de grafo con contenido real de chunks
- `src/api/main.py` — validación de timeout (10-600s), top_k (1-20), graph_radius (0-5), backend enum
- `AGENTS.md`, `README.md`, `release.md` — documentación actualizada

## Errores detectados
- Ninguno reportado actualmente. Los tests requieren `PYTHONPATH=.` y no necesitan servicios externos (mocks para LLM/vector store).

## Siguiente paso que debe ejecutar
```bash
PYTHONPATH=. pytest tests/ -v
```
