from io import BytesIO

import docx
import pymupdf
import pytest
from fastapi.testclient import TestClient

from doc_holler.core.config import Settings
from doc_holler.core.errors import LLMProviderError
from doc_holler.dependencies import (
    provide_embedding_service,
    provide_openrouter_client,
    provide_settings,
)
from doc_holler.main import app
from doc_holler.services.answer_generation import INSUFFICIENT_INFORMATION_FALLBACK


class IntegrationFakeEmbeddingService:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            val = float(len(text) % 10) / 10.0
            embeddings.append([val] * 8)
        return embeddings

    def embed_query(self, query: str) -> list[float]:
        val = float(len(query) % 10) / 10.0
        return [val] * 8


class IntegrationFakeOpenRouterClient:
    def __init__(self) -> None:
        self.call_count = 0
        self.should_fail = False

    def complete_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> str:
        self.call_count += 1
        if self.should_fail:
            raise LLMProviderError("Simulated OpenRouter failure")
        return "Based on the documents, Celery uses Redis as a task queue and broker."


@pytest.fixture
def fake_llm() -> IntegrationFakeOpenRouterClient:
    return IntegrationFakeOpenRouterClient()


@pytest.fixture
def client(fake_llm: IntegrationFakeOpenRouterClient) -> TestClient:
    fake_embeddings = IntegrationFakeEmbeddingService()
    app.dependency_overrides[provide_embedding_service] = lambda: fake_embeddings
    app.dependency_overrides[provide_openrouter_client] = lambda: fake_llm
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_sample_pdf_bytes(text: str = "Redis is used by Celery for queueing.") -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_docx_bytes(text: str = "Docx content about distributed tasks.") -> bytes:
    doc = docx.Document()
    doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_documents_list_initially(client: TestClient) -> None:
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    assert response.json() == {"documents": []}


def test_chat_with_no_documents_indexed(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"question": "How does Celery work?"})
    assert response.status_code == 400
    assert "No documents are currently indexed" in response.json()["detail"]


def test_empty_question_validation(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"question": "   "})
    assert response.status_code == 400


def test_upload_unsupported_format(client: TestClient) -> None:
    files = [("files", ("image.png", b"\x89PNG\r\n\x1a\n", "image/png"))]
    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 400


def test_upload_empty_document(client: TestClient) -> None:
    files = [("files", ("empty.txt", b"", "text/plain"))]
    response = client.post("/api/v1/documents", files=files)
    assert response.status_code == 400


def test_document_lifecycle_and_multi_document_chat(
    client: TestClient,
    fake_llm: IntegrationFakeOpenRouterClient,
) -> None:
    pdf_bytes = create_sample_pdf_bytes("Celery uses Redis as an in-memory message broker.")
    docx_bytes = create_sample_docx_bytes("Worker processes consume messages asynchronously.")
    txt_bytes = b"Configuration parameters include broker_url and result_backend."

    files = [
        ("files", ("celery_guide.pdf", pdf_bytes, "application/pdf")),
        (
            "files",
            (
                "workers.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ),
        ("files", ("config.txt", txt_bytes, "text/plain")),
    ]

    upload_response = client.post("/api/v1/documents", files=files)
    assert upload_response.status_code == 201
    upload_data = upload_response.json()
    assert len(upload_data["documents"]) == 3
    assert len(upload_data["failed"]) == 0

    list_response = client.get("/api/v1/documents")
    assert list_response.status_code == 200
    docs = list_response.json()["documents"]
    assert len(docs) == 3
    doc_ids = [d["id"] for d in docs]

    chat_response = client.post("/api/v1/chat", json={"question": "How does Celery use Redis?"})
    assert chat_response.status_code == 200
    chat_data = chat_response.json()
    assert chat_data["answer_found"] is True
    assert "Celery uses Redis" in chat_data["answer"]
    assert len(chat_data["sources"]) > 0

    has_pdf_page = any(s["page"] is not None for s in chat_data["sources"])
    assert has_pdf_page is True

    doc_to_delete = doc_ids[0]
    delete_response = client.delete(f"/api/v1/documents/{doc_to_delete}")
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True

    delete_not_found = client.delete(f"/api/v1/documents/{doc_to_delete}")
    assert delete_not_found.status_code == 404

    after_delete_response = client.get("/api/v1/documents")
    assert len(after_delete_response.json()["documents"]) == 2

    fake_llm.should_fail = True
    failing_chat = client.post("/api/v1/chat", json={"question": "What is the broker url?"})
    assert failing_chat.status_code == 502
    assert "Simulated OpenRouter failure" in failing_chat.json()["detail"]


def test_missing_answer_behavior(client: TestClient) -> None:
    txt_bytes = b"Apples and oranges are types of fruit."
    files = [("files", ("fruits.txt", txt_bytes, "text/plain"))]
    upload_res = client.post("/api/v1/documents", files=files)
    assert upload_res.status_code == 201

    app.dependency_overrides[provide_openrouter_client] = lambda: IntegrationFakeOpenRouterClient()
    app.dependency_overrides[provide_settings] = lambda: Settings(relevance_distance_threshold=-1.0)

    try:
        response = client.post("/api/v1/chat", json={"question": "What is quantum mechanics?"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer_found"] is False
        assert data["answer"] == INSUFFICIENT_INFORMATION_FALLBACK
        assert data["sources"] == []
    finally:
        del app.dependency_overrides[provide_settings]
