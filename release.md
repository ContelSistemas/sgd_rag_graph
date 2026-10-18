# Notas de Versión - Graph RAG para Base del Conocimiento

## v0.9.5-alpha (Sprint 1.5: Búsqueda por Palabra Clave para Términos Técnicos)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se agrega **búsqueda por palabra clave** (`keyword_search`) como complemento a la búsqueda semántica híbrida, resolviendo el problema de que embeddings no recuperaban términos técnicos específicos (ej. `XGE1/0/25`) aunque el chunk existiera en el índice. Se actualiza el modelo de embeddings a `paraphrase-multilingual-mpnet-base-v2` (768 dims) y se incrementa `default_top_k` a 20 para recuperar más candidatos antes del filtrado por deduplicación.

### ✨ Novedades y Componentes Implementados
- **Búsqueda por palabra clave (`src/vectorstore/store.py`):** Nuevo método `keyword_search(keywords, top_k)` que utiliza `where_document={"$contains": kw}` de ChromaDB para encontrar chunks cuyo contenido contenga términos técnicos exactos (puertos, IPs, VLANs, IDs de switches). Hace búsquedas separadas por cada palabra clave para evitar que ChromaDB truncé resultados con `$or`.
- **Integración en Hybrid Retriever (`src/retrieval/hybrid.py`):** `retrieve()` ahora ejecuta `keyword_search` antes de la búsqueda vectorial y prioriza los hits de keyword (más precisos para términos técnicos). Extrae automáticamente palabras clave técnicas de la consulta mediante regex (patrones mayúsculas + palabras de 4+ caracteres excluyendo stopwords en español).
- **Modelo de embeddings actualizado:** `paraphrase-multilingual-mpnet-base-v2` (768 dims, mejor para español y términos técnicos) reemplazando a `all-MiniLM-L6-v2` (384 dims). Requiere reindexar (`rm -rf data/vectorstore`).
- **Parámetros ajustados (`src/config/settings.py`, `.env`):** `default_top_k=20` (era 4), `EMBEDDING_MODEL=paraphrase-multilingual-mpnet-base-v2`.
- **Validación de recuperación:** Probado con consulta "¿Qué pasó con el puerto XGE1/0/25 del switch en PQS?" — el chunk `heading-33-2025-01-22` ahora se recupera correctamente y el LLM puede responder.

### 🔧 Flujo de Uso
```bash
# 1. Limpiar índice anterior (requerido por cambio de modelo de embeddings)
rm -rf data/vectorstore

# 2. Reindexar documentos con nuevo modelo de embeddings
python3 run_demo.py   # o POST /index vía API/Streamlit

# 3. Probar consulta con término técnico
python3 run_chat.py llamacpp http://localhost:8080
# > ¿Qué pasó con el puerto XGE1/0/25 del switch en PQS?
```

### ⚠️ Nota Importante
El cambio de modelo de embeddings invalida los vectores previamente indexados en ChromaDB (dimensiones diferentes: 768 vs 384). Es **obligatorio** reindexar (`rm -rf data/vectorstore` + `python3 run_demo.py`) antes de usar esta versión.

---

## v0.9.4-alpha (Sprint 1.4: Mejora de Recuperación y Generación con Modelo 3B)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se completan mejoras en el motor de recuperación híbrida y la capa de generación LLM para trabajar con modelos más grandes (3B). Se corrige el chunker para que encabezados de nivel inferior (`###`) no generen chunks huérfanos, se relajan los filtros de deduplicación que impedían recuperar múltiples chunks del mismo documento, y se ajusta el prompt y parámetros del cliente LLM para que el modelo 3B extraiga información del contexto en lugar de responder "no hay información".

### ✨ Novedades y Componentes Implementados
- **Chunker corregido (`src/ingestion/chunker.py`):** Los encabezados `###` ahora se agrupan con su sección padre `##` en lugar de crear chunks separados huérfanos. El chunker busca el siguiente encabezado del mismo nivel o superior para delimitar el fin de cada chunk.
- **Retriever relajado (`src/retrieval/hybrid.py`):** Eliminado el filtro `seen_source_paths` que descartaba todos los chunks posteriores del mismo documento. Ahora permite hasta `MAX_CONTEXTS_PER_SOURCE=5` chunks por fuente y usa `settings.default_top_k` como límite total en lugar de un valor hardcodeado.
- **Prompt del LLM mejorado (`src/generation/local_llm.py`):** Instrucciones más directivas para leer TODO el contexto y buscar fechas/eventos. Post-procesamiento que filtra bloques "Pregunta:", "Respuesta:", "Contexto:" generados por el modelo. Añadidas secuencias `stop` para llama.cpp. Eliminado print de depuración temporal.
- **Parámetros optimizados para modelo 3B (`src/config/settings.py`):** `llm_temperature=0.3`, `llm_n_predict=384`, `llm_ctx_size=4096`, `default_top_k=10`.
- **Chat CLI con mayor `top_k` (`run_chat.py`):** Búsqueda vectorial con `top_k=50` para obtener más candidatos antes de filtrar.

### 🔧 Flujo de Uso
```bash
# 1. Limpiar índice anterior (requerido por cambio en el chunker)
rm -rf data/vectorstore data/knowledge_graph.json

# 2. Reindexar documentos
python3 run_demo.py   # o POST /index vía API/Streamlit

# 3. Probar consulta con modelo 3B
python3 run_chat.py llamacpp http://localhost:8080
```

### ⚠️ Nota Importante
El cambio en el chunker invalida los chunks previamente indexados en ChromaDB. Es **obligatorio** reindexar (`rm -rf data/vectorstore data/knowledge_graph.json` + `python3 run_demo.py`) antes de usar esta versión.

---

## v0.9.3-alpha (Sprint 1.3: Ingesta de Documentos Word y PDF)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se completa el **Sprint 1.3** con la capacidad de alimentar el grafo de conocimiento y la base vectorial a partir de documentos Word (.docx) y PDF, convirtiéndolos a Markdown con frontmatter YAML antes de indexarlos. Permite incorporar documentación existente de la Base del Conocimiento sin tener que reescribirla manualmente en Markdown.

### ✨ Novedades y Componentes Implementados
- **Conversor Word → Markdown (`src/ingestion/docx_to_md.py`):** Nueva herramienta que extrae texto de archivos .docx usando `python-docx` y lo convierte a Markdown con estructura de encabezados (`#`, `##`, `###`), negritas y frontmatter YAML automático (título, categoría, autor, fecha, tags, ID).
- **Pipeline de ingesta Word/PDF:** Los archivos .docx convertidos a .md entran en el pipeline estándar (Parser → Chunker → Grafo → VectorStore), por lo que se indexan, crean nodos en el grafo y se recuperan en consultas híbridas igual que cualquier documento Markdown nativo.
- **Frontmatter sintético para documentos importados:** Se genera automáticamente `id`, `title`, `categoria: importado`, `autor: Sistema Base del Conocimiento`, `creado` (fecha de conversión), `tags: ["#importado", "#word"]` y `Link to: null`.
- **Preservación de enlaces wiki:** Si el documento Word contiene referencias tipo `[[enlace]]`, se conservan en el Markdown resultante y se crean las aristas correspondientes en el grafo.
- **PDF (pendiente):** Documentado en backlog para integrar con `pypdf`/`pdfplumber` y OCR (`pytesseract`/`easyocr`) para PDF escaneados.

### 🔧 Flujo de Uso
```bash
# 1. Convertir un documento Word a Markdown
python3 src/ingestion/docx_to_md.py "data/contrato msp.docx" "data/contrato msp.md"

# 2. Reindexar (el indexer limpia duplicados previos antes de insertar)
POST /index   # vía API, Streamlit o python3 run_demo.py

# 3. Consultar sobre el documento importado
python3 run_chat.py llamacpp http://localhost:8080
```

---

## v0.9.2-alpha (Sprint 1.2: Modelo Ligero 1B, Deduplicación de Contextos y Optimización para Hardware Limitado)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se completa el **Sprint 1.2** con mejoras orientadas a entornos de hardware limitado (solo CPU, RAM reducida): **modelo LLM ligero (gemma-3-1b-it 1B)**, **parámetros de generación reducidos** (`n_predict=256`, `temperature=0.3`), **top_k por defecto 3**, **truncado de contexto en prompt**, **deduplicación de chunks por contenido** (no solo por `chunk_id`) y **limpieza de chunks previos al re-indexar**. Se eliminan respuestas repetidas y fuentes duplicadas en cada consulta.

### ✨ Novedades y Componentes Implementados
- **Modelo LLM ligero por defecto (`src/config/settings.py`):** `llm_model_name` pasa de `llama3` a `gemma-3-1b-it` (1B, cuantificado), ideal para CPU sin GPU.
- **Parámetros de generación reducidos:** `llm_n_predict=256`, `llm_temperature=0.3`, `llm_ctx_size=2048`. Menos tokens de salida y menor consumo de CPU/RAM por inferencia.
- **Retrieval más ligero:** `default_top_k` baja de 4 a 3; `MAX_CONTEXTS = 6` en `HybridRetriever` limita el total de contextos enviados al LLM.
- **Deduplicación robusta (`src/vectorstore/store.py`, `src/retrieval/hybrid.py`):**
  - `similarity_search` descarta chunks con hash de contenido duplicado (MD5).
  - `HybridRetriever` dedup por `chunk_id` **y** por hash de contenido entre resultados vectoriales y expansión de grafo.
  - `MAX_CONTEXTS` evita saturar el modelo con contexto repetido o excesivo.
- **Indexación sin duplicados acumulados (`src/vectorstore/indexer.py`, `src/vectorstore/store.py`):**
  - Nuevo `delete_chunks_by_source(source_path)` para limpiar chunks previos de una fuente antes de `add_chunks`.
  - El indexer llama a `delete_chunks_by_source` por documento antes de re-indexar, evitando chunks repetidos en ChromaDB.
- **Prompt optimizado para modelo 1B (`src/generation/local_llm.py`):** Prompt más corto, contexto truncado a 500 chars por chunk y 2000 totales, instrucciones de síntesis (prohíbe copia textual).
- **Coherencia entre interfaces:** `src/api/main.py` y `src/ui/app.py` pasan `n_predict` y `temperature` al `LocalLLMClient`; `src/ui/tui.py` usa `settings.default_top_k` por defecto.

### 🖥️ Interfaz Disponibles (todas comparten la misma lógica `src/`)
| Interfaz | Comando | Descripción |
|----------|---------|-------------|
| API REST | `uvicorn src.api.main:app --reload` | Endpoints `/health`, `/index`, `/query` |
| Web (Streamlit) | `streamlit run src/ui/app.py` | Panel visual con chat, editor y configuración |
| TUI (Textual) | `python3 src/ui/tui.py` | Interfaz de terminal ligera, sin servidor web |
| CLI Chat | `python3 run_chat.py llamacpp http://localhost:8080` | Chat conversacional por terminal |

### 🧪 Comandos de Prueba
```bash
# Tests unitarios (11 passing, mocks para LLM/vector store)
PYTHONPATH=. pytest tests/ -v

# Lanza servidor LLM ligero (1B, CPU)
llama-server -hf ggml-org/gemma-3-1b-it-Q4_K_M-GGUF -c 2048 --port 8080

# Chat CLI
python3 run_chat.py llamacpp http://localhost:8080

# Reindexar documentos (limpia duplicados previos)
POST /index   # o ejecutar python3 run_demo.py
```

---

## v0.9.1-alpha (Sprint 1.1: TUI Textual, Configuración .env y Soporte Multi-Interfaz)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se completa el Sprint 1.1 con tres mejoras de operatividad y experiencia de desarrollador: **archivo `.env` para configuración por variables de entorno**, **nueva TUI basada en Textual** como alternativa ligera a Streamlit, y documentación consolidada de todas las mejoras del Sprint 1. El sistema mantiene su arquitectura desacoplada: la lógica de negocio (`src/`) es compartida por API, Streamlit y TUI sin duplicación.

### ✨ Novedades y Componentes Implementados
- **Archivo `.env` y `.env.example`:** Variables de entorno por defecto para LLM, Vector Store, Grafo, API y Retrieval. Ignorado en git (`.gitignore` ya incluía `.env`). Carga automática vía `src/config/settings.py` (pydantic-settings).
- **TUI Textual (`src/ui/tui.py`):** Nueva interfaz de terminal independiente que reusa `LocalLLMClient`, `HybridRetriever`, `KnowledgeGraphManager`, `VectorStoreManager` y `KnowledgeBaseIndexer`. Incluye chat interactivo, configuración de backend/URL/timeout/top-k/radio de grafo, indexación Base del Conocimiento y estadísticas del grafo. No requiere servidor web ni navegador.
- **Cliente LLM lee `.env` por defecto (`src/generation/local_llm.py`):** El constructor de `LocalLLMClient` ahora usa `get_settings()` como valores por defecto (`backend`, `base_url`, `model_name`, `timeout`, `max_retries`, `base_delay`), permitiendo instanciarlo sin argumentos y tomar la configuración del entorno.
- **Dependencia añadida:** `textual>=0.86.0` en `requirements.txt`.

### 🖥️ Interfaz Disponibles (todas comparten la misma lógica `src/`)
| Interfaz | Comando | Descripción |
|----------|---------|-------------|
| API REST | `uvicorn src.api.main:app --reload` | Endpoints `/health`, `/index`, `/query` |
| Web (Streamlit) | `streamlit run src/ui/app.py` | Panel visual con chat, editor y configuración |
| TUI (Textual) | `python3 src/ui/tui.py` | Interfaz de terminal ligera, sin servidor web |
| CLI Chat | `python3 run_chat.py llamacpp http://localhost:8080` | Chat conversacional por terminal |

### 🧪 Comandos de Prueba
```bash
# Tests unitarios (11 passing, mocks para LLM/vector store)
PYTHONPATH=. pytest tests/ -v

# TUI (requiere LLM server en puerto 8080)
python3 src/ui/tui.py

# Demo E2E
python3 run_demo.py

# Cargar .env
cp .env.example .env && export $(cat .env | xargs)
```

---

## v0.9.0-alpha (Sprint 1: Mejoras Core - Graph Expansion, LLM Retry, Config Centralizada)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado el **Sprint 1** de mejoras core del sistema, abordando tres áreas críticas: **recuperación híbrida real** (el grafo ahora devuelve contenido real de chunks vecinos, no solo metadatos), **resiliencia del cliente LLM** (retry exponencial con backoff configurable), y **configuración centralizada** con validación via pydantic-settings.

### ✨ Novedades y Componentes Implementados
- **Recuperación Híbrida Real (`src/retrieval/hybrid.py`, `src/vectorstore/store.py`):** Nueva función `get_chunks_by_doc_title()` en VectorStoreManager. El `HybridRetriever` ahora busca chunks reales de documentos vecinos en el grafo (límite 3 por vecino) y los incluye con su contenido completo, mejorando drásticamente la calidad del contexto enviado al LLM.
- **Cliente LLM con Retry/Backoff (`src/generation/local_llm.py`):** Implementación de reintentos exponenciales (`max_retries=3`, `base_delay=1.0s`) para errores 5xx, timeouts y errores de conexión. Parámetros configurables vía settings.
- **Configuración Centralizada (`src/config/settings.py`):** Nuevo módulo con `pydantic-settings` que unifica todas las variables de entorno (LLM, Vector Store, Graph, API, Retrieval) con validación de tipos, rangos y enums. Elimina `os.getenv` disperso.
- **Validación en API (`src/api/main.py`):** Pydantic `Field` con constraints: `top_k` (1-20), `graph_radius` (0-5), `timeout` (10-600s), `backend` enum (`llamacpp`|`ollama`).
- **Actualización AGENTS.md:** Añadida tabla de variables de entorno, comando Docker con profile UI, gotchas de Docker (`host.docker.internal`, hot-reload).

### 🔧 Cambios Técnicos
- `src/vectorstore/store.py`: +`get_chunks_by_doc_title(doc_title, limit=5)`
- `src/retrieval/hybrid.py`: Graph expansion usa chunks reales + deduplicación por `chunk_id`
- `src/generation/local_llm.py`: `_request_with_retry()` con backoff exponencial, `max_retries`, `base_delay`
- `src/config/settings.py`: Nuevo, `Settings` class con `SettingsConfigDict`, `@lru_cache get_settings()`
- `src/api/main.py`, `src/ui/app.py`, `src/vectorstore/indexer.py`: Migración a `get_settings()`

### 🧪 Comandos de Prueba
```bash
# Tests unitarios (11 passing, mocks para LLM/vector store)
PYTHONPATH=. pytest tests/ -v

# Demo E2E (requiere LLM server en puerto 8080)
python3 run_demo.py

# Chat CLI
python3 run_chat.py llamacpp http://localhost:8080

# API + UI con Docker
docker-compose --profile ui up --build
```

---

## v0.8.0-alpha (Fase 8A: Interfaz Web Visual con Streamlit)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado la **Fase 8A** del proyecto, implementando la **Interfaz Web de Usuario con Streamlit (`src/ui/app.py`)** para permitir a los operadores e ingenieros interactuar visualmente con el sistema Graph RAG para la Base del Conocimiento, configurar parámetros de recuperación y backend LLM, ejecutar la indexación en tiempo real y consultar el grafo de conocimiento. Se han validado todas las dependencias vectoriales (`chromadb`, `sentence-transformers`) y establecido las pautas de permisos para entornos de producción.

### ✨ Novedades y Componentes Implementados
- **Interfaz Web Streamlit (`src/ui/app.py`):** Panel de control lateral con configuración de backend (Ollama / Llama.cpp), control de top-K y radio de grafo, botón de reindexación y visualización de estadísticas del grafo. Chat conversacional con despliegue de fuentes y referencias a ficheros originales de la Base del Conocimiento.
- **Validación Vectorial Completa:** Integración probada con ChromaDB y embeddings locales SentenceTransformers (`all-MiniLM-L6-v2`).
- **Nota de Producción (Permisos):** Recordatorio de configuración de permisos sobre `data/` para evitar bloqueos de base de datos en despliegues *on-premise*.

### 🧪 Comandos de Prueba Utilizados
1. **Ejecución de la Interfaz Web:**
   ```bash
   streamlit run src/ui/app.py
   ```

---

## v0.7.0-alpha (Fase 7: Contenerización Docker, Persistencia de Grafo y Chat CLI Interactivo)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado la **Fase 7** del proyecto, implementando la **Persistencia del Grafo de Conocimiento** en disco (`data/knowledge_graph.json`), la **Contenerización con Docker y Docker Compose** (`Dockerfile`, `docker-compose.yml`) para despliegues *on-premise* reproducibles, y el **Cliente de Chat Interactivo por Línea de Comandos** (`run_chat.py`) para consultas conversacionales directas.

### ✨ Novedades y Componentes Implementados
- **Persistencia de Grafo (`src/graph/manager.py`):** Guardado y carga automática del grafo NetworkX en formato JSON (`data/knowledge_graph.json`), evitando recomputar relaciones entre reinicios.
- **Cliente de Chat Interactivo (`run_chat.py`):** Interfaz CLI conversacional para realizar consultas híbridas y visualizar respuestas y fuentes de la Base del Conocimiento.
- **Contenerización Docker (`Dockerfile`, `docker-compose.yml`):** Configuración lista para producción *on-premise* con volúmenes persistentes para `data/`.
- **Pruebas Unitarias Ampliadas (`tests/test_graph.py`):** Cobertura de tests para la persistencia del grafo.

### 🧪 Comandos de Prueba Utilizados
1. **Ejecución de Pruebas Unitarias:**
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```
2. **Ejecución del Chat Interactivo CLI:**
   ```bash
   python3 run_chat.py llamacpp http://localhost:8080
   ```
3. **Despliegue con Docker Compose:**
   ```bash
   docker-compose up --build
   ```

---

## v0.6.0-alpha (Fase 6: Capa de Servicio - API REST con FastAPI)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado la **Fase 6** del proyecto, implementando la **Capa de Servicio (API REST con FastAPI en `src/api/main.py`)** para exponer los endpoints de salud (`/health`), indexación (`/index`) y consulta híbrida con generación LLM local (`/query`), junto con pruebas unitarias (`tests/test_api.py`) utilizando `TestClient`.

### ✨ Novedades y Componentes Implementados
- **API REST FastAPI (`src/api/main.py`):** Endpoints robustos para ingesta, recuperación híbrida y síntesis LLM local *on-premise*.
- **Pruebas Unitarias de API (`tests/test_api.py`):** Cobertura de tests para todos los endpoints utilizando `TestClient` de FastAPI y mocks.
- **Actualización de Dependencias (`requirements.txt`):** Inclusión de `fastapi` y `uvicorn`.

### 🧪 Comandos de Prueba Utilizados
1. **Ejecución de Pruebas Unitarias (incluyendo API):**
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```
2. **Ejecución del Servidor API:**
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --ws none
   ```

---

## v0.5.0-alpha (Fase 5: Pruebas de Integración E2E y Script de Demostración)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado la **Fase 5** del sistema, implementando el script de demostración de integración End-to-End (`run_demo.py`), validando la indexación real de la Base del Conocimiento, la recuperación híbrida y la conectividad con el servidor LLM local (`llama.cpp` en `http://localhost:8080`) con timeout ampliado y configurable (por defecto 300 segundos).

### ✨ Novedades y Componentes Implementados
- **Script E2E (`run_demo.py`):** Orquestador completo para pruebas de integración sobre la documentación real en `data/`.
- **Configuración de Timeout Robusta (`src/generation/local_llm.py`):** Soporte de timeout ajustable (`timeout=300` o superior) para evitar caídas ante consultas largas en servidores LLM locales.
- **Documentación de Pruebas:** Guía completa de comandos de validación y pruebas unitarias/E2E en el `README.md`.

### 🧪 Comandos de Prueba Utilizados
1. **Ejecución de Pruebas Unitarias:**
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```
2. **Ejecución de Demostración E2E (`run_demo.py`):**
   ```bash
   python3 run_demo.py
   ```
3. **Consulta Puntual al LLM Local:**
   ```bash
   python3 -c "
   from src.generation.local_llm import LocalLLMClient
   llm = LocalLLMClient(backend='llamacpp', base_url='http://localhost:8080', timeout=300)
   print(llm.generate_response('¿Cuándo se bloqueó la OLT?', [{'content': 'Olt bloqueada el 12 de octubre.', 'metadata': {'title': 'Incidencia'}}]))
   "
   ```

---

## v0.4.0-alpha (Fase 4: Recuperación Híbrida y Generación Local - Ollama & Llama.cpp)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado la **Fase 4** del sistema, implementando el **Motor de Recuperación Híbrida** (búsqueda vectorial + expansión de contexto mediante vecinos en el grafo NetworkX) y la **Capa de Generación Local LLM** con soporte multi-backend para **Ollama** y el servidor nativo de **llama.cpp** (`llama-server` vía endpoint `/completion`). Se han incorporado pruebas unitarias completas para los nuevos componentes.

### ✨ Novedades y Componentes Implementados
- **Motor de Recuperación Híbrida (`src/retrieval/hybrid.py`):** Combina la recuperación semántica densa de fragmentos con la exploración topológica de documentos relacionados en el grafo de conocimiento.
- **Cliente LLM Local Multi-backend (`src/generation/local_llm.py`):** Soporte unificado para Ollama (`/api/generate`) y el servidor HTTP nativo de `llama.cpp` (`/completion`), garantizando la soberanía de datos *on-premise*. Se ha incorporado la recomendación de modelos ultraligeros (`ggml-org/gemma-3-1b-it-GGUF`) para pruebas locales eficientes en hardware de bajos recursos. Se ha añadido un parámetro de `timeout` configurable (por defecto 300 segundos) para prevenir interrupciones por tiempo de espera en consultas locales a `llama-server`.
- **Pruebas Unitarias (`tests/test_retrieval.py`, `tests/test_local_llm.py`):** Validación de recuperación y generación con mocks.

### 🧪 Comandos de Prueba Utilizados
1. **Ejecución de Pruebas Unitarias:**
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```
2. **Prueba del Motor de Recuperación Híbrida:**
   ```bash
   python3 -c "
   from src.vectorstore.store import VectorStoreManager
   from src.graph.manager import KnowledgeGraphManager
   from src.retrieval.hybrid import HybridRetriever
   vs = VectorStoreManager()
   gm = KnowledgeGraphManager()
   retriever = HybridRetriever(vector_store=vs, graph_manager=gm)
   print('Retriever inicializado correctamente.')
   "
   ```

---

## v0.3.0-alpha (Fase 3: Indexación y Almacenamiento Vectorial)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado la **Fase 3** del proyecto, implementando el chunking jerárquico por encabezados, el gestor de base de datos vectorial local con ChromaDB y embeddings locales con SentenceTransformers (con soporte modular para entornos ligeros), el pipeline completo de indexación y nuevas pruebas unitarias.

### ✨ Novedades y Componentes Implementados
- **Chunker Jerárquico (`src/ingestion/chunker.py`):** Fragmentación inteligente de documentos Markdown respetando la jerarquía de títulos (`#`, `##`, `###`) y preservando el contexto y metadatos.
- **Gestor Vectorial Local (`src/vectorstore/store.py`):** Integración con ChromaDB y SentenceTransformers (`all-MiniLM-L6-v2`) para generación y búsqueda de similitud semántica. Incluye manejo robusto de dependencias para ejecución ligera en entornos sin GPU.
- **Pipeline de Indexación (`src/vectorstore/indexer.py`):** Orquestador que conecta Parser, Chunker, Gestor de Grafo y Base Vectorial para procesar automáticamente los ficheros de la Base del Conocimiento.
- **Pruebas Unitarias y Comandos de Validación:** Cobertura de tests para fragmentación y búsqueda vectorial.

### 🧪 Comandos de Prueba Utilizados
1. **Ejecución de Pruebas Unitarias:**
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```
2. **Prueba de Chunking sobre Documentos Reales (`data/`):**
   ```bash
   python3 -c "
   from src.ingestion.parser import MarkdownParser
   from src.ingestion.chunker import HierarchicalMarkdownChunker
   parser = MarkdownParser()
   chunker = HierarchicalMarkdownChunker()
   parsed = parser.parse_file('data/C00012 - Muro Parque Santiago.md')
   chunks = chunker.chunk_document(parsed)
   print(f'Total de chunks generados: {len(chunks)}')
   for c in chunks[:3]:
       print(f' - ID: {c[\"chunk_id\"]} | Cabecera: {c[\"header_path\"]}')
   "
   ```

---

## v0.2.0-alpha (Fase 2: Ingesta y Análisis Estructural)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado la **Fase 2** del proyecto, implementando el parser robusto de Markdown y el gestor de grafos de conocimiento basado en NetworkX. Se han incorporado pruebas unitarias completas y herramientas de validación sobre documentos reales de la Base del Conocimiento.

### ✨ Novedades y Componentes Implementados
- **Parser de Markdown (`src/ingestion/parser.py`):** Lectura automatizada de ficheros `.md`, extracción de metadatos YAML frontmatter y extracción de enlaces cruzados estilo wiki (`[[enlace]]` / `[[enlace|alias]]`).
- **Gestor de Grafo (`src/graph/manager.py`):** Creación de la red relacional dirigida con **NetworkX**, permitiendo inserción de nodos/documentos, aristas relacionales y obtención de subgrafos contextuales por radio de vecinos.
- **Pruebas Unitarias y Validación (`tests/`):** Cobertura de tests para el parser y operaciones de grafo.
- **Documentación de Comandos de Prueba:** Guía de ejecución para pruebas unitarias y parsing de documentos reales en `data/`.

### 🧪 Comandos de Prueba Utilizados
1. **Ejecución de Pruebas Unitarias:**
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```
2. **Prueba de Ingesta y Parsing sobre Documentos Reales (`data/`):**
   ```bash
   python3 -c "
   from pathlib import Path
   from src.ingestion.parser import MarkdownParser
   parser = MarkdownParser()
   for md_file in Path('data').glob('*.md'):
       res = parser.parse_file(md_file)
       print(f'Archivo: {md_file.name} | Título: {res[\"frontmatter\"].get(\"title\")} | Enlaces Wiki: {len(res[\"wiki_links\"])}')
   "
   ```

---

## v0.1.0-alpha (Fase Inicial / Planificación y Diseño Arquitectónico)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Esta versión inicial establece las bases conceptuales, arquitectónicas y de gobernanza para el desarrollo del sistema **Graph RAG para la Base del Conocimiento**. Define los principios rectores orientados a la privacidad y soberanía de datos (*on-premise*), así como la integración híbrida de grafos de conocimiento y recuperación vectorial.

### ✨ Novedades y Componentes Incluidos
- **Directrices de Desarrollo (`AGENTS.md`):** Normas técnicas para la colaboración entre el Guía y el Agente de Programación, priorizando la simplicidad, eficiencia y preservación del contexto estructural de los documentos Markdown.
- **Definición de Arquitectura (`docs/architecture_mindmap.mmd` & `docs/graph_rag_sgd_mindmap.svg`):** Esquema modular detallado de los cuatro pilares del sistema:
  1. Ingesta y Procesamiento (Parser Markdown, Frontmatter, Chunking Estructural, Grafo NetworkX).
  2. Indexación y Almacenamiento (Embeddings locales, Base de Datos Vectorial, Metadatos).
  3. Motor de Recuperación Híbrido (Búsqueda semántica densa + expansión relacional en grafo + re-ranking).
  4. Capa de Generación e Interfaz (LLM local, API/Interfaz de consulta).
- **Documentación de Entrada (`README.md`):** Guía general del proyecto, arquitectura visual en Mermaid, estructura del repositorio y **guía detallada de despliegue y pruebas** para entornos de desarrollo y producción *on-premise*.

### 🎯 Próximos Pasos (v0.2.0)
- Desarrollo del script de ingesta en Python para lectura de archivos Markdown de la Base del Conocimiento.
- Extracción automatizada de metadatos YAML frontmatter y enlaces cruzados tipo wiki (`[[enlace]]`).
- Construcción inicial del grafo de relaciones utilizando NetworkX.

---

## 🚀 Roadmap / Mejoras Futuras (Post v0.8.0)

### Visualización Interactiva del Grafo de Conocimiento (UI)
**Propuesta:** Añadir nueva tab "🕸️ Grafo Base del Conocimiento" en Streamlit para explorar nodos/edges visualmente.

**Funcionalidades deseadas:**
- **Vista grafo interactiva** (pyvis / networkx + streamlit-agraph / cytoscape.js):
  - Nodos = documentos (tamaño por nº chunks, color por categoría)
  - Edges = wiki links (dirigidos, etiquetados)
  - Zoom, pan, drag, selección múltiple
- **Filtros**: por categoría, por status, por radio de vecinos desde nodo seleccionado
- **Detalle al click**: panel lateral con metadatos del nodo, chunks asociados, vecinos directos
- **Acciones**: "Ver documento en Editor", "Ejecutar consulta RAG desde este nodo"
- **Métricas**: grado de entrada/salida, centralidad, componentes conectados
- **Export**: PNG/SVG del subgrafo visible, JSON del subgrafo para análisis offline

**Dependencias candidatas:**
- `streamlit-agraph` (wrapper de react-graph-vis)
- `pyvis` (genera HTML interactivo, embebible via `st.components.v1.html`)
- `networkx` + `matplotlib`/`plotly` para vistas estáticas rápidas

**Valor:** Permite a gestores/documentalistas entender la topología documental, detectar docs huérfanos, clusters temáticos, y validar que los wiki links reflejan la estructura real de la Base del Conocimiento.
