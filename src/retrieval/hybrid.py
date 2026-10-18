from typing import List, Dict, Any, Optional
import hashlib
from src.config import get_settings
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager

class HybridRetriever:
    """Motor de Recuperación Híbrida (Vectorial + Expansión de Contexto en Grafo)."""

    MAX_CONTEXTS_PER_SOURCE = 10

    def __init__(self, vector_store: VectorStoreManager, graph_manager: KnowledgeGraphManager):
        self.vector_store = vector_store
        self.graph_manager = graph_manager
        self.max_contexts = get_settings().default_top_k

    def _content_hash(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def retrieve(self, query: str, top_k: int = 4, graph_radius: int = 1) -> List[Dict[str, Any]]:
        try:
            vector_results = self.vector_store.similarity_search(query, top_k=top_k)
        except Exception:
            vector_results = []

        # Búsqueda por palabra clave para términos técnicos que embeddings no captan bien
        keywords = self._extract_keywords(query)
        keyword_results = []
        if keywords:
            try:
                keyword_results = self.vector_store.keyword_search(keywords, top_k=top_k)
            except Exception:
                keyword_results = []

        retrieved_contexts = []
        seen_chunk_ids = set()
        seen_content_hashes = set()
        source_count = {}

        def _add_context(entry: Dict[str, Any]) -> bool:
            content = entry.get("content", "")
            content_hash = self._content_hash(content)
            chunk_id = entry.get("chunk_id", "")
            source_path = entry.get("metadata", {}).get("source_path", "")
            if chunk_id in seen_chunk_ids or content_hash in seen_content_hashes:
                return False
            if source_path and source_count.get(source_path, 0) >= self.MAX_CONTEXTS_PER_SOURCE:
                return False
            if len(retrieved_contexts) >= self.max_contexts:
                return False
            seen_chunk_ids.add(chunk_id)
            seen_content_hashes.add(content_hash)
            if source_path:
                source_count[source_path] = source_count.get(source_path, 0) + 1
            retrieved_contexts.append(entry)
            return True

        # Primero agregar resultados por palabra clave (más precisos para términos técnicos)
        for res in keyword_results:
            _add_context({
                "type": "keyword_hit",
                "chunk_id": res["chunk_id"],
                "content": res["content"],
                "metadata": res["metadata"],
                "distance": 0.0
            })

        # Luego agregar resultados vectoriales
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

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """Extrae palabras clave técnicas de la consulta para búsqueda por texto exacto."""
        import re
        # Patrones técnicos: IPs, nombres de puertos (XGE1/0/25), VLANs, alfanuméricos con símbolos
        keywords = set()

        # Buscar patrones como XGE1/0/25, VLAN184, 172.217.114.4, etc.
        tech_patterns = re.findall(r'\b[A-Z]{2,}[A-Z0-9_/.-]*\b', query)
        keywords.update(tech_patterns)

        # Buscar palabras de 4+ caracteres que no sean stopwords comunes en español
        stopwords = {'que', 'cual', 'cuales', 'como', 'donde', 'cuando', 'porque', 'para',
                     'con', 'por', 'del', 'de', 'la', 'las', 'los', 'el', 'un', 'una', 'y',
                     'o', 'a', 'en', 'se', 'ha', 'han', 'ha', 'fue', 'fueron', 'está', 'están',
                     'qué', 'cuál', 'cuáles', 'cómo', 'dónde', 'cuándo', 'por qué'}
        words = re.findall(r'\b[a-záéíóúñ]{4,}\b', query.lower())
        keywords.update(w for w in words if w not in stopwords)

        return list(keywords)
