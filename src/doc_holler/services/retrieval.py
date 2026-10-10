from dataclasses import dataclass

from doc_holler.core.config import Settings
from doc_holler.core.errors import NoDocumentsIndexedError
from doc_holler.repositories.document_repository import DocumentRepository
from doc_holler.repositories.vector_store import ChromaVectorStore, RetrievedChunk
from doc_holler.services.embeddings import EmbeddingServiceProtocol


@dataclass(frozen=True)
class RetrievalResult:
    relevant_chunks: list[RetrievedChunk]
    has_sufficient_evidence: bool


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingServiceProtocol,
        vector_store: ChromaVectorStore,
        document_repository: DocumentRepository,
        settings: Settings,
    ) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.document_repository = document_repository
        self.settings = settings

    def retrieve(self, question: str) -> RetrievalResult:
        if self.document_repository.count() == 0 or self.vector_store.count() == 0:
            raise NoDocumentsIndexedError()

        query_embedding = self.embedding_service.embed_query(question)
        candidate_chunks = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=self.settings.retrieval_top_k,
        )

        relevant = [
            chunk
            for chunk in candidate_chunks
            if chunk.distance <= self.settings.relevance_distance_threshold
        ]

        return RetrievalResult(
            relevant_chunks=relevant,
            has_sufficient_evidence=len(relevant) > 0,
        )
