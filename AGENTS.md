# Directrices de Desarrollo y Criterios Arquitectónicos - Graph RAG para SGD

Este documento establece las normas, los objetivos y la hoja de ruta técnica que regirán la colaboración entre el Guía (Tú) y el Agente de Programación (Yo) en el desarrollo del sistema Graph RAG para el Sistema de Gestión Documental (SGD).

---

## 1. Principios Rectores

* **Privacidad y Soberanía de Datos:** Todo el procesamiento, vectorización, indexación y almacenamiento del grafo debe realizarse en entornos locales (on-premise), sin depender de APIs de terceros en la nube, garantizando la seguridad de la documentación del SGD.
* **Simplicidad y Eficiencia:** Priorizamos arquitecturas ligeras. Evitaremos dependencias bloated o bases de datos pesadas en la fase inicial, optando por herramientas modulares que escalen de forma limpia.
* **Mantenimiento del Contexto Estructural:** Los documentos en Markdown de tu SGD poseen relaciones intrínsecas (enlaces wiki `[[enlace]]`, frontmatter, jerarquías de encabezados). El sistema debe preservar y explotar esta topología mediante un grafo de conocimiento subyacente.

---

## 2. Puntos Clave de la Arquitectura

### A. Ingestión y Análisis Estructural
- **Parser de Markdown:** Lectura automatizada de archivos Markdown (`.md`) extrayendo metadatos YAML (frontmatter), jerarquía de títulos y enlaces cruzados.
- **Grafo de Conocimiento:** Construcción de una red relacional utilizando estructuras locales (ej. NetworkX o SQLite estructurado) basada en los enlaces y categorías del SGD.

### B. Indexación y Recuperación Híbrida (Graph + Vector)
- **Chunking Jerárquico:** Fragmentación de textos respetando los límites de los encabezados (`#`, `##`, `###`) para evitar la pérdida de contexto semántico.
- **Búsqueda Vectorial:** Empleo de modelos de *embeddings* ligeros ejecutados localmente.
- **Recuperación en Grafo:** Estrategia de expansión de contexto: a partir de los documentos encontrados por similitud semántica, el motor explorará nodos vecinos en el grafo para rescatar documentación complementaria.

### C. Generación (LLM Local)
- Conexión con un motor LLM local para la síntesis de respuestas basadas exclusivamente en el contexto recuperado, devolviendo referencias claras a los ficheros originales del SGD.

---

## 3. Flujo de Trabajo y Colaboración

1. **Definición de Tareas:** El Guía establece la prioridad del próximo bloque funcional.
2. **Generación de Código:** El Agente implementa los componentes modulares en scripts limpios de Python o contenedores Docker optimizados.
3. **Iteración y Pruebas:** Se validan los resultados, ajustando parámetros (tamaño de chunk, solapamiento, umbrales de similitud) según el comportamiento real sobre la documentación de tu SGD.

---

*Última actualización:* Fase 8A completada (Interfaz Web Visual con Streamlit y Panel de Control).