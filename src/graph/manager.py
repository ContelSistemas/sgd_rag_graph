import networkx as nx
from typing import Dict, Any, List, Optional

class KnowledgeGraphManager:
    """Gestor de Grafo de Conocimiento basado en NetworkX para el SGD."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_document_node(self, doc_id: str, metadata: Dict[str, Any]) -> None:
        """Agrega o actualiza un nodo de documento en el grafo."""
        self.graph.add_node(doc_id, **metadata)

    def add_relation(self, source_id: str, target_id: str, relation_type: str = "wiki_link", **attrs) -> None:
        """Agrega una arista dirigida entre dos documentos."""
        if not self.graph.has_node(source_id):
            self.graph.add_node(source_id)
        if not self.graph.has_node(target_id):
            self.graph.add_node(target_id)
            
        self.graph.add_edge(source_id, target_id, relation=relation_type, **attrs)

    def get_neighbors(self, doc_id: str, radius: int = 1) -> List[str]:
        """Obtiene los vecinos conectados a un documento dentro de un radio dado."""
        if not self.graph.has_node(doc_id):
            return []
        
        neighbors = set()
        current_layer = {doc_id}
        
        for _ in range(radius):
            next_layer = set()
            for node in current_layer:
                succ = list(self.graph.successors(node))
                pred = list(self.graph.predecessors(node))
                next_layer.update(succ)
                next_layer.update(pred)
            neighbors.update(next_layer)
            current_layer = next_layer
            
        neighbors.discard(doc_id)
        return list(neighbors)

    def get_subgraph_context(self, doc_id: str, radius: int = 1) -> Dict[str, Any]:
        """Obtiene un subgrafo centrado en un documento para enriquecer el contexto RAG."""
        neighbor_nodes = self.get_neighbors(doc_id, radius)
        sub_nodes = [doc_id] + neighbor_nodes
        subgraph = self.graph.subgraph(sub_nodes)
        
        return {
            "nodes": [{"id": n, **subgraph.nodes[n]} for n in subgraph.nodes],
            "edges": [{"source": u, "target": v, **subgraph.edges[u, v]} for u, v in subgraph.edges]
        }
