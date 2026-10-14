import streamlit as st
import sys
from pathlib import Path

# Asegurar que el directorio raíz está en sys.path para importaciones absolutas de src
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.retrieval.hybrid import HybridRetriever
from src.generation.local_llm import LocalLLMClient
from src.vectorstore.indexer import SGDIndexer
from src.ui.markdown_editor import render_markdown_editor

st.set_page_config(
    page_title="Graph RAG para SGD - Interfaz Web On-Premise",
    page_icon="📚",
    layout="wide"
)

@st.cache_resource
def init_rag_components():
    vector_store = VectorStoreManager(persist_directory="data/vectorstore")
    graph_manager = KnowledgeGraphManager(persist_path="data/knowledge_graph.json")
    retriever = HybridRetriever(vector_store=vector_store, graph_manager=graph_manager)
    return vector_store, graph_manager, retriever

vector_store, graph_manager, retriever = init_rag_components()

st.title("📚 Graph RAG para Sistema de Gestión Documental (SGD)")
st.markdown("Recuperación Aumentada por Grafo de Conocimiento y Búsqueda Vectorial (*On-Premise*)")

tab_chat, tab_editor = st.tabs(["💬 Asistente SGD", "📝 Editor Documentos"])

with tab_chat:
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración del Sistema")
        
        backend = st.selectbox("Backend LLM", ["llamacpp", "ollama"], index=0)
        base_url = st.text_input("URL Base del LLM", value="http://localhost:8080")
        timeout = st.slider("Timeout (segundos)", 30, 600, 300)
        
        st.markdown("---")
        top_k = st.slider("Fragmentos Top-K", 1, 10, 3)
        graph_radius = st.slider("Radio del Grafo", 0, 3, 1)
        
        st.markdown("---")
        st.subheader("🔄 Ingesta / Indexación")
        if st.button("Ejecutar Indexación SGD", type="primary"):
            with st.spinner("Indexando documentos Markdown y actualizando grafo..."):
                try:
                    indexer = SGDIndexer(data_dir="data", vector_dir="data/vectorstore")
                    total = indexer.run_indexing()
                    st.success(f"¡Indexación completada! Chunks procesados: {total}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en indexación: {e}")

        st.markdown("---")
        st.info(f"📊 Estadísticas del Grafo:\n- Nodos: {len(graph_manager.graph.nodes)}\n- Relaciones: {len(graph_manager.graph.edges)}")

    # Sección principal de Chat / Consultas
    st.subheader("💬 Asistente de Consultas del SGD")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message and message["sources"]:
                with st.expander("🔍 Fuentes y Referencias del SGD"):
                    for src in message["sources"]:
                        meta = src.get("metadata", {})
                        st.write(f"- **{meta.get('title', 'N/A')}** (`{meta.get('source_path', 'N/A')}`)")

    if prompt := st.chat_input("Escribe tu pregunta sobre la documentación del SGD..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Buscando en vector store y grafo de conocimiento y generando respuesta..."):
                try:
                    contexts = retriever.retrieve(prompt, top_k=top_k, graph_radius=graph_radius)
                    llm = LocalLLMClient(backend=backend, base_url=base_url, timeout=timeout)
                    answer = llm.generate_response(prompt, contexts)
                    
                    st.markdown(answer)
                    if contexts:
                        with st.expander("🔍 Fuentes y Referencias del SGD"):
                            for src in contexts:
                                meta = src.get("metadata", {})
                                st.write(f"- **{meta.get('title', 'N/A')}** (`{meta.get('source_path', 'N/A')}`)")
                                
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