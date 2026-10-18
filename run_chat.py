import sys
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.retrieval.hybrid import HybridRetriever
from src.generation.local_llm import LocalLLMClient

def main():
    print("=== Chat Interactivo - Graph RAG para Base del Conocimiento ===")
    print("Inicializando componentes...")
    
    vector_store = VectorStoreManager(persist_directory="data/vectorstore")
    graph_manager = KnowledgeGraphManager(persist_path="data/knowledge_graph.json")
    retriever = HybridRetriever(vector_store=vector_store, graph_manager=graph_manager)
    
    # Configurar cliente LLM local (por defecto llamacpp en 8080 o se puede cambiar a ollama)
    backend = "llamacpp"
    base_url = "http://localhost:8080"
    if len(sys.argv) > 1:
        backend = sys.argv[1]
    if len(sys.argv) > 2:
        base_url = sys.argv[2]
        
    llm = LocalLLMClient(backend=backend, base_url=base_url, timeout=300)
    print(f"LLM conectado con backend '{backend}' en '{base_url}'.")
    print("Escribe tu consulta sobre la Base del Conocimiento (o 'salir' para terminar):\n")
    
    while True:
        try:
            query = input("KB Query > ").strip()
            if not query or query.lower() in ["salir", "exit", "quit"]:
                print("¡Hasta luego!")
                break
                
            print("Buscando en vector store y grafo de conocimiento...")
            results = retriever.retrieve(query, top_k=50, graph_radius=1)
            
            print(f"Recuperados {len(results)} fragmentos/contextos.")
            print("Generando respuesta con LLM local...")
            
            response = llm.generate_response(query, results)
            print(f"\n--- Respuesta ---\n{response}\n-----------------\n")
            
            print("Fuentes y referencias:")
            seen_sources = set()
            for i, r in enumerate(results, 1):
                meta = r.get("metadata", {})
                title = meta.get('title', 'N/A')
                source_path = meta.get('source_path', 'N/A')
                source_key = (title, source_path)
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)
                print(f"  [{i}] {title} ({source_path})")
            print()
            
        except KeyboardInterrupt:
            print("\n¡Hasta luego!")
            break
        except Exception as e:
            print(f"Error procesando consulta: {e}")

if __name__ == "__main__":
    main()
