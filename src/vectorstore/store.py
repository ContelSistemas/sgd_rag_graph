import os
from typing import List, Dict, Any, Optional

try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

class VectorStoreManager:
    """Gestor de base de datos vectorial local (ChromaDB) y embeddings locales (SentenceTransformers)."""

    def __init__(self, persist_directory: str = "data/vectorstore", model_name: str = "all-MiniLM-L6-v2"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        self.encoder = SentenceTransformer(model_name) if HAS_SENTENCE_TRANSFORMERS else None
        
        if HAS_CHROMADB:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(name="sgd_documents")
        else:
            self.client = None
            self.collection = None

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        if not self.collection or not self.encoder:
            raise RuntimeError("ChromaDB y/o SentenceTransformers no están instalados en este entorno.")
        if not chunks:
            return

        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk["content"] for chunk in chunks]
        
        embeddings = self.encoder.encode(documents, show_progress_bar=False).tolist()

        metadatas = []
        for chunk in chunks:
            meta = {
                "source_path": str(chunk.get("source_path", "")),
                "header_path": str(chunk.get("header_path", "")),
                "title": str(chunk.get("frontmatter", {}).get("title", ""))
            }
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def similarity_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.collection or not self.encoder:
            raise RuntimeError("ChromaDB y/o SentenceTransformers no están instalados en este entorno.")
            
        query_embedding = self.encoder.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )

        formatted_results = []
        if results and results["ids"] and len(results["ids"]) > 0:
            ids = results["ids"][0]
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(ids)

            for chunk_id, doc, meta, dist in zip(ids, docs, metas, distances):
                formatted_results.append({
                    "chunk_id": chunk_id,
                    "content": doc,
                    "metadata": meta,
                    "distance": dist
                })

        return formatted_results

    def get_chunks_by_doc_title(self, doc_title: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.collection:
            raise RuntimeError("ChromaDB no está disponible.")
        
        results = self.collection.get(
            where={"title": doc_title},
            limit=limit
        )

        formatted_results = []
        if results and results["ids"]:
            for chunk_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
                formatted_results.append({
                    "chunk_id": chunk_id,
                    "content": doc,
                    "metadata": meta,
                    "distance": 0.0
                })

        return formatted_results
