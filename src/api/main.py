from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from src.config import get_settings
from src.vectorstore.indexer import KnowledgeBaseIndexer
from src.retrieval.hybrid import HybridRetriever
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.generation.local_llm import LocalLLMClient

settings = get_settings()

app = FastAPI(
    title="Graph RAG para Base del Conocimiento - API REST",
    description="API on-premise para recuperación híbrida y generación local en la Base del Conocimiento",
    version="0.6.0"
)

# Instancias globales
vector_store = VectorStoreManager(persist_directory=settings.vector_store_dir)
graph_manager = KnowledgeGraphManager(persist_path=settings.graph_persist_path)
retriever = HybridRetriever(vector_store=vector_store, graph_manager=graph_manager)

class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=4, ge=1, le=20)
    graph_radius: int = Field(default=1, ge=0, le=5)
    backend: str = Field(default=settings.llm_backend, pattern="^(llamacpp|ollama)$")
    base_url: str = Field(default=settings.llm_base_url)
    timeout: int = Field(default=settings.llm_timeout, ge=10, le=600)

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
        "message": "Bienvenido a la API REST de Graph RAG para Base del Conocimiento",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Graph RAG Base del Conocimiento API"}

@app.post("/index", response_model=IndexResponse)
def trigger_indexing():
    try:
        indexer = KnowledgeBaseIndexer(data_dir=settings.data_dir, vector_dir=settings.vector_store_dir)
        total_chunks = indexer.run_indexing()
        global graph_manager, retriever
        graph_manager.load_from_json(settings.graph_persist_path)
        retriever = HybridRetriever(vector_store=vector_store, graph_manager=graph_manager)
        return IndexResponse(status="success", total_chunks=total_chunks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
def query_rag(req: QueryRequest):
    try:
        contexts = retriever.retrieve(req.query, top_k=req.top_k, graph_radius=req.graph_radius)
        llm = LocalLLMClient(
            backend=req.backend,
            base_url=req.base_url,
            model_name=settings.llm_model_name,
            timeout=req.timeout,
            max_retries=settings.llm_max_retries,
            base_delay=settings.llm_base_delay,
            n_predict=settings.llm_n_predict,
            temperature=settings.llm_temperature,
            repeat_penalty=settings.llm_repeat_penalty,
        )
        answer = llm.generate_response(req.query, contexts)
        return QueryResponse(query=req.query, response=answer, contexts=contexts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
