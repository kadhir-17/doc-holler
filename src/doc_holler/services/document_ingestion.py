import uuid
from pathlib import Path

from doc_holler.core.config import Settings
from doc_holler.core.errors import DocumentNotFoundError, EmptyDocumentError
from doc_holler.integrations.document_extractors import extract_document
from doc_holler.repositories.document_repository import DocumentRepository
from doc_holler.repositories.vector_store import ChromaVectorStore
from doc_holler.schemas.documents import DocumentRecord
from doc_holler.services.embeddings import EmbeddingServiceProtocol
from doc_holler.services.text_chunking import chunk_sections


class DocumentIngestionService:
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

    def ingest_document(
        self,
        file_path: Path,
        original_filename: str,
        file_size: int,
        content_type: str,
    ) -> DocumentRecord:
        doc_id = uuid.uuid4().hex[:12]
        safe_filename = Path(original_filename).name

        sections = extract_document(file_path, safe_filename)
        chunks = chunk_sections(
            document_id=doc_id,
            filename=safe_filename,
            sections=sections,
            chunk_size_words=self.settings.chunk_size_words,
            chunk_overlap_words=self.settings.chunk_overlap_words,
        )

        if not chunks:
            raise EmptyDocumentError(f"Document '{safe_filename}' contains no usable text chunks")

        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_service.embed_documents(texts)

        try:
            self.vector_store.add_chunks(chunks, embeddings)
            record = DocumentRecord(
                id=doc_id,
                filename=safe_filename,
                content_type=content_type,
                size_bytes=file_size,
                status="indexed",
                chunk_count=len(chunks),
            )
            self.document_repository.add(record)
            return record
        except Exception:
            self.vector_store.delete_by_document_id(doc_id)
            self.document_repository.delete(doc_id)
            raise

    def delete_document(self, document_id: str) -> None:
        record = self.document_repository.get(document_id)
        if record is None:
            raise DocumentNotFoundError(document_id)

        self.vector_store.delete_by_document_id(document_id)
        self.document_repository.delete(document_id)
