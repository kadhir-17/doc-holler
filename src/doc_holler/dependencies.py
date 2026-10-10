from functools import lru_cache

from fastapi import Depends

from doc_holler.core.config import Settings, get_settings
from doc_holler.integrations.openrouter_client import OpenRouterClient, OpenRouterClientProtocol
from doc_holler.repositories.document_repository import DocumentRepository
from doc_holler.repositories.vector_store import ChromaVectorStore
from doc_holler.services.answer_generation import AnswerGenerationService
from doc_holler.services.document_ingestion import DocumentIngestionService
from doc_holler.services.embeddings import (
    EmbeddingServiceProtocol,
    SentenceTransformerEmbeddingService,
)
from doc_holler.services.retrieval import RetrievalService


@lru_cache(maxsize=1)
def provide_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def provide_document_repository() -> DocumentRepository:
    return DocumentRepository()


@lru_cache(maxsize=1)
def provide_vector_store() -> ChromaVectorStore:
    settings = provide_settings()
    return ChromaVectorStore(collection_name=settings.chroma_collection_name)


@lru_cache(maxsize=1)
def provide_embedding_service() -> SentenceTransformerEmbeddingService:
    settings = provide_settings()
    return SentenceTransformerEmbeddingService(model_name=settings.embedding_model_name)


def provide_openrouter_client(
    settings: Settings = Depends(provide_settings),
) -> OpenRouterClientProtocol:
    return OpenRouterClient(settings=settings)


def provide_ingestion_service(
    embedding_service: EmbeddingServiceProtocol = Depends(provide_embedding_service),
    vector_store: ChromaVectorStore = Depends(provide_vector_store),
    document_repository: DocumentRepository = Depends(provide_document_repository),
    settings: Settings = Depends(provide_settings),
) -> DocumentIngestionService:
    return DocumentIngestionService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        document_repository=document_repository,
        settings=settings,
    )


def provide_retrieval_service(
    embedding_service: EmbeddingServiceProtocol = Depends(provide_embedding_service),
    vector_store: ChromaVectorStore = Depends(provide_vector_store),
    document_repository: DocumentRepository = Depends(provide_document_repository),
    settings: Settings = Depends(provide_settings),
) -> RetrievalService:
    return RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        document_repository=document_repository,
        settings=settings,
    )


def provide_answer_generation_service(
    retrieval_service: RetrievalService = Depends(provide_retrieval_service),
    openrouter_client: OpenRouterClientProtocol = Depends(provide_openrouter_client),
) -> AnswerGenerationService:
    return AnswerGenerationService(
        retrieval_service=retrieval_service,
        openrouter_client=openrouter_client,
    )
