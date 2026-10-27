import streamlit as st
import sys
from pathlib import Path

# Asegurar que el directorio raíz está en sys.path para importaciones absolutas de src
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.config import get_settings
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.retrieval.hybrid import HybridRetriever
from src.generation.local_llm import LocalLLMClient
from src.vectorstore.indexer import KnowledgeBaseIndexer
from src.ui.markdown_editor import render_markdown_editor
from src.documentation import DocumentationAgent

settings = get_settings()

st.set_page_config(
    page_title="Graph RAG para Base del Conocimiento - Interfaz Web On-Premise",
    page_icon="📚",
    layout="wide"
)

@st.cache_resource
def init_rag_components():
    vector_store = VectorStoreManager(persist_directory=settings.vector_store_dir)
    graph_manager = KnowledgeGraphManager(persist_path=settings.graph_persist_path)
    retriever = HybridRetriever(vector_store=vector_store, graph_manager=graph_manager)
    return vector_store, graph_manager, retriever

vector_store, graph_manager, retriever = init_rag_components()

st.title("📚 Graph RAG para Base del Conocimiento")
st.markdown("Recuperación Aumentada por Grafo de Conocimiento y Búsqueda Vectorial (*On-Premise*)")

tab_chat, tab_editor, tab_doc = st.tabs(["💬 Asistente Base del Conocimiento", "📝 Editor Documentos", "📄 Documentar Incidencia"])

with tab_chat:
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración del Sistema")
        
        backend = st.selectbox("Backend LLM", ["llamacpp", "ollama"], index=0 if settings.llm_backend == "llamacpp" else 1)
        base_url = st.text_input("URL Base del LLM", value=settings.llm_base_url)
        timeout = st.slider("Timeout (segundos)", 30, settings.api_max_timeout, settings.llm_timeout)
        
        st.markdown("---")
        top_k = st.slider("Fragmentos Top-K", 1, 20, settings.default_top_k)
        graph_radius = st.slider("Radio del Grafo", 0, 5, settings.default_graph_radius)
        
        st.markdown("---")
        st.subheader("🔄 Ingesta / Indexación")
        if st.button("Ejecutar Indexación Base del Conocimiento", type="primary"):
            with st.spinner("Indexando documentos Markdown y actualizando grafo..."):
                try:
                    indexer = KnowledgeBaseIndexer(data_dir=settings.data_dir, vector_dir=settings.vector_store_dir)
                    total = indexer.run_indexing()
                    # Recargar grafo persistido en la instancia cacheada
                    graph_manager.load_from_json(settings.graph_persist_path)
                    st.success(f"¡Indexación completada! Chunks procesados: {total}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en indexación: {e}")

        st.markdown("---")
        st.info(f"📊 Estadísticas del Grafo:\n- Nodos: {len(graph_manager.graph.nodes)}\n- Relaciones: {len(graph_manager.graph.edges)}")

    # Sección principal de Chat / Consultas
    st.subheader("💬 Asistente de Consultas de la Base del Conocimiento")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message and message["sources"]:
                with st.expander("🔍 Fuentes y Referencias de la Base del Conocimiento"):
                    seen_sources = set()
                    for src in message["sources"]:
                        meta = src.get("metadata", {})
                        title = meta.get('title', 'N/A')
                        source_path = meta.get('source_path', 'N/A')
                        source_key = (title, source_path)
                        if source_key in seen_sources:
                            continue
                        seen_sources.add(source_key)
                        st.write(f"- **{title}** (`{source_path}`)")

    if prompt := st.chat_input("Escribe tu pregunta sobre la Base del Conocimiento..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Buscando en vector store y grafo de conocimiento y generando respuesta..."):
                try:
                    contexts = retriever.retrieve(prompt, top_k=top_k, graph_radius=graph_radius)
                    llm = LocalLLMClient(
                        backend=backend,
                        base_url=base_url,
                        model_name=settings.llm_model_name,
                        timeout=timeout,
                        max_retries=settings.llm_max_retries,
                        base_delay=settings.llm_base_delay,
                        n_predict=settings.llm_n_predict,
                        temperature=settings.llm_temperature,
                        repeat_penalty=settings.llm_repeat_penalty,
                    )
                    answer = llm.generate_response(prompt, contexts)
                    
                    st.markdown(answer)
                    if contexts:
                        with st.expander("🔍 Fuentes y Referencias de la Base del Conocimiento"):
                            seen_sources = set()
                            for src in contexts:
                                meta = src.get("metadata", {})
                                title = meta.get('title', 'N/A')
                                source_path = meta.get('source_path', 'N/A')
                                source_key = (title, source_path)
                                if source_key in seen_sources:
                                    continue
                                seen_sources.add(source_key)
                                st.write(f"- **{title}** (`{source_path}`)")
                                
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": contexts
                    })
                except Exception as e:
                    err_msg = f"Error al procesar la consulta: {e}"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": err_msg, "sources": []})

with tab_editor:
    render_markdown_editor()

with tab_doc:
    st.subheader("📄 Documentar Incidencia")
    st.markdown(
        "Entrega el **caso**, las **pruebas** y la **resolución** de una incidencia. "
        "El agente, con ayuda del LLM local, organiza la información en el esquema de "
        "frontmatter del proyecto y la guarda como archivo Markdown en `data/incidencias/`."
    )

    # Configuración del LLM para esta pestaña (valores por defecto de settings)
    with st.expander("⚙️ Configuración del LLM", expanded=False):
        doc_backend = st.selectbox(
            "Backend LLM",
            ["llamacpp", "ollama"],
            index=0 if settings.llm_backend == "llamacpp" else 1,
            key="doc_backend",
        )
        doc_base_url = st.text_input(
            "URL Base del LLM",
            value=settings.llm_base_url,
            key="doc_base_url",
        )
        doc_timeout = st.slider(
            "Timeout (segundos)",
            30,
            settings.api_max_timeout,
            settings.llm_timeout,
            key="doc_timeout",
        )
        doc_temperature = st.slider(
            "Temperatura",
            0.0,
            1.0,
            0.2,
            0.1,
            key="doc_temperature",
        )
        doc_n_predict = st.slider(
            "Máx. tokens (n_predict)",
            64,
            4096,
            1024,
            64,
            key="doc_n_predict",
        )

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        caso = st.text_area(
            "📋 Caso del incidente",
            height=180,
            placeholder="Describe qué ocurrió, qué servicio/cliente se vio afectado, síntomas observados...",
            key="doc_caso",
        )
    with col2:
        pruebas = st.text_area(
            "🔬 Pruebas realizadas",
            height=180,
            placeholder="Capturas de tráfico, comandos ejecutados, logs, resultados de diagnósticos...",
            key="doc_pruebas",
        )

    resolucion = st.text_area(
        "✅ Resolución aplicada",
        height=180,
        placeholder="Qué se hizo para resolver el incidente, solución definitiva, workaround, configuraciones cambiadas...",
        key="doc_resolucion",
    )

    col_save, col_over = st.columns(2)
    with col_save:
        write_file = st.checkbox(
            "Guardar archivo en data/incidencias/",
            value=True,
            key="doc_write_file",
        )
    with col_over:
        overwrite = st.checkbox(
            "Sobreescribir si ya existe",
            value=False,
            key="doc_overwrite",
        )

    if st.button("🤖 Organizar con el LLM local", type="primary", key="doc_organize"):
        if not (caso and pruebas and resolucion):
            st.error("Por favor, rellena caso, pruebas y resolución antes de organizar.")
        else:
            with st.spinner("Contactando al LLM local y organizando la incidencia..."):
                try:
                    agent = DocumentationAgent(
                        backend=doc_backend,
                        base_url=doc_base_url,
                        timeout=doc_timeout,
                        temperature=doc_temperature,
                        n_predict=doc_n_predict,
                    )
                    result = agent.run(
                        caso=caso,
                        pruebas=pruebas,
                        resolucion=resolucion,
                        write_file=write_file,
                        overwrite=overwrite,
                    )

                    st.success("✅ Incidencia organizada correctamente")

                    fm = result.frontmatter
                    st.markdown("### 📋 Resultado organizado")

                    meta_col1, meta_col2, meta_col3 = st.columns(3)
                    with meta_col1:
                        st.write(f"**ID:** {fm.id}")
                        st.write(f"**Título:** {fm.title}")
                        st.write(f"**Sistema:** {fm.sistema}")
                    with meta_col2:
                        st.write(f"**Categoría:** {fm.categoria}")
                        st.write(f"**Criticidad:** {fm.criticidad}")
                        st.write(f"**Tipo:** {fm.tipo}")
                    with meta_col3:
                        st.write(f"**Clientes:** {', '.join(fm.clientes_afectados) or '(ninguno)'}")
                        st.write(f"**Tags:** {', '.join(fm.tags) or '(ninguno)'}")
                        st.write(f"**F. detección:** {fm.fecha_deteccion}")
                        st.write(f"**F. actualización:** {fm.fecha_actualizacion}")

                    st.markdown("### 📄 Cuerpo Markdown")
                    st.code(result.body, language="markdown")

                    if result.file_path:
                        st.info(f"💾 Archivo guardado en: `{result.file_path}`")
                        st.markdown(
                            "Para que el grafo y el vector store lo recojan, ejecuta la indexación:"
                        )
                        st.code(
                            "PYTHONPATH=. python3 -m src.vectorstore.indexer",
                            language="bash",
                        )

                    with st.expander("🔍 Salida cruda del LLM (JSON)"):
                        st.code(result.raw_llm_output or "(no disponible)", language="json")

                except Exception as e:
                    st.error(f"Error al organizar la incidencia: {e}")