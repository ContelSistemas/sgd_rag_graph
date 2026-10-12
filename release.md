# Notas de Versión - Graph RAG para SGD

## v0.4.0-alpha (Fase 4: Recuperación Híbrida y Generación Local - Ollama & Llama.cpp)
**Fecha:** Octubre 2026

### 📋 Resumen de la Versión
Se ha completado la **Fase 4** del sistema, implementando el **Motor de Recuperación Híbrida** (búsqueda vectorial + expansión de contexto mediante vecinos en el grafo NetworkX) y la **Capa de Generación Local LLM** con soporte multi-backend para **Ollama** y el servidor nativo de **llama.cpp** (`llama-server` vía endpoint `/completion`). Se han incorporado pruebas unitarias completas para los nuevos componentes.

### ✨ Novedades y Componentes Implementados
- **Motor de Recuperación Híbrida (`src/retrieval/hybrid.py`):** Combina la recuperación semántica densa de fragmentos con la exploración topológica de documentos relacionados en el grafo de conocimiento.
- **Cliente LLM Local Multi-backend (`src/generation/local_llm.py`):** Soporte unificado para Ollama (`/api/generate`) y el servidor HTTP nativo de `llama.cpp` (`/completion`), garantizando la soberanía de datos *on-premise*. Se ha incorporado la recomendación de modelos ultraligeros (`ggml-org/gemma-3-1b-it-GGUF`) para pruebas locales eficientes en hardware de bajos recursos.
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
- **Pipeline de Indexación (`src/vectorstore/indexer.py`):** Orquestador que conecta Parser, Chunker, Gestor de Grafo y Base Vectorial para procesar automáticamente los ficheros del SGD.
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
Se ha completado la **Fase 2** del proyecto, implementando el parser robusto de Markdown y el gestor de grafos de conocimiento basado en NetworkX. Se han incorporado pruebas unitarias completas y herramientas de validación sobre documentos reales del SGD.

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
Esta versión inicial establece las bases conceptuales, arquitectónicas y de gobernanza para el desarrollo del sistema **Graph RAG para el Sistema de Gestión Documental (SGD)**. Define los principios rectores orientados a la privacidad y soberanía de datos (*on-premise*), así como la integración híbrida de grafos de conocimiento y recuperación vectorial.

### ✨ Novedades y Componentes Incluidos
- **Directrices de Desarrollo (`AGENTS.md`):** Normas técnicas para la colaboración entre el Guía y el Agente de Programación, priorizando la simplicidad, eficiencia y preservación del contexto estructural de los documentos Markdown.
- **Definición de Arquitectura (`docs/architecture_mindmap.mmd` & `docs/graph_rag_sgd_mindmap.svg`):** Esquema modular detallado de los cuatro pilares del sistema:
  1. Ingesta y Procesamiento (Parser Markdown, Frontmatter, Chunking Estructural, Grafo NetworkX).
  2. Indexación y Almacenamiento (Embeddings locales, Base de Datos Vectorial, Metadatos).
  3. Motor de Recuperación Híbrido (Búsqueda semántica densa + expansión relacional en grafo + re-ranking).
  4. Capa de Generación e Interfaz (LLM local, API/Interfaz de consulta).
- **Documentación de Entrada (`README.md`):** Guía general del proyecto, arquitectura visual en Mermaid, estructura del repositorio y **guía detallada de despliegue y pruebas** para entornos de desarrollo y producción *on-premise*.

### 🎯 Próximos Pasos (v0.2.0)
- Desarrollo del script de ingesta en Python para lectura de archivos Markdown del SGD.
- Extracción automatizada de metadatos YAML frontmatter y enlaces cruzados tipo wiki (`[[enlace]]`).
- Construcción inicial del grafo de relaciones utilizando NetworkX.
