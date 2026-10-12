from typing import List, Dict, Any, Optional
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager

class HybridRetriever:
    """Motor de Recuperación Híbrida (Vectorial + Expansión de Contexto en Grafo)."""

    def __init__(self, vector_store: VectorStoreManager, graph_manager: KnowledgeGraphManager):
        self.vector_store = vector_store
        self.graph_manager = graph_manager

    def retrieve(self, query: str, top_k: int = 4, graph_radius: int = 1) -> List[Dict[str, Any]]:
        try:
            vector_results = self.vector_store.similarity_search(query, top_k=top_k)
        except Exception:
            vector_results = []

        retrieved_contexts = []
        seen_chunks = set()

        for res in vector_results:
            chunk_id = res["chunk_id"]
            if chunk_id not in seen_chunks:
                seen_chunks.add(chunk_id)
                retrieved_contexts.append({
                    "type": "vector_hit",
                    "chunk_id": chunk_id,
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
                    neighbor_path = neighbor_data.get("source_path", "")
                    if neighbor_path and neighbor_path != source_path:
                        retrieved_contexts.append({
                            "type": "graph_expansion",
                            "chunk_id": f"graph-neighbor-{neighbor}",
                            "content": f"[Documento Relacionado en Grafo: {neighbor}]",
                            "metadata": neighbor_data,
                            "distance": 0.0
                        })

        return retrieved_contexts
