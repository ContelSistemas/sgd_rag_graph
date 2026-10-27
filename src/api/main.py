from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from src.config import get_settings
from src.vectorstore.indexer import KnowledgeBaseIndexer
from src.retrieval.hybrid import HybridRetriever
from src.vectorstore.store import VectorStoreManager
from src.graph.manager import KnowledgeGraphManager
from src.generation.local_llm import LocalLLMClient
from src.documentation import DocumentationAgent

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


class DocumentationRequest(BaseModel):
    caso: str
    pruebas: str
    resolucion: str
    write_file: bool = True
    overwrite: bool = False
    backend: Optional[str] = None
    base_url: Optional[str] = None
    timeout: Optional[int] = None
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    n_predict: int = Field(default=1024, ge=64, le=4096)


class DocumentationResponse(BaseModel):
    id: str
    title: str
    caso: str
    tipo: str
    categoria: str
    sistema: str
    criticidad: str
    tags: List[str]
    clientes_afectados: List[str]
    fecha_deteccion: str
    fecha_actualizacion: str
    body: str
    file_path: Optional[str]
    raw_llm_output: Optional[str]

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


@app.post("/documentar-incidencia", response_model=DocumentationResponse)
def documentar_incidencia(req: DocumentationRequest):
    """Organiza una incidencia usando el LLM local y (opcionalmente) la guarda
    como archivo Markdown en data/incidencias/<ID>.md."""
    try:
        agent = DocumentationAgent(
            backend=req.backend,
            base_url=req.base_url,
            timeout=req.timeout,
            temperature=req.temperature,
            n_predict=req.n_predict,
        )
        result = agent.run(
            caso=req.caso,
            pruebas=req.pruebas,
            resolucion=req.resolucion,
            write_file=req.write_file,
            overwrite=req.overwrite,
        )

        fm = result.frontmatter
        return DocumentationResponse(
            id=fm.id,
            title=fm.title,
            caso=fm.caso,
            tipo=fm.tipo,
            categoria=fm.categoria,
            sistema=fm.sistema,
            criticidad=fm.criticidad,
            tags=fm.tags,
            clientes_afectados=fm.clientes_afectados,
            fecha_deteccion=fm.fecha_deteccion,
            fecha_actualizacion=fm.fecha_actualizacion,
            body=result.body,
            file_path=str(result.file_path) if result.file_path else None,
            raw_llm_output=result.raw_llm_output,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
