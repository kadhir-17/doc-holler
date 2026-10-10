from threading import Lock

from doc_holler.schemas.documents import DocumentRecord


class DocumentRepository:
    def __init__(self) -> None:
        self._documents: dict[str, DocumentRecord] = {}
        self._lock = Lock()

    def add(self, document: DocumentRecord) -> None:
        with self._lock:
            self._documents[document.id] = document

    def get(self, document_id: str) -> DocumentRecord | None:
        with self._lock:
            return self._documents.get(document_id)

    def list_all(self) -> list[DocumentRecord]:
        with self._lock:
            return list(self._documents.values())

    def delete(self, document_id: str) -> bool:
        with self._lock:
            if document_id in self._documents:
                del self._documents[document_id]
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._documents)

    def clear(self) -> None:
        with self._lock:
            self._documents.clear()
