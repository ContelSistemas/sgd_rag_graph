import asyncio
import sys
from functools import partial
from pathlib import Path
from typing import List, Dict, Any

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Select,
    Static,
)

from src.config import get_settings
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.retrieval.hybrid import HybridRetriever
from src.generation.local_llm import LocalLLMClient
from src.vectorstore.indexer import SGDIndexer


class GraphRAGTUI(App):
    CSS_PATH = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="sidebar", classes="panel"):
                yield Label("Configuracion")
                yield Select(
                    options=[("llamacpp", "llamacpp"), ("ollama", "ollama")],
                    value="llamacpp",
                    id="backend_select",
                )
                yield Input(placeholder="http://localhost:8080", id="base_url_input", value="http://localhost:8080")
                yield Input(placeholder="300", id="timeout_input", value="300")
                yield Input(placeholder=str(settings.default_top_k), id="top_k_input", value=str(settings.default_top_k))
                yield Input(placeholder="1", id="graph_radius_input", value="1")
                yield Static()
                yield Button("Indexar SGD", id="btn_index", variant="primary")
                yield Button("Limpiar chat", id="btn_clear", variant="default")
                yield Static(id="stats")
            with Vertical(id="center", classes="panel"):
                yield Log(id="chat_log", auto_scroll=True)
                yield Input(placeholder="Escribe tu pregunta sobre la documentación del SGD...", id="chat_input")
        yield Footer()

    def on_mount(self) -> None:
        settings = get_settings()
        self.vector_store = VectorStoreManager(persist_directory=settings.vector_store_dir)
        self.graph_manager = KnowledgeGraphManager(persist_path=settings.graph_persist_path)
        self.retriever = HybridRetriever(vector_store=self.vector_store, graph_manager=self.graph_manager)
        self.settings = settings
        self.messages: List[Dict[str, Any]] = []
        self._update_stats()
        self.query_one("#chat_input", Input).focus()

    def _update_stats(self) -> None:
        stats_widget = self.query_one("#stats", Static)
        stats_widget.update(
            f"Grafo: {self.graph_manager.graph.number_of_nodes()} nodos, "
            f"{self.graph_manager.graph.number_of_edges()} aristas"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_index":
            self.run_worker(self._index_worker, thread=True, exclusive=True)
        elif event.button.id == "btn_clear":
            log = self.query_one("#chat_log", Log)
            log.clear()
            self.messages = []

    def _index_worker(self) -> None:
        self.app.call_from_thread(self._index_log_write, "[Indexando documentos...]")
        try:
            indexer = SGDIndexer(data_dir=self.settings.data_dir, vector_dir=self.settings.vector_store_dir)
            total = indexer.run_indexing()
            self.graph_manager.load_from_json(self.settings.graph_persist_path)
            self.app.call_from_thread(self._update_stats)
            self.app.call_from_thread(self._index_log_write, f"[Indexacion completa: {total} chunks]")
        except Exception as e:
            self.app.call_from_thread(self._index_log_write, f"[Error indexacion: {e}]")

    def _index_log_write(self, msg: str) -> None:
        self.query_one("#chat_log", Log).write(msg)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat_input":
            return
        query = event.input.value.strip()
        if not query:
            return
        event.input.value = ""
        self.query_one("#chat_log", Log).write(f"[Tú] {query}")
        self.messages.append({"role": "user", "content": query})
        self.run_worker(partial(self._query_worker, query), thread=True, exclusive=True)

    def _query_worker(self, query: str) -> None:
        backend = self.query_one("#backend_select", Select).value
        base_url = self.query_one("#base_url_input", Input).value
        timeout = int(self.query_one("#timeout_input", Input).value or 300)
        top_k = int(self.query_one("#top_k_input", Input).value or 4)
        graph_radius = int(self.query_one("#graph_radius_input", Input).value or 1)

        self.app.call_from_thread(self._query_log_write, "[Generando respuesta...]")
        try:
            contexts = self.retriever.retrieve(query, top_k=top_k, graph_radius=graph_radius)
            llm = LocalLLMClient(
                backend=backend,
                base_url=base_url,
                model_name=self.settings.llm_model_name,
                timeout=timeout,
                max_retries=self.settings.llm_max_retries,
                base_delay=self.settings.llm_base_delay,
            )
            answer = llm.generate_response(query, contexts)
            self.app.call_from_thread(self._query_log_write, f"[Asistente] {answer}")
            if contexts:
                self.app.call_from_thread(self._query_log_write, "[Fuentes]")
                for src in contexts:
                    meta = src.get("metadata", {})
                    self.app.call_from_thread(
                        self._query_log_write,
                        f"- {meta.get('title', 'N/A')} ({meta.get('source_path', 'N/A')})",
                    )
            self.messages.append({"role": "assistant", "content": answer, "sources": contexts})
        except Exception as e:
            self.app.call_from_thread(self._query_log_write, f"[Error: {e}]")

    def _query_log_write(self, msg: str) -> None:
        self.query_one("#chat_log", Log).write(msg)


if __name__ == "__main__":
    app = GraphRAGTUI()
    app.run()
