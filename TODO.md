# TODO.md

## Objetivo actual
Sistema Graph RAG para Base del Conocimiento (v0.9.5) estable tras Sprint 1, 1.1, 1.2, 1.3, Sprint 1.4 y Sprint 1.5: búsqueda por palabra clave para términos técnicos, modelo de embeddings actualizado a paraphrase-multilingual-mpnet-base-v2, default_top_k=20, chunker corregido, retriever relajado, prompt del LLM mejorado para modelo 3B, parámetros optimizados para 3B.

## Tareas pendientes (backlog - nuevas fuentes de documento)
- ✅ **Word (.docx):** Implementado en Sprint 1.3 con `src/ingestion/docx_to_md.py` (`python-docx`).
- **PDF:** Pendiente — integrar con `pypdf`/`pdfplumber` y OCR (`pytesseract`/`easyocr`) para PDF escaneados.
  - Adaptar el pipeline actual para aceptar texto extraído de PDF y generar chunks con frontmatter sintético.
  - Añadir endpoint o comando CLI para indexar archivos .pdf desde `data/` o ruta configurada.

## Tareas pendientes
- Reindexar documentos: colocar nuevos `.md` en `data/` y ejecutar `POST /index` o `python3 run_demo.py` (el indexer ahora limpia chunks previos antes de insertar).
- Validar persistencia del grafo en `data/knowledge_graph.json` tras reindexación.
- Comprobar acceso de escritura a `data/vectorstore/` para ChromaDB.
- Documentar en `docs/` el uso de `PLAN.md`/`TODO.md` para seguimiento de sprints.
- ✅ **Probar LLM más grande:** Probado Llama3.2-3B-Instruct Q4_K_M en sprint 1.4. Mejora en construcción de respuestas pero requiere parámetros y prompt ajustados para extraer información del contexto.
- Considerar visualización interactiva del grafo en Streamlit (pyvis / streamlit-agraph) — ver roadmap en `release.md`.

## Tareas completadas (esta sesión - Sprint 1.4 v0.9.4)
- Chunker corregido: encabezados `###` se agrupan con su sección padre `##` (`src/ingestion/chunker.py`)
- Retriever relajado: eliminado filtro restrictivo por `source_path`; `MAX_CONTEXTS_PER_SOURCE=5`; usa `settings.default_top_k` (`src/retrieval/hybrid.py`)
- Prompt del LLM mejorado para modelo 3B; post-procesamiento filtra bloques "Pregunta/Respuesta/Contexto"; secuencias `stop` para llama.cpp (`src/generation/local_llm.py`)
- Parámetros optimizados para 3B: `temperature=0.3`, `n_predict=384`, `ctx_size=4096`, `default_top_k=10` (`src/config/settings.py`)
- Chat CLI con `top_k=50` para más candidatos de ChromaDB (`run_chat.py`)
- Documentación: `release.md` (v0.9.4), `TODO.md` (este archivo)

## Tareas completadas (esta sesión - Sprint 1.5 v0.9.5)
- Búsqueda por palabra clave (`keyword_search`) en `src/vectorstore/store.py`: usa `where_document={"$contains": kw}` de ChromaDB para encontrar chunks con términos técnicos exactos (ej. `XGE1/0/25`)
- Integración de `keyword_search` en `HybridRetriever.retrieve()`: ejecuta keyword antes de búsqueda vectorial y prioriza hits de keyword; extrae palabras clave automáticamente vía regex (`src/retrieval/hybrid.py`)
- Modelo de embeddings actualizado a `paraphrase-multilingual-mpnet-base-v2` (768 dims) en `src/config/settings.py`, `.env` y `.env.example`
- `default_top_k` incrementado de 4 a 20 en `src/config/settings.py` y `.env`
- `MAX_CONTEXTS_PER_SOURCE` incrementado de 5 a 10 en `src/retrieval/hybrid.py`
- Validación de recuperación: consulta "¿Qué pasó con el puerto XGE1/0/25 del switch en PQS?" ahora recupera el chunk relevante y el LLM responde correctamente
- Documentación: `release.md` (v0.9.5), `TODO.md`, `README.md`, `AGENTS.md`

## Tareas completadas (esta sesión - Sprint 1.3 v0.9.3)
- Conversor Word → Markdown (`src/ingestion/docx_to_md.py`): extrae texto de .docx con `python-docx`, genera frontmatter YAML automático, preserva encabezados, negritas y enlaces wiki `[[...]]`.
- Pipeline de ingesta Word/PDF integrado: los .md convertidos entran al pipeline estándar (Parser → Chunker → Grafo → VectorStore).
- Frontmatter sintético para documentos importados: `id`, `title`, `categoria: importado`, `autor: Sistema Base del Conocimiento`, `creado`, `tags: ["#importado", "#word"]`, `Link to: null`.
- Prueba real con `data/contrato msp.docx` → `data/contrato msp.md` → indexado (89 chunks totales, nodo `contrato_msp` en el grafo).
- Pruebas unitarias: `11 passed` (`PYTHONPATH=. pytest tests/ -q`)
- Documentación: `release.md` (v0.9.3), `README.md` (sprint 1.3 + sección ingesta Word/PDF), `TODO.md` (este archivo)

## Tareas completadas (esta sesión - Sprint 1.2 v0.9.2)
- Modelo LLM ligero por defecto: `llm_model_name` = `gemma-3-1b-it` en `src/config/settings.py`
- Parámetros de generación reducidos: `llm_n_predict=256`, `llm_temperature=0.3`, `llm_ctx_size=2048`
- `default_top_k` bajó de 4 a 3; `MAX_CONTEXTS = 6` en `HybridRetriever`
- Dedup robusto en `similarity_search` (`src/vectorstore/store.py`): descarta chunks con hash de contenido duplicado
- Nuevo `delete_chunks_by_source(source_path)` en `src/vectorstore/store.py`
- `HybridRetriever` dedup por `chunk_id` y hash de contenido entre vector + grafo (`src/retrieval/hybrid.py`)
- Indexer llama a `delete_chunks_by_source` antes de `add_chunks` (`src/vectorstore/indexer.py`)
- Prompt optimizado para modelo 1B: contexto truncado, instrucciones anti-copia (`src/generation/local_llm.py`)
- `LocalLLMClient` acepta `n_predict` y `temperature`; API y Streamlit los pasan
- `src/ui/tui.py` usa `settings.default_top_k` por defecto
- Documento de ejemplo `data/documento_ejemplo.md` para pruebas (frontmatter, enlaces wiki, texto)
- Pruebas unitarias: `11 passed` (`PYTHONPATH=. pytest tests/ -q`)
- Documentación: `release.md` (v0.9.2), `README.md` (sprint 1.1/1.2 + sección hardware limitado), `TODO.md` (este archivo)

## Tareas completadas (Sprint 1.1 v0.9.1)
- Crear `.env` con valores por defecto (basado en `src/config/settings.py`)
- Crear `.env.example` como plantilla de variables de entorno
- `.env` ya estaba en `.gitignore` (línea 6)
- Modificar `src/generation/local_llm.py` para leer valores por defecto de `.env` vía `get_settings()`
- Crear `src/ui/tui.py` — nueva TUI con Textual que reusa `LocalLLMClient`, `HybridRetriever`, `KnowledgeGraphManager`, `VectorStoreManager`, `KnowledgeBaseIndexer`
- Agregar `textual>=0.86.0` a `requirements.txt`
- Actualizar `README.md`: sección de configuración `.env` y sección de TUI Textual
- Actualizar `release.md`: nueva versión v0.9.1-alpha con todas las mejoras
- Vaciar `data/knowledge_graph.json` y borrar `.md` de `data/` y `data/vectorstore/` para empezar pruebas desde cero
- Arreglar error `KeyError: 'edges'` en `knowledge_graph.json` (usar `"edges": []` no `"links"`)
- Arreglar error TUI `AttributeError: 'GraphRAGTUI' object has no attribute 'chat_input'` (uso de `query_one` en lugar de acceso directo)
- Arreglar error TUI `TypeError: _query_worker() missing 1 required positional argument` (uso de `functools.partial`)

## Tareas completadas (Sprint 1 v0.9.0)
- `src/config/settings.py` — configuración centralizada con pydantic-settings (lee `.env` automáticamente)
- `src/generation/local_llm.py` — reintentos exponenciales (`max_retries=3`, `base_delay=1s`)
- `src/retrieval/hybrid.py` — expansión de grafo con contenido real de chunks
- `src/api/main.py` — validación de timeout (10-600s), top_k (1-20), graph_radius (0-5), backend enum
- `AGENTS.md`, `README.md`, `release.md` — documentación actualizada

## Archivos modificados (Sprint 1.3 v0.9.3)
- `src/ingestion/docx_to_md.py` — nuevo: conversor Word → Markdown con frontmatter YAML
- `release.md`, `README.md`, `TODO.md` — documentación v0.9.3

## Archivos modificados (Sprint 1.2 v0.9.2)
- `src/config/settings.py` — modelo 1B, n_predict, temperature, ctx_size, top_k=3
- `src/generation/local_llm.py` — prompt anti-copia, n_predict/temperature, truncado contexto
- `src/vectorstore/store.py` — dedup por hash, delete_chunks_by_source
- `src/vectorstore/indexer.py` — limpia chunks previos antes de add_chunks
- `src/retrieval/hybrid.py` — dedup cruzado vector+grafo, MAX_CONTEXTS=6
- `src/api/main.py` — pasa n_predict y temperature al LLM
- `src/ui/app.py` — pasa n_predict y temperature al LLM
- `src/ui/tui.py` — top_k por defecto desde settings
- `data/documento_ejemplo.md` — nuevo documento tipo para pruebas
- `release.md`, `README.md`, `TODO.md` — documentación

## Errores detectados
- Ninguno reportado actualmente. Los tests requieren `PYTHONPATH=.` y no necesitan servicios externos (mocks para LLM/vector store).

## Siguiente paso que debe ejecutar
```bash
# 1. Lanzar servidor LLM (recomendado 3B para sprint 1.4)
llama-server -hf bartowski/Llama-3.2-3B-Instruct-GGUF:Q4_K_M -c 4096 --port 8080

# 2. Limpiar índice anterior (requerido por cambio en el chunker)
rm -rf data/vectorstore data/knowledge_graph.json

# 3. Reindexar documentos (limpia duplicados previos)
POST /index   # vía API, Streamlit o python3 run_demo.py

# 4. Ejecutar pruebas
PYTHONPATH=. pytest tests/ -v

# 5. Chat CLI
python3 run_chat.py llamacpp http://localhost:8080
```
