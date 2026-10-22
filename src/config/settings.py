from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    llm_backend: str = "llamacpp"
    llm_base_url: str = "http://localhost:8080"
    llm_model_name: str = "qwen2.5-3b-instruct"
    llm_timeout: int = 300
    llm_max_retries: int = 3
    llm_base_delay: float = 1.0
    llm_n_predict: int = 512
    llm_temperature: float = 0.3
    llm_ctx_size: int = 4096
    llm_repeat_penalty: float = 1.15

    # Vector Store
    vector_store_dir: str = "data/vectorstore"
    embedding_model: str = "paraphrase-multilingual-mpnet-base-v2"

    # Graph
    graph_persist_path: str = "data/knowledge_graph.json"

    # Graph extraction (LLM-based entity/relation extraction)
    extraction_enabled: bool = False
    extraction_model: Optional[str] = None
    extraction_temperature: float = 0.1
    extraction_max_tokens: int = 512
    entity_similarity_threshold: float = 0.9

    # Data
    data_dir: str = "data"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_max_timeout: int = 600

    # Retrieval defaults
    default_top_k: int = 20
    default_graph_radius: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()