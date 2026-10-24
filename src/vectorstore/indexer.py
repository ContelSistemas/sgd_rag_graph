from pathlib import Path
from typing import Optional
from src.config import get_settings
from src.ingestion.parser import MarkdownParser
from src.ingestion.chunker import HierarchicalMarkdownChunker
from src.graph.manager import KnowledgeGraphManager
from src.graph.extractor import LLMExtractor, populate_graph_from_extraction
from src.vectorstore.store import VectorStoreManager

class KnowledgeBaseIndexer:
    """Pipeline completo de indexación para la Base del Conocimiento (Parser + Chunker + Graph + VectorStore)."""

    def __init__(self, data_dir: Optional[str] = None, vector_dir: Optional[str] = None):
        settings = get_settings()
        self.data_dir = Path(data_dir or settings.data_dir)
        self.parser = MarkdownParser()
        self.chunker = HierarchicalMarkdownChunker()
        self.graph_manager = KnowledgeGraphManager(persist_path=settings.graph_persist_path)
        self.vector_store = VectorStoreManager(persist_directory=vector_dir or settings.vector_store_dir)

        self.extractor = None
        if settings.extraction_enabled:
            try:
                self.extractor = LLMExtractor()
            except Exception as e:
                print(f"Aviso: no se pudo inicializar el extractor LLM: {e}")
                self.extractor = None

    def run_indexing(self) -> int:
        if not self.data_dir.exists():
            return 0

        total_chunks = 0
        md_files = [f for f in self.data_dir.glob("**/*.md") if f.is_file() and "vectorstore" not in f.parts]

        for file_path in md_files:
            try:
                parsed = self.parser.parse_file(file_path)
                frontmatter = parsed.get("frontmatter", {})
                doc_id = frontmatter.get("id", file_path.stem)

                self.graph_manager.add_document_node(doc_id, {
                    "source_path": str(file_path),
                    "title": frontmatter.get("title", file_path.stem),
                    "category": frontmatter.get("categoria", frontmatter.get("category", "General"))
                })

                for link in parsed.get("wiki_links", []):
                    target_id = link["target"]
                    self.graph_manager.add_relation(doc_id, target_id, relation_type="wiki_link")

                chunks = self.chunker.chunk_document(parsed)
                if chunks:
                    self.vector_store.delete_chunks_by_source(str(file_path))
                    self.vector_store.add_chunks(chunks)
                    total_chunks += len(chunks)

                    # Extracción de entidades y relaciones por chunk (solo si el extractor está disponible)
                    if self.extractor:
                        for chunk in chunks:
                            try:
                                populate_graph_from_extraction(
                                    kg_manager=self.graph_manager,
                                    extractor=self.extractor,
                                    text=chunk["content"],
                                    chunk_id=chunk["chunk_id"],
                                    source_path=str(file_path),
                                    frontmatter=frontmatter,
                                    add_frontmatter_nodes=False,  # evita duplicados con lo que ya hace el indexer
                                )
                            except Exception as e:
                                print(f"Aviso: extracción falló para chunk {chunk['chunk_id']}: {e}")

            except Exception as e:
                print(f"Error indexando {file_path}: {e}")

        return total_chunks


if __name__ == "__main__":
    indexer = KnowledgeBaseIndexer()
    total = indexer.run_indexing()
    print(f"Total chunks indexados: {total}")
