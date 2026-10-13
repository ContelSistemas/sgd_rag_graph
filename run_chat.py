import sys
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.retrieval.hybrid import HybridRetriever
from src.generation.local_llm import LocalLLMClient

def main():
    print("=== Chat Interactivo - Graph RAG para SGD ===")
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
    print("Escribe tu consulta sobre el SGD (o 'salir' para terminar):\n")
    
    while True:
        try:
            query = input("SGD Query > ").strip()
            if not query or query.lower() in ["salir", "exit", "quit"]:
                print("¡Hasta luego!")
                break
                
            print("Buscando en vector store y grafo de conocimiento...")
            results = retriever.retrieve(query, top_k=3, graph_radius=1)
            
            print(f"Recuperados {len(results)} fragmentos/contextos.")
            print("Generando respuesta con LLM local...")
            
            response = llm.generate_response(query, results)
            print(f"\n--- Respuesta ---\n{response}\n-----------------\n")
            
            print("Fuentes y referencias:")
            for i, r in enumerate(results, 1):
                meta = r.get("metadata", {})
                print(f"  [{i}] {meta.get('title', 'N/A')} ({meta.get('source_path', 'N/A')})")
            print()
            
        except KeyboardInterrupt:
            print("\n¡Hasta luego!")
            break
        except Exception as e:
            print(f"Error procesando consulta: {e}")

if __name__ == "__main__":
    main()
