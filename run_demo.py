from pathlib import Path
from src.vectorstore.indexer import SGDIndexer
from src.retrieval.hybrid import HybridRetriever
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.generation.local_llm import LocalLLMClient

def main():
    print("=== Graph RAG para SGD - Demostración de Integración E2E (Fase 5) ===")
    
    # 1. Indexación de documentos del SGD
    print("\n[1] Iniciando indexación de documentos en 'data/'...")
    indexer = SGDIndexer(data_dir="data", vector_dir="data/vectorstore")
    total_chunks = indexer.run_indexing()
    print(f" -> Indexación completada. Total de chunks indexados: {total_chunks}")
    print(f" -> Nodos en el grafo de conocimiento: {len(indexer.graph_manager.graph.nodes)}")
    
    # 2. Recuperación Híbrida
    print("\n[2] Probando recuperación híbrida (Vectorial + Grafo)...")
    retriever = HybridRetriever(vector_store=indexer.vector_store, graph_manager=indexer.graph_manager)
    
    query = "¿Cuándo se bloqueó la OLT?"
    print(f" -> Consulta: '{query}'")
    results = retriever.retrieve(query, top_k=3, graph_radius=1)
    print(f" -> Fragmentos y contextos recuperados: {len(results)}")
    
    for i, res in enumerate(results, 1):
        print(f"    [{i}] Tipo: {res['type']} | ID: {res['chunk_id']} | Título: {res['metadata'].get('title', 'N/A')}")
        print(f"        Extracto: {res['content'][:150]}...")
        
    # 3. Prueba de Generación LLM Local (Ollama / Llama.cpp)
    print("\n[3] Probando cliente LLM Local (Llama.cpp en http://localhost:8080 / Ollama)...")
    # Intentamos con Llama.cpp server en puerto 8080 (configurable timeout=300)
    llm = LocalLLMClient(backend="llamacpp", base_url="http://localhost:8080", timeout=300)
    
    print(" -> Enviando consulta y contexto al motor LLM local...")
    response = llm.generate_response(query, results)
    print("\nRespuesta Generada por el LLM Local:\n")
    print(response)
    print("\n=== Demostración E2E Finalizada ===")

if __name__ == "__main__":
    main()
