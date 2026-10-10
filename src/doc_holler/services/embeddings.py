from typing import Protocol

from sentence_transformers import SentenceTransformer


class EmbeddingServiceProtocol(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class SentenceTransformerEmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, query: str) -> list[float]:
        model = self._get_model()
        embedding = model.encode(query, convert_to_numpy=True, show_progress_bar=False)
        return embedding.tolist()
