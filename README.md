# Graph RAG para SGD (Sistema de Gestión Documental)

Sistema avanzado de Recuperación Aumentada por Generación (RAG) basado en Grafos de Conocimiento y Búsqueda Vectorial, diseñado específicamente para operar en entornos locales (*on-premise*) y asegurar la privacidad y soberanía de la documentación del Sistema de Gestión Documental (SGD).

---

## 📌 Características Principales

- **Privacidad y Soberanía Total:** Procesamiento, indexación y ejecución de modelos totalmente locales, sin dependencias de APIs en la nube.
- **Mantenimiento del Contexto Estructural:** Explotación de la topología documental subyacente en archivos Markdown (enlaces tipo wiki `[[enlace]]`, metadatos frontmatter y jerarquía de encabezados).
- **Recuperación Híbrida (Graph + Vector):**
  - **Búsqueda Vectorial Semántica:** Recuperación de fragmentos mediante similitud de coseno (dense retrieval) con embeddings ligeros locales.
  - **Búsqueda Relacional en Grafo:** Exploración de nodos vecinos en el grafo de conocimiento para rescatar contexto complementario y dependencias cruzadas.
- **Generación Local (LLM):** Integración con motores LLM locales para la síntesis de respuestas con referencias precisas a los ficheros originales del SGD.

---

## 🏗️ Arquitectura del Sistema

```mermaid
graph TD
    A[Documentos Markdown SGD] --> B[Ingesta y Procesamiento]
    B --> C[Parser de Markdown & Extracción Frontmatter]
    B --> D[Chunking Estructural por Encabezados]
    B --> E[Gestor de Grafo NetworkX / Wiki Links]
    
    C & D --> F[Indexación y Almacenamiento]
    E --> F
    F --> G[Embeddings Locales / Base Vectorial]
    
    H[Consulta del Usuario] --> I[Motor de Recuperación Híbrido]
    I --> J[Búsqueda Semántica Vectorial]
    I --> K[Expansión de Contexto en Grafo]
    J & K --> L[Fusión y Re-ranking]
    
    L --> M[Capa de Generación - LLM Local]
    M --> N[Respuesta con Referencias al SGD]
```

---

## 📂 Estructura del Proyecto

```text
grafrac/
├── config/              # Configuración centralizada (pydantic-settings)
├── data/                # Documentos del SGD y persistencia local
├── docs/                # Documentación y esquemas (mindmap, SVG)
├── src/                 # Código fuente (ingestion, graph, vectorstore, retrieval, generation, api, ui, config)
├── tests/               # Pruebas unitarias e integración
├── requirements.txt     # Dependencias de Python
├── README.md            # Documentación principal
└── release.md           # Notas de versión
```

---

## ⚙️ Despliegue y Pruebas (Dev & Producción)

### 1. Entorno de Desarrollo (Dev)

Para configurar y probar el proyecto en un entorno local de desarrollo:

1. **Clonar el repositorio y acceder al directorio:**
   ```bash
   cd grafrac
   ```
2. **Crear y activar un entorno virtual de Python:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Instalar las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configurar el entorno:**
   - Coloca los archivos Markdown de tu SGD en el directorio `data/` o configura la ruta en `config/`.
5. **Ejecutar pruebas unitarias:**
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```

### 5.5. Configuración por Variables de Entorno (`.env`)

El sistema lee su configuración desde un archivo `.env` en la raíz del proyecto (ignorado en git vía `.gitignore`). Copia `.env.example` a `.env` y ajusta los valores según tu entorno:

```bash
cp .env.example .env
# Edita .env con tu editor preferido
PYTHONPATH=. pytest tests/ -v
```

Todas las variables están centralizadas en `src/config/settings.py` (pydantic-settings) y se cargan automáticamente al iniciar cualquier componente (`LocalLLMClient`, `VectorStoreManager`, `KnowledgeGraphManager`, `SGDIndexer`, etc.).

### 6. Ejecución de la TUI Textual (Interfaz de Terminal)

Como alternativa a la interfaz web Streamlit, el proyecto incluye una TUI basada en [Textual](https://textual.textualize.io/) que reusa los mismos componentes de negocio (grafo, vector store, retriever, LLM):

```bash
python3 src/ui/tui.py
```

La TUI incluye chat interactivo, barra lateral de configuración (backend, URL, timeout, top-k, radio de grafo), botón de indexación SGD y estadísticas del grafo. No requiere servidor web y se ejecuta directamente en la terminal.

### 7. Ejecución del Chat CLI Interactivo (Fase 7)

Para realizar consultas conversacionales interactivas directamente desde la terminal utilizando el motor de recuperación híbrida y el LLM local:

```bash
python3 run_chat.py llamacpp http://localhost:8080
```

### 8. Ejecución de la Interfaz Web Visual (Streamlit - Fase 8A)

Para iniciar la interfaz gráfica de usuario web para consultas interactivas, configuración y reindexación:

```bash
streamlit run src/ui/app.py
```

Para levantar el servidor API REST en local y exponer los endpoints de consulta híbrida y indexación:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --ws none
```

Endpoints disponibles:
- `GET /health`: Estado de salud del servicio.
- `POST /index`: Ejecuta la indexación de los documentos del SGD.
- `POST /query`: Realiza una consulta híbrida (vectorial + grafo) y síntesis con LLM local.


Para ejecutar la demostración completa del sistema (Fase 5) indexando la documentación del SGD, realizando recuperación híbrida y consultando al LLM local (ej. Llama.cpp en `http://localhost:8080`):

```bash
python3 run_demo.py
```

Para realizar consultas personalizadas o pruebas puntuales con el cliente LLM local especificando un tiempo de espera (`timeout`):

```bash
python3 -c "
from src.generation.local_llm import LocalLLMClient

llm = LocalLLMClient(backend='llamacpp', base_url='http://localhost:8080', timeout=300)
context = [{
    'content': 'La OLT1 se bloqueó a las 03:45 AM del 12 de octubre de 2026 debido a un fallo de alimentación en el rack principal.',
    'metadata': {'title': 'Registro de Incidencias OLT', 'source_path': 'data/incidencias_red.md'}
}]
response = llm.generate_response('¿Cuándo se bloqueó la OLT1?', context)
print('Respuesta:\n', response)
"
```


### 2. Entorno de Producción (Host Definitivo On-Premise)

Para el despliegue definitivo en el servidor local de producción asegurando la soberanía de datos:

1. **Requisitos del Servidor:**
   - Sistema operativo Linux (Ubuntu/Debian recomendado) u otro entorno compatible.
   - Python 3.10 o superior instalado.
    - [Ollama](https://ollama.com/) o **[llama.cpp](https://github.com/ggerganov/llama.cpp)** (servidor nativo `llama-server`) para la inferencia de LLM local on-premise.
      - **Con Ollama:**
        ```bash
        curl -fsSL https://ollama.com/install.sh | sh
        ollama serve &
        ollama pull llama3
        ```
      - **Con llama.cpp (Servidor Nativo):**
        ```bash
        # Para entornos con recursos limitados (recomendado para pruebas locales):
        llama-server -hf ggml-org/gemma-3-1b-it-GGUF -c 2048 --port 8080
        
        # Para producción con mayor hardware:
        llama-server -hf bartowski/Qwen2.5-3B-Instruct-GGUF:Q4_K_S -c 4096 --port 8080
        ```
         *Nota:* El cliente `LocalLLMClient` en `src/generation/local_llm.py` soporta ambos backends configurando `backend="ollama"` o `backend="llamacpp"`. Permite configurar el tiempo de espera mediante el parámetro `timeout` (por defecto 300 segundos):
         ```python
         client = LocalLLMClient(backend="llamacpp", base_url="http://localhost:8080", timeout=300)
         ```
2. **Clonación y Configuración en Producción:**
   ```bash
   git clone <url-repositorio> grafrac
   cd grafrac
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Persistencia y Permisos (⚠️ IMPORTANTE para Producción):**
   - Asegurar permisos de lectura y escritura en la carpeta `data/` (para evitar errores de base de datos de lectura en ChromaDB y el grafo JSON):
     ```bash
     sudo chown -R $USER:$USER data/
     ```
4. **Ejecución como Servicio (Systemd):**
   Crear un archivo de servicio en `/etc/systemd/system/grafrac.service`:
   ```ini
   [Unit]
   Description=Graph RAG para SGD
   After=network.target ollama.service

   [Service]
   User=tu_usuario
   WorkingDirectory=/ruta/a/grafrac
   ExecStart=/ruta/a/grafrac/venv/bin/python main.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Habilitar y arrancar el servicio:
   ```bash
   sudo systemctl enable --now grafrac.service
   ```

---

## 🖥️ Optimización para Hardware Limitado (CPU solo, sin GPU)

El sistema está preparado para ejecutarse exclusivamente en CPU con modelos ultraligeros. Para entornos con recursos limitados:

### Modelo LLM recomendado (1B)
Lanza `llama-server` con Gemma 3 1B cuantificado:

```bash
# Modelo ligero, ideal para CPU sin GPU
llama-server -hf ggml-org/gemma-3-1b-it-Q4_K_M-GGUF -c 2048 --port 8080
```

Luego consulta:
```bash
python3 run_chat.py llamacpp http://localhost:8080
```

### Parámetros por defecto optimizados (`src/config/settings.py`)
| Parámetro | Valor | Efecto |
|-----------|-------|--------|
| `llm_model_name` | `gemma-3-1b-it` | Modelo 1B, bajo consumo de RAM/CPU |
| `llm_n_predict` | 256 | Máximo de tokens generados por respuesta |
| `llm_temperature` | 0.3 | Menor variación, respuestas más deterministas |
| `llm_ctx_size` | 2048 | Ventana de contexto reducida |
| `default_top_k` | 3 | Menos fragmentos recuperados por consulta |
| `MAX_CONTEXTS` (retriever) | 6 | Tope de contextos enviados al LLM |

### Deduplicación de contextos
Cada consulta elimina automáticamente fragmentos repetidos (por `chunk_id` y por hash de contenido) tanto de la búsqueda vectorial como de la expansión de grafo, evitando respuestas "corta-pega" y fuentes duplicadas.

---

## 🚀 Hoja de Ruta

1. **Fase 1:** Diseño arquitectónico, directrices y estructuración documental. *(Completado)*
2. **Fase 2:** Implementación del Parser de Markdown, extracción de enlaces wiki y construcción del grafo con NetworkX. *(Completado)*
3. **Fase 3:** Configuración del sistema de chunking jerárquico y almacenamiento vectorial local. *(Completado)*
4. **Fase 4:** Desarrollo del motor de recuperación híbrida (Vector + Grafo) y conexión con LLM local. *(Completado)*
5. **Fase 5:** Pruebas de integración sobre documentación real del SGD y optimización de rendimiento. *(Completado)*
6. **Fase 6:** Capa de Servicio (API REST con FastAPI) y Orquestación. *(Completado)*
7. **Fase 7:** Persistencia del Grafo, Interfaz de Chat CLI Interactiva y Contenerización Docker/Docker Compose. *(Completado)*
8. **Fase 8A:** Interfaz Web Visual con Streamlit y Panel de Control. *(Completado)*
9. **Sprint 1 (v0.9.0):** Mejoras Core - Graph Expansion real, LLM Retry/Backoff, Config Centralizada. *(Completado)*
10. **Sprint 1.1 (v0.9.1):** TUI Textual, Configuración `.env` y Soporte Multi-Interfaz. *(Completado)*
11. **Sprint 1.2 (v0.9.2):** Modelo Ligero 1B, Deduplicación de Contextos y Optimización para Hardware Limitado. *(Completado)*
