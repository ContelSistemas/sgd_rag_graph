from typing import List, Dict, Any, Optional, Set
import hashlib
import re
from src.config import get_settings
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager

class HybridRetriever:
    """Motor de Recuperación Híbrida (Vectorial + Expansión de Contexto en Grafo)."""

    MAX_CONTEXTS_PER_SOURCE = 5
    MAX_DISTINCT_SOURCES = 4
    MAX_DISTINCT_SOURCES_WITH_CLIENT = 2

    def __init__(self, vector_store: VectorStoreManager, graph_manager: KnowledgeGraphManager):
        self.vector_store = vector_store
        self.graph_manager = graph_manager
        self.max_contexts = get_settings().default_top_k
        self._client_slugs: Optional[Set[str]] = None

    def _content_hash(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _discover_client_slugs(self) -> Set[str]:
        """Descubre los slugs de cliente disponibles en el vector store a partir de las rutas de archivo."""
        if self._client_slugs is not None:
            return self._client_slugs
        slugs: Set[str] = set()
        try:
            # Obtener una muestra de documentos para extraer rutas
            results = self.vector_store.collection.get(limit=500)
            if results and results.get("metadatas"):
                for meta in results["metadatas"]:
                    sp = meta.get("source_path", "") or ""
                    m = re.search(r'data/clientes/([^/]+)/', sp)
                    if m:
                        slugs.add(m.group(1))
        except Exception:
            pass
        self._client_slugs = slugs
        return slugs

    def _detect_client_in_query(self, query: str) -> Optional[str]:
        """Detecta si la consulta menciona un cliente específico y devuelve su slug."""
        slugs = self._discover_client_slugs()
        if not slugs:
            return None
        q_lower = query.lower()
        # 1. Coincidencia exacta del slug (ej. "hotel_villa_cortes" en la consulta)
        for slug in sorted(slugs, key=len, reverse=True):
            if slug.lower() in q_lower:
                return slug
        # 2. Coincidencia de palabras significativas del slug (ej. "villa cortes" → hotel_villa_cortes)
        stop_slug_words = {'hotel', 'cliente', 'base', 'conocimiento', 'red', 'central', 'sistema', 'los', 'parque'}
        for slug in sorted(slugs, key=len, reverse=True):
            parts = slug.replace('_', ' ').split()
            significant = [p for p in parts if len(p) > 3 and p not in stop_slug_words]
            if significant and all(p in q_lower for p in significant):
                return slug
        return None

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
                keyword_results = self.vector_store.keyword_search(keywords, top_k=top_k * 3)
            except Exception:
                keyword_results = []

        retrieved_contexts = []
        seen_chunk_ids = set()
        seen_content_hashes = set()
        source_count = {}

        # Detectar si la consulta menciona un cliente específico
        detected_client = self._detect_client_in_query(query)

        def _client_match(source_path: str) -> bool:
            if not detected_client or not source_path:
                return False
            return detected_client in source_path

        def _is_client_result(entry: Dict[str, Any]) -> bool:
            sp = entry.get("metadata", {}).get("source_path", "")
            return _client_match(sp)

        def _is_placeholder(content: str) -> bool:
            """Detecta chunks que solo contienen comentarios de placeholder sin información real."""
            stripped = content.strip()
            # Si el contenido solo tiene el comentario de relleno y poco más, es un placeholder
            if "<!-- Rellena aquí" in stripped:
                # Quitar el comentario y ver si queda algo significativo
                cleaned = re.sub(r'<!--.*?-->', '', stripped, flags=re.DOTALL).strip()
                # También quitar encabezados markdown vacíos
                cleaned = re.sub(r'#+\s*.*', '', cleaned).strip()
                cleaned = re.sub(r'\*\*.*?\*\*', '', cleaned).strip()
                if len(cleaned) < 20:
                    return True
            return False

        def _add_context(entry: Dict[str, Any]) -> bool:
            content = entry.get("content", "")
            content_hash = self._content_hash(content)
            chunk_id = entry.get("chunk_id", "")
            source_path = entry.get("metadata", {}).get("source_path", "")
            if chunk_id in seen_chunk_ids or content_hash in seen_content_hashes:
                return False
            if source_path and source_count.get(source_path, 0) >= self.MAX_CONTEXTS_PER_SOURCE:
                return False
            # Filtrar placeholders vacíos (excepto si es el único resultado del cliente)
            if _is_placeholder(content):
                return False
            if len(retrieved_contexts) >= self.max_contexts:
                return False
            seen_chunk_ids.add(chunk_id)
            seen_content_hashes.add(content_hash)
            if source_path:
                source_count[source_path] = source_count.get(source_path, 0) + 1
            retrieved_contexts.append(entry)
            return True

        # Separar resultados en cliente detectado y otros
        client_results: List[Dict[str, Any]] = []
        other_results: List[Dict[str, Any]] = []

        for res in keyword_results:
            if detected_client and _is_client_result(res):
                client_results.append(res)
            else:
                other_results.append(res)

        for res in vector_results:
            if detected_client and _is_client_result(res):
                client_results.append(res)
            else:
                other_results.append(res)

        # 1. Primero: TODOS los resultados del cliente detectado (prioridad absoluta)
        for res in client_results:
            entry = {
                "type": res.get("type", "client_hit"),
                "chunk_id": res["chunk_id"],
                "content": res["content"],
                "metadata": res["metadata"],
                "distance": res.get("distance", 0.0),
            }
            _add_context(entry)

        # 2. Solo si hay cliente detectado y aún queda espacio, agregar máximo 1 fuente ajena
        # (para casos donde el cliente no tiene información suficiente)
        if detected_client:
            other_source_added: Set[str] = set()
            for res in other_results:
                sp = res.get("metadata", {}).get("source_path", "")
                if sp and sp not in other_source_added:
                    if len(other_source_added) >= 1:
                        continue  # Solo 1 fuente ajena máximo cuando hay cliente detectado
                    other_source_added.add(sp)
                elif sp and sp in other_source_added:
                    pass  # Misma fuente ya permitida, seguir agregando
                else:
                    continue  # Fuente distinta, saltar
                _add_context({
                    "type": res.get("type", "other_hit"),
                    "chunk_id": res["chunk_id"],
                    "content": res["content"],
                    "metadata": res["metadata"],
                    "distance": res.get("distance", 0.0),
                })
        else:
            # Sin cliente detectado: agregar todos los demás resultados normalmente
            for res in other_results:
                _add_context({
                    "type": res.get("type", "hit"),
                    "chunk_id": res["chunk_id"],
                    "content": res["content"],
                    "metadata": res["metadata"],
                    "distance": res.get("distance", 0.0),
                })

        # 3. Expansión de grafo: solo del cliente detectado si hay uno
        for res in list(retrieved_contexts):  # Copia para no modificar mientras iteramos
            meta = res.get("metadata", {})
            source_path = meta.get("source_path", "")
            doc_id = meta.get("title", "")

            if not doc_id or not self.graph_manager.graph.has_node(doc_id):
                continue

            neighbors = self.graph_manager.get_neighbors(doc_id, radius=graph_radius)
            for neighbor in neighbors:
                neighbor_data = self.graph_manager.graph.nodes.get(neighbor, {})
                neighbor_title = neighbor_data.get("title", neighbor)

                try:
                    neighbor_chunks = self.vector_store.get_chunks_by_doc_title(neighbor_title, limit=3)
                    for nc in neighbor_chunks:
                        nc_sp = nc.get("metadata", {}).get("source_path", "")
                        if detected_client and not _client_match(nc_sp):
                            continue
                        _add_context({
                            "type": "graph_expansion",
                            "chunk_id": nc["chunk_id"],
                            "content": nc["content"],
                            "metadata": nc["metadata"],
                            "distance": 0.0,
                        })
                except Exception:
                    neighbor_path = neighbor_data.get("source_path", "")
                    if neighbor_path and neighbor_path != source_path:
                        if detected_client and not _client_match(neighbor_path):
                            continue
                        entry = {
                            "type": "graph_expansion",
                            "chunk_id": f"graph-neighbor-{neighbor}",
                            "content": f"[Documento Relacionado en Grafo: {neighbor_title}]",
                            "metadata": neighbor_data,
                            "distance": 0.0,
                        }
                        _add_context(entry)

        return retrieved_contexts

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """Extrae palabras clave técnicas de la consulta para búsqueda por texto exacto.

        Los identificadores técnicos (con guiones, números o patrones mayúsculas)
        se priorizan al principio para que no queden desplazados por palabras genéricas
        al limitar el número de resultados.
        """
        import re

        # Patrón para identificadores técnicos: NET-IPTV-0041, XGE1/0/25, VLAN184, etc.
        tech_pattern = re.compile(r'\b[A-Z]{2,}[A-Z0-9_/.-]*\b')

        tech_keywords: List[str] = []
        generic_keywords: List[str] = []

        # Identificadores técnicos primero (prioridad alta)
        for m in tech_pattern.finditer(query):
            tech_keywords.append(m.group(0))

        # Palabras comunes de 4+ caracteres que no sean stopwords (prioridad baja)
        stopwords = {'que', 'cual', 'cuales', 'como', 'donde', 'cuando', 'porque', 'para',
                     'con', 'por', 'del', 'de', 'la', 'las', 'los', 'el', 'un', 'una', 'y',
                     'o', 'a', 'en', 'se', 'ha', 'han', 'ha', 'fue', 'fueron', 'está', 'están',
                     'qué', 'cuál', 'cuáles', 'cómo', 'dónde', 'cuándo', 'por qué'}
        words = re.findall(r'\b[a-záéíóúñ]{4,}\b', query.lower())
        for w in words:
            if w not in stopwords:
                generic_keywords.append(w)

        # Combinar: técnicos primero, genéricos después, sin duplicados
        seen: set = set()
        combined: List[str] = []
        for kw in tech_keywords + generic_keywords:
            if kw not in seen:
                seen.add(kw)
                combined.append(kw)

        return combined
