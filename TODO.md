# TODO — Activar extracción de entidades con LLM (Opción C)

Este documento describe los pasos para activar la extracción de entidades y relaciones mediante LLM en el grafo de conocimiento, tal como se planteó en la revisión de arquitectura.

## Estado actual (Opción A — Base pipeline sin LLM)

El proyecto está configurado para funcionar **sin extracción LLM** (`extraction_enabled = False` en `src/config/settings.py`). El pipeline base funciona así:

```
Markdown Parser → Chunker → Vector Store (ChromaDB) + Knowledge Graph (nodos de documento + enlaces wiki_link)
```

Esto ya está operativo y probado con los 4 archivos de `data/clientes/`.

## ¿Qué se necesita para activar la Opción C (extracción LLM)?

Cuando dispongas de hardware más potente (GPU o servidor dedicado), sigue estos pasos:

### 1. Levantar un servidor LLM potente

Ejemplo con `llama-server` (llama.cpp) usando Qwen3-4B o Qwen3-8B:

```bash
# Qwen3-4B (recomendado para CPU/GPU intermedio)
llama-server -hf bartowski/Qwen3-4B-Instruct-2507-Q4_K_M -c 4096 --port 8080 --host 0.0.0.0 -t 8 --mmap

# Qwen3-8B (si tienes GPU con suficiente VRAM)
llama-server -hf bartowski/Qwen3-8B-Instruct-2507-Q4_K_M -c 4096 --port 8080 --host 0.0.0.0 -t 8 --mmap --gpu-layers 999
```

O con Ollama:

```bash
ollama serve
ollama pull qwen3:4b
# o qwen3:8b
```

### 2. Configurar el backend en `.env` o variables de entorno

Crea o edita `.env` en la raíz del proyecto:

```env
LLM_BACKEND=llamacpp
LLM_BASE_URL=http://localhost:8080
LLM_TIMEOUT=300
LLM_MODEL_NAME=qwen3-4b-instruct-2507
EXTRACTION_ENABLED=true
EXTRACTION_MODEL=qwen3-4b-instruct-2507
EXTRACTION_TEMPERATURE=0.1
EXTRACTION_MAX_TOKENS=512
ENTITY_SIMILARITY_THRESHOLD=0.9
```

O edita directamente `src/config/settings.py`:

```python
extraction_enabled: bool = True
extraction_model: Optional[str] = "qwen3-4b-instruct-2507"
```

### 3. Reindexar la base de conocimientos

La extracción LLM se ejecuta durante el indexado. Para enriquecer el grafo existente con entidades extraídas:

```bash
# Limpiar vector store y grafo (opcional, si quieres empezar limpio)
rm -rf data/vectorstore data/knowledge_graph.json

# Ejecutar indexado con extracción LLM activada
PYTHONPATH=. python3 -c "
from src.vectorstore.indexer import KnowledgeBaseIndexer
idx = KnowledgeBaseIndexer()
total = idx.run_indexing()
print(f'Chunks indexados: {total}')
"
```

**Nota:** En hardware potente con GPU, cada chunk debería procesarse en segundos. En CPU con modelos pequeños puede tardar varios minutos por chunk.

### 4. Verificar que el grafo se enriqueció

Después del indexado, revisa `data/knowledge_graph.json`. Deberías ver:
- Nodos con `"extracted": true` (entidades extraídas por LLM)
- Aristas con `"chunk_id"` vinculadas a chunks específicos
- Nuevos tipos de relación más allá de `wiki_link` (ej. `conecta_a`, `tiene_ip`, `tiene_vlan`, etc.)

### 5. (Opcional) Ajustar el modelo de embeddings si es necesario

Si en el futuro cambias el modelo de embeddings (`embedding_model` en settings), recuerda reindexar ChromaDB porque cambian las dimensiones:

```bash
rm -rf data/vectorstore
```

---

## Archivos involucrados

| Archivo | Función |
|---|---|
| `src/config/settings.py` | Configuración centralizada (`extraction_enabled`, `extraction_model`, etc.) |
| `src/graph/extractor.py` | Módulo de extracción LLM (esquemas Pydantic, prompt, llamada JSON-forzada) |
| `src/vectorstore/indexer.py` | Instancia `LLMExtractor` y llama a `populate_graph_from_extraction` por chunk |
| `src/graph/manager.py` | `KnowledgeGraphManager` — almacena nodos y aristas en NetworkX + JSON |

## Comandos útiles

```bash
# Tests unitarios (sin servicios externos)
PYTHONPATH=. pytest tests/ -v

# Indexado base (sin LLM, funciona ahora)
PYTHONPATH=. python3 -m src.vectorstore.indexer

# Crear un nuevo cliente (directorio, MDs y frontmatter automáticos)
PYTHONPATH=. python3 scripts/crear_cliente.py "Nombre del Cliente"

# Crear cliente con sistemas personalizados
PYTHONPATH=. python3 scripts/crear_cliente.py "Nombre del Cliente" iptv switches wifi

# Servidor FastAPI
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --ws none

# Streamlit UI
streamlit run src/ui/app.py
```

---

## Crear Nuevos Clientes (`scripts/crear_cliente.py`)

El script permite añadir clientes a la Base del Conocimiento sin romper lo existente:

```bash
# Sistemas por defecto: iptv, xgspon, switches, voip, tv, wifi
PYTHONPATH=. python3 scripts/crear_cliente.py "Hotel Guayarmina"

# Sistemas personalizados
PYTHONPATH=. python3 scripts/crear_cliente.py "Hotel Guayarmina" iptv switches wifi

# Con fecha personalizada
PYTHONPATH=. python3 scripts/crear_cliente.py "Hotel Guayarmina" --fecha 2026-10-24
```

Después de crear, siempre indexar:

```bash
PYTHONPATH=. python3 -m src.vectorstore.indexer
```

Cada cliente se crea en `data/clientes/<slug>/` con un índice central y un archivo por subsistema, todos con frontmatter YAML y enlaces wiki bidireccionales.

---

## Retriever: Filtrado por Cliente (v0.9.6-gamma)

El retriever detecta automáticamente el cliente mencionado en la consulta y prioriza sus chunks:

```bash
# Consulta sobre cliente específico
PYTHONPATH=. python3 run_chat.py llamacpp http://localhost:8080
# > busca el caso NET-IPTV-0041 en villa cortes
# Respuesta basada en [Hotel Villa Cortes - Muro de Conocimiento]
```

Para que funcione, el nombre en la consulta debe coincidir con parte del slug del cliente (ej. "villa cortes" detecta `hotel_villa_cortes`). Los chunks placeholder (`<!-- Rellena aquí ... -->`) se filtran automáticamente para no ocupar espacio en el contexto.
