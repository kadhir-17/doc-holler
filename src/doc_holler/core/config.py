from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: float = 60.0

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_collection_name: str = "doc_holler_chunks"

    retrieval_top_k: int = 5
    relevance_distance_threshold: float = 1.0

    chunk_size_words: int = 250
    chunk_overlap_words: int = 40

    max_upload_size_bytes: int = 15 * 1024 * 1024
    max_files_per_upload: int = 10
    allowed_extensions: tuple[str, ...] = (".pdf", ".txt", ".docx")

    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]
    temp_storage_dir: str = ""

    static_dir: Path = Path(__file__).resolve().parent.parent.parent.parent / "static"


def get_settings() -> Settings:
    return Settings()
