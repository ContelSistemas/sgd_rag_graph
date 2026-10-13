from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.vectorstore.indexer import SGDIndexer
from src.retrieval.hybrid import HybridRetriever
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.generation.local_llm import LocalLLMClient

app = FastAPI(
    title="Graph RAG para SGD - API REST",
    description="API on-premise para recuperación híbrida y generación local en el Sistema de Gestión Documental",
    version="0.6.0"
)

# Instancias globales o de soporte
vector_store = VectorStoreManager(persist_directory="data/vectorstore")
graph_manager = KnowledgeGraphManager()
retriever = HybridRetriever(vector_store=vector_store, graph_manager=graph_manager)

class QueryRequest(BaseModel):
    query: str
    top_k: int = 4
    graph_radius: int = 1
    backend: str = "llamacpp"
    base_url: str = "http://localhost:8080"
    timeout: int = 300

class QueryResponse(BaseModel):
    query: str
    response: str
    contexts: List[Dict[str, Any]]

class IndexResponse(BaseModel):
    status: str
    total_chunks: int

@app.get("/")
def root():
    return {
        "message": "Bienvenido a la API REST de Graph RAG para SGD",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Graph RAG SGD API"}

@app.post("/index", response_model=IndexResponse)
def trigger_indexing():
    try:
        indexer = SGDIndexer(data_dir="data", vector_dir="data/vectorstore")
        total_chunks = indexer.run_indexing()
        # Sincronizamos graph_manager global con el indexador
        global graph_manager, retriever
        graph_manager = indexer.graph_manager
        retriever = HybridRetriever(vector_store=vector_store, graph_manager=graph_manager)
        return IndexResponse(status="success", total_chunks=total_chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
def query_rag(req: QueryRequest):
    try:
        contexts = retriever.retrieve(req.query, top_k=req.top_k, graph_radius=req.graph_radius)
        llm = LocalLLMClient(backend=req.backend, base_url=req.base_url, timeout=req.timeout)
        answer = llm.generate_response(req.query, contexts)
        return QueryResponse(query=req.query, response=answer, contexts=contexts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
