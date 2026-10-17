from typing import List, Dict, Any, Optional
import hashlib
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager

class HybridRetriever:
    """Motor de Recuperación Híbrida (Vectorial + Expansión de Contexto en Grafo)."""

    MAX_CONTEXTS = 4
    MAX_CONTEXTS_PER_SOURCE = 1

    def __init__(self, vector_store: VectorStoreManager, graph_manager: KnowledgeGraphManager):
        self.vector_store = vector_store
        self.graph_manager = graph_manager

    def _content_hash(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def retrieve(self, query: str, top_k: int = 4, graph_radius: int = 1) -> List[Dict[str, Any]]:
        try:
            vector_results = self.vector_store.similarity_search(query, top_k=top_k)
        except Exception:
            vector_results = []

        retrieved_contexts = []
        seen_chunk_ids = set()
        seen_content_hashes = set()
        seen_source_paths = set()

        def _add_context(entry: Dict[str, Any]) -> bool:
            content = entry.get("content", "")
            content_hash = self._content_hash(content)
            chunk_id = entry.get("chunk_id", "")
            source_path = entry.get("metadata", {}).get("source_path", "")
            if chunk_id in seen_chunk_ids or content_hash in seen_content_hashes:
                return False
            if source_path and source_path in seen_source_paths:
                return False
            if len(retrieved_contexts) >= self.MAX_CONTEXTS:
                return False
            seen_chunk_ids.add(chunk_id)
            seen_content_hashes.add(content_hash)
            if source_path:
                seen_source_paths.add(source_path)
            retrieved_contexts.append(entry)
            return True

        for res in vector_results:
            _add_context({
                "type": "vector_hit",
                "chunk_id": res["chunk_id"],
                "content": res["content"],
                "metadata": res["metadata"],
                "distance": res.get("distance", 0.0)
            })

            meta = res.get("metadata", {})
            source_path = meta.get("source_path", "")
            doc_id = meta.get("title", "")
            
            if doc_id and self.graph_manager.graph.has_node(doc_id):
                neighbors = self.graph_manager.get_neighbors(doc_id, radius=graph_radius)
                for neighbor in neighbors:
                    neighbor_data = self.graph_manager.graph.nodes.get(neighbor, {})
                    neighbor_title = neighbor_data.get("title", neighbor)
                    
                    try:
                        neighbor_chunks = self.vector_store.get_chunks_by_doc_title(neighbor_title, limit=3)
                        for nc in neighbor_chunks:
                            _add_context({
                                "type": "graph_expansion",
                                "chunk_id": nc["chunk_id"],
                                "content": nc["content"],
                                "metadata": nc["metadata"],
                                "distance": 0.0
                            })
                    except Exception:
                        neighbor_path = neighbor_data.get("source_path", "")
                        if neighbor_path and neighbor_path != source_path:
                            entry = {
                                "type": "graph_expansion",
                                "chunk_id": f"graph-neighbor-{neighbor}",
                                "content": f"[Documento Relacionado en Grafo: {neighbor_title}]",
                                "metadata": neighbor_data,
                                "distance": 0.0
                            }
                            _add_context(entry)

        return retrieved_contexts
