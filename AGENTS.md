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
| REST API | `src/api/main.py` | FastAPI: `/health`, `/index`, `/query` |
| Streamlit UI | `src/ui/app.py` | Web interface with config sidebar |

## Data Layout
```
data/
├── *.md                    # Source Knowledge Base documents
├── vectorstore/            # ChromaDB persistence
└── knowledge_graph.json    # NetworkX graph export
```

## Environment Variables (API)
| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BACKEND` | `llamacpp` | `ollama` or `llamacpp` |
| `LLM_BASE_URL` | `http://localhost:8080` | LLM server URL |
| `LLM_TIMEOUT` | `300` | Request timeout in seconds |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-mpnet-base-v2` | Embedding model for vector store |
| `DEFAULT_TOP_K` | `20` | Default number of retrieved chunks |

## LLM Backends
- **llama.cpp**: `llama-server -hf bartowski/Qwen2.5-3B-Instruct-GGUF:Q4_K_S -c 4096 --port 8080` (recomendado para v0.9.5)
- **Ollama**: `ollama serve && ollama pull qwen2.5:3b`
- Configure in code: `LocalLLMClient(backend="llamacpp", base_url="http://localhost:8080", timeout=300)`

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