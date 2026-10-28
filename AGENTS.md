# AGENTS.md - Graph RAG para Base del Conocimiento

## Project Overview
Graph RAG system for on-premise knowledge base (Base del Conocimiento). Combines vector search (ChromaDB + sentence-transformers) with knowledge graph (NetworkX) for hybrid retrieval, plus local LLM generation (Ollama / llama.cpp).

## Key Commands

**Tests** (always run with PYTHONPATH):
```bash
PYTHONPATH=. pytest tests/ -v
```

**Run E2E Demo** (requires local LLM server on port 8080):
```bash
python3 run_demo.py
```

**CLI Chat** (args: backend, base_url):
```bash
python3 run_chat.py llamacpp http://localhost:8080
```

**Streamlit UI**:
```bash
streamlit run src/ui/app.py
```

**FastAPI Server**:
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --ws none
```

**Docker** (API only):
```bash
docker-compose up --build
```

**Docker with UI** (dev profile):
```bash
docker-compose --profile ui up --build
```

## Architecture & Entry Points

| Component | File | Purpose |
|-----------|------|---------|
| Markdown Parser | `src/ingestion/parser.py` | Extracts frontmatter, wiki links `[[link\|alias]]`, headers |
| Hierarchical Chunker | `src/ingestion/chunker.py` | Splits by header hierarchy preserving context |
| Knowledge Graph | `src/graph/manager.py` | NetworkX DiGraph, persists to `data/knowledge_graph.json` |
| Vector Store | `src/vectorstore/store.py` | ChromaDB + sentence-transformers (paraphrase-multilingual-mpnet-base-v2) |
| Indexer | `src/vectorstore/indexer.py` | Orchestrates parser → chunker → graph → vector store |
| Hybrid Retriever | `src/retrieval/hybrid.py` | Vector search + graph neighbor expansion |
| Local LLM Client | `src/generation/local_llm.py` | Multi-backend: Ollama (`/api/generate`) + llama.cpp (`/completion`) |
| LLM Extractor | `src/graph/extractor.py` | Optional entity/relation extraction with JSON-forced LLM output |
| Documentation Agent | `src/documentation/agent.py` | Organizes incident notes (case/evidence/resolution) via local LLM into frontmatter + Markdown in `data/incidencias/` |
| REST API | `src/api/main.py` | FastAPI: `/health`, `/index`, `/query`, `/documentar-incidencia` |
| Streamlit UI | `src/ui/app.py` | Web interface with config sidebar + "Documentar Incidencia" tab |
| Crear Estructura/Clientes | `scripts/crear_estructura.py` | Creates directories and initial Markdown documents per client and system; validates systems, idempotent (`--force`), `--init-data-dir` |

## Data Layout
```
data/
├── clientes/               # Una carpeta por cliente (ej. parque_santiago/, hotel_guayarmina/)
│   ├── <cliente>/          # Un cliente = un directorio con sus .md
│   │   ├── <cliente>.md    # Índice central del cliente
│   │   └── <cliente>_<sistema>.md  # Subsistemas (iptv, xgspon, switches, voip, tv, wifi)
├── incidencias/            # Casos de incidencia genéricos (referenciados vía [[<CASE_ID>]])
│   └── <CASE_ID>.md        # Ej: NET-IPTV-0041.md con frontmatter completo
├── vectorstore/            # ChromaDB persistence
└── knowledge_graph.json    # NetworkX graph export
```

## Crear Nuevos Clientes y Estructura de Directorios (`scripts/crear_cliente.py` y `scripts/crear_estructura.py`)

Para añadir un cliente sin romper lo existente, puedes usar cualquiera de los dos scripts. Ambos crean el directorio bajo `data/clientes/<slug>/`, un índice central (`<slug>.md`) y un archivo por subsistema (`<slug>_<sistema>.md`) con frontmatter YAML y enlaces wiki bidireccionales.

### `scripts/crear_cliente.py` (original)

Crea clientes con los sistemas por defecto (`iptv, xgspon, switches, voip, tv, wifi`) o personalizados.

```bash
# Sistemas por defecto
PYTHONPATH=. python3 scripts/crear_cliente.py "Hotel Guayarmina"

# Sistemas personalizados
PYTHONPATH=. python3 scripts/crear_cliente.py "Hotel Guayarmina" iptv switches wifi

# Luego indexar
PYTHONPATH=. python3 -m src.vectorstore.indexer
```

### `scripts/crear_estructura.py` (extendido)

Además de crear clientes, permite inicializar la estructura raíz de `data/` (`clientes/`, `incidencias/`, `vectorstore/`), valida los sistemas contra un catálogo, es idempotente (`--force` para sobrescribir) y acepta `--data-dir`, `--fecha` y `--autor` personalizados.

```bash
# Inicializar solo la estructura raíz de data/
PYTHONPATH=. python3 scripts/crear_estructura.py --init-data-dir

# Crear cliente con sistemas por defecto
PYTHONPATH=. python3 scripts/crear_estructura.py "Hotel Guayarmina"

# Sistemas personalizados
PYTHONPATH=. python3 scripts/crear_estructura.py "Hotel Guayarmina" iptv switches wifi

# Sobrescribir archivos existentes
PYTHONPATH=. python3 scripts/crear_estructura.py "Hotel Guayarmina" --force

# Directorio de datos, fecha y autor personalizados
PYTHONPATH=. python3 scripts/crear_estructura.py "Hotel Guayarmina" --data-dir ./data --fecha 2026-10-24 --autor "Equipo TI"

# Listar sistemas disponibles
PYTHONPATH=. python3 scripts/crear_estructura.py --listar-sistemas

# Luego indexar
PYTHONPATH=. python3 -m src.vectorstore.indexer
```

Cada cliente obtiene `id` único en el frontmatter, enlaces wiki bidireccionales entre el índice central y sus subsistemas, y comentarios para rellenar el conocimiento.

## Documentar Incidencias (`src/documentation/agent.py`)

El agente de documentación permite crear casos de incidencia genéricos en `data/incidencias/` a partir de notas crudas (caso, pruebas y resolución), organizadas con el LLM local según el esquema de frontmatter del proyecto. Esto permite que múltiples clientes referencien el mismo caso vía `[[<CASE_ID>]]` sin duplicar contenido.

### Uso

```python
from src.documentation import DocumentationAgent

agent = DocumentationAgent()
result = agent.run(
    caso="Corte de IPTV cada 4 minutos...",
    pruebas="Captura IGMP... el STB ignora queries de 0.0.0.0",
    resolucion="Configurar SVI con IP 10.40.0.2/24 en VLAN 400",
    write_file=True,  # guarda en data/incidencias/<ID>.md
)
print(result.file_path)  # data/incidencias/NET-IPTV-0042.md
```

### CLI de ejemplo

```bash
PYTHONPATH=. python3 scripts/documentar_incidencia.py \
    --caso "..." \
    --pruebas "..." \
    --resolucion "..."
```

### Endpoint API

```bash
curl -X POST http://localhost:8000/documentar-incidencia \
  -H "Content-Type: application/json" \
  -d '{"caso": "...", "pruebas": "...", "resolucion": "..."}'
```

### UI Streamlit

```bash
streamlit run src/ui/app.py
# → pestaña "📄 Documentar Incidencia"
```

### Frontmatter generado (campos obligatorios)

`id`, `title`, `caso`, `tipo`, `categoria`, `sistema`, `criticidad`, `tags`, `clientes_afectados`, `fecha_deteccion`, `fecha_actualizacion`.

### Cuerpo Markdown generado

Secciones estándar: `## 1. Síntoma del Problema`, `## 2. Causa Raíz (Análisis Técnico)`, `## 3. Protocolo de Resolución`, `## 4. Comprobación de Verificación`.

### Después de documentar

Ejecutar el indexador para que el grafo y el vector store recojan el nuevo caso:

```bash
PYTHONPATH=. python3 -m src.vectorstore.indexer
```

Luego referenciar el caso desde cualquier cliente vía wiki link:

```markdown
## Incidencias destacadas
- [[NET-IPTV-0042]]
```

## Environment Variables (API)
| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BACKEND` | `llamacpp` | `ollama` or `llamacpp` |
| `LLM_BASE_URL` | `http://localhost:8080` | LLM server URL |
| `LLM_TIMEOUT` | `300` | Request timeout in seconds |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-mpnet-base-v2` | Embedding model for vector store |
| `DEFAULT_TOP_K` | `20` | Default number of retrieved chunks |
| `EXTRACTION_ENABLED` | `false` | Enable LLM-based entity/relation extraction during indexing |
| `EXTRACTION_MODEL` | `null` | LLM model for extraction (uses `LLM_MODEL_NAME` if null) |
| `EXTRACTION_TEMPERATURE` | `0.1` | Temperature for extraction LLM |
| `EXTRACTION_MAX_TOKENS` | `512` | Max tokens for extraction LLM |
| `ENTITY_SIMILARITY_THRESHOLD` | `0.9` | Threshold to merge duplicate entities |

## LLM Backends
- **llama.cpp**: `llama-server -hf bartowski/Llama-3.2-3B-Instruct-GGUF:Q4_K_M -c 4096 --port 8080 --alias llama-3.2-3b` (recomendado para v0.9.5+)
- **Ollama**: `ollama serve && ollama pull qwen2.5:3b`
- Configure in code: `LocalLLMClient(backend="llamacpp", base_url="http://localhost:8080", timeout=300)`
- Current alias in `.env`: `LLM_MODEL_NAME=llama-3.2-3b`

## Opción A vs Opción C (Extracción de Entidades)

El proyecto soporta dos modos de despliegue:

**Opción A — Base pipeline sin LLM (por defecto):**
- `extraction_enabled = false`
- El grafo contiene solo nodos de documento y enlaces wiki_link
- Funciona sin servidor LLM durante el indexado
- Ideal para desarrollo y hardware limitado

**Opción C — Extracción con LLM (para producción en hardware potente):**
- `extraction_enabled = true`
- El extractor (`src/graph/extractor.py`) enriquece el grafo con entidades y relaciones extraídas por LLM
- Requiere servidor LLM potente (Qwen3-4B/8B recomendado con GPU)
- Más detalles en `TODO.md`

## Development Notes
- Python 3.10+, dependencies in `requirements.txt`
- Tests use mocks for LLM/vector store - **no external services needed** for unit tests
- `PYTHONPATH=.` required for imports (no package install)
- Graph persists automatically on index; reloads on startup
- Production: fix `data/` permissions (`chown -R $USER:$USER data/`)

## Common Gotchas
- LLM timeout defaults to 300s - increase for slow models
- ChromaDB requires write access to `data/vectorstore/`
- Wiki links use `[[target]]` or `[[target|alias]]` syntax
- Frontmatter must be valid YAML at file start
- Docker uses `host.docker.internal` for LLM connectivity from container
- `docker-compose.override.yml` mounts source for hot-reload (dev only)

## Retriever: Filtrado por Cliente
Cuando una consulta menciona un cliente específico (ej. "villa cortes", "parque santiago"), el retriever detecta automáticamente el cliente y prioriza sus chunks, evitando que el LLM confunda información de diferentes clientes. Para que funcione, el nombre en la consulta debe coincidir con parte del slug del cliente (ej. "villa cortes" detecta `hotel_villa_cortes`).

## Sprint 1 Improvements (v0.9.0)
- **Graph expansion** now retrieves actual chunk content from neighbors (not just metadata)
- **LLM client** has exponential backoff retry (`max_retries=3`, `base_delay=1s`)
- **Centralized config** in `src/config/settings.py` (pydantic-settings) with validation
- **API validates** timeout (10-600s), top_k (1-20), graph_radius (0-5), backend enum

## Sprint 1.5 Improvements (v0.9.5)
- **Keyword search** added to `VectorStoreManager` (`keyword_search`) for exact text matching of technical terms (e.g. `XGE1/0/25`, IPs, VLANs) that semantic embeddings miss
- **HybridRetriever** integrates `keyword_search` before vector search, prioritizing keyword hits; auto-extracts technical keywords via regex
- **Embedding model** changed to `paraphrase-multilingual-mpnet-base-v2` (768 dims) — requires reindexing (`rm -rf data/vectorstore`)
- **default_top_k** increased to 20; **MAX_CONTEXTS_PER_SOURCE** increased to 10

## Sprint 1.6 Improvements (v0.9.6 — Completed)
- **LLM Extractor** (`src/graph/extractor.py`): Optional entity/relation extraction with JSON-forced output, entity normalization/deduplication, frontmatter-to-graph integration
- **Opción A / Opción C**: Base pipeline without LLM extraction (default) vs optional LLM enrichment for production
- **Centralized extraction config**: `extraction_enabled`, `extraction_model`, `extraction_temperature`, `extraction_max_tokens`, `entity_similarity_threshold` in `src/config/settings.py`
- **Indexer integration**: `KnowledgeBaseIndexer` instantiates `LLMExtractor` only when `extraction_enabled = true`

## Sprint 1.6-delta Improvements (v0.9.6-delta — Completed)
- **Documentation Agent** (`src/documentation/agent.py`): `DocumentationAgent` organizes incident notes (case/evidence/resolution) via local LLM into frontmatter + Markdown in `data/incidencias/`; includes `IncidentFrontmatter` and `DocumentationResult` data models
- **CLI** (`scripts/documentar_incidencia.py`): Document incidents from console with `--caso`, `--pruebas`, `--resolucion`
- **API** (`src/api/main.py`): New endpoint `POST /documentar-incidencia` with `DocumentationRequest`/`DocumentationResponse`
- **Streamlit UI** (`src/ui/app.py`): New tab "📄 Documentar Incidencia" with case/evidence/resolution text areas, LLM config, result preview, and raw LLM output expander