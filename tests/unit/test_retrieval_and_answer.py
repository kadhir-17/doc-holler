import pytest

from doc_holler.core.config import Settings
from doc_holler.core.errors import (
    LLMConfigurationError,
    NoDocumentsIndexedError,
)
from doc_holler.integrations.openrouter_client import OpenRouterClient
from doc_holler.repositories.document_repository import DocumentRepository
from doc_holler.repositories.vector_store import ChromaVectorStore, RetrievedChunk
from doc_holler.schemas.documents import DocumentRecord
from doc_holler.services.answer_generation import (
    INSUFFICIENT_INFORMATION_FALLBACK,
    AnswerGenerationService,
    format_excerpts,
    is_insufficient_answer,
)
from doc_holler.services.retrieval import RetrievalService


class FakeEmbeddingService:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 16 for _ in texts]

    def embed_query(self, query: str) -> list[float]:
        return [0.1] * 16


class FakeOpenRouterClient:
    def __init__(self, answer: str = "This is a grounded answer.") -> None:
        self.answer = answer
        self.last_messages: list[dict[str, str]] = []

    def complete_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> str:
        self.last_messages = messages
        return self.answer


def test_retrieval_no_documents_indexed() -> None:
    settings = Settings()
    doc_repo = DocumentRepository()
    vector_store = ChromaVectorStore(collection_name="test_retrieval_empty")
    embedding_service = FakeEmbeddingService()
    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        document_repository=doc_repo,
        settings=settings,
    )

    with pytest.raises(NoDocumentsIndexedError):
        retrieval_service.retrieve("What is this document about?")


def test_format_excerpts() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="chunk_1",
            document_id="doc_1",
            filename="guide.pdf",
            text="Step one is to configure the server.",
            distance=0.2,
            page_number=3,
        ),
        RetrievedChunk(
            chunk_id="chunk_2",
            document_id="doc_2",
            filename="notes.txt",
            text="Step two is to run the server.",
            distance=0.4,
            page_number=None,
        ),
    ]
    formatted = format_excerpts(chunks)
    assert "[Source: guide.pdf | Page 3 | Chunk ID: chunk_1]" in formatted
    assert "[Source: notes.txt | Page N/A | Chunk ID: chunk_2]" in formatted
    assert "Step one is to configure the server." in formatted
    assert "Step two is to run the server." in formatted


def test_is_insufficient_answer() -> None:
    assert is_insufficient_answer(INSUFFICIENT_INFORMATION_FALLBACK) is True
    assert is_insufficient_answer("I don't have enough information to answer.") is True
    insufficient_sample = "The supplied document does not contain sufficient information."
    assert is_insufficient_answer(insufficient_sample) is True
    assert is_insufficient_answer("Celery uses Redis as a message broker.") is False


def test_answer_generation_insufficient_retrieval() -> None:
    settings = Settings(relevance_distance_threshold=0.5)
    doc_repo = DocumentRepository()
    doc_repo.add(
        DocumentRecord(
            id="doc1",
            filename="test.txt",
            content_type="text/plain",
            size_bytes=100,
            status="indexed",
            chunk_count=1,
        )
    )

    class LowRelevanceVectorStore(ChromaVectorStore):
        def query(self, query_embedding: list[float], top_k: int = 5) -> list[RetrievedChunk]:
            return [
                RetrievedChunk(
                    chunk_id="chunk_1",
                    document_id="doc1",
                    filename="test.txt",
                    text="Unrelated topic completely.",
                    distance=1.8,
                    page_number=None,
                )
            ]

        def count(self) -> int:
            return 1

    vector_store = LowRelevanceVectorStore(collection_name="test_low_rel")
    embedding_service = FakeEmbeddingService()
    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        document_repository=doc_repo,
        settings=settings,
    )
    fake_llm = FakeOpenRouterClient("Should not be called")
    answer_service = AnswerGenerationService(
        retrieval_service=retrieval_service,
        openrouter_client=fake_llm,
    )

    response = answer_service.answer_question("Where is the database located?")
    assert response.answer_found is False
    assert response.answer == INSUFFICIENT_INFORMATION_FALLBACK
    assert response.sources == []
    assert len(fake_llm.last_messages) == 0


def test_answer_generation_success() -> None:
    settings = Settings(relevance_distance_threshold=1.0)
    doc_repo = DocumentRepository()
    doc_repo.add(
        DocumentRecord(
            id="doc1",
            filename="spec.pdf",
            content_type="application/pdf",
            size_bytes=200,
            status="indexed",
            chunk_count=1,
        )
    )

    class HighRelevanceVectorStore(ChromaVectorStore):
        def query(self, query_embedding: list[float], top_k: int = 5) -> list[RetrievedChunk]:
            return [
                RetrievedChunk(
                    chunk_id="chunk_1",
                    document_id="doc1",
                    filename="spec.pdf",
                    text="The timeout parameter is set to 30 seconds.",
                    distance=0.15,
                    page_number=4,
                )
            ]

        def count(self) -> int:
            return 1

    vector_store = HighRelevanceVectorStore(collection_name="test_high_rel")
    embedding_service = FakeEmbeddingService()
    retrieval_service = RetrievalService(
        embedding_service=embedding_service,
        vector_store=vector_store,
        document_repository=doc_repo,
        settings=settings,
    )
    fake_llm = FakeOpenRouterClient("The timeout is 30 seconds.")
    answer_service = AnswerGenerationService(
        retrieval_service=retrieval_service,
        openrouter_client=fake_llm,
    )

    response = answer_service.answer_question("What is the timeout parameter?")
    assert response.answer_found is True
    assert response.answer == "The timeout is 30 seconds."
    assert len(response.sources) == 1
    assert response.sources[0].filename == "spec.pdf"
    assert response.sources[0].page == 4
    assert response.sources[0].chunk_id == "chunk_1"
    assert len(fake_llm.last_messages) == 2


def test_openrouter_missing_config() -> None:
    settings = Settings(openrouter_api_key="", openrouter_model="test-model")
    client = OpenRouterClient(settings)
    with pytest.raises(LLMConfigurationError):
        client.complete_chat([{"role": "user", "content": "hi"}])

    settings2 = Settings(openrouter_api_key="valid-key", openrouter_model="")
    client2 = OpenRouterClient(settings2)
    with pytest.raises(LLMConfigurationError):
        client2.complete_chat([{"role": "user", "content": "hi"}])
