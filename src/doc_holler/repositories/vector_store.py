from dataclasses import dataclass
from threading import Lock
from typing import Any

import chromadb

from doc_holler.core.errors import RetrievalError
from doc_holler.services.text_chunking import TextChunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    text: str
    distance: float
    page_number: int | None = None


class ChromaVectorStore:
    def __init__(self, collection_name: str = "doc_holler_chunks") -> None:
        self.collection_name = collection_name
        self._lock = Lock()
        self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[TextChunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return

        ids: list[str] = [chunk.chunk_id for chunk in chunks]
        documents: list[str] = [chunk.text for chunk in chunks]
        metadatas: list[dict[str, Any]] = [
            {
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page_number if chunk.page_number is not None else -1,
            }
            for chunk in chunks
        ]

        with self._lock:
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

    def query(self, query_embedding: list[float], top_k: int = 5) -> list[RetrievedChunk]:
        with self._lock:
            total_count = self._collection.count()
            if total_count == 0:
                return []

            n_results = min(top_k, total_count)
            try:
                results = self._collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"],
                )
            except Exception as exc:
                raise RetrievalError(f"Vector search failed: {exc}") from exc

        retrieved: list[RetrievedChunk] = []
        ids_list = results.get("ids", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        metas_list = results.get("metadatas", [[]])[0]
        dists_list = results.get("distances", [[]])[0]

        for idx in range(len(ids_list)):
            chunk_id = ids_list[idx]
            text = docs_list[idx]
            meta = metas_list[idx] if idx < len(metas_list) else {}
            dist = float(dists_list[idx]) if idx < len(dists_list) else 0.0

            page_val = meta.get("page", -1)
            page_number = int(page_val) if page_val is not None and int(page_val) >= 1 else None

            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(meta.get("document_id", "")),
                    filename=str(meta.get("filename", "")),
                    text=text,
                    distance=dist,
                    page_number=page_number,
                )
            )

        return retrieved

    def delete_by_document_id(self, document_id: str) -> None:
        with self._lock:
            try:
                self._collection.delete(where={"document_id": document_id})
            except Exception:
                pass

    def count(self) -> int:
        with self._lock:
            return self._collection.count()

    def clear(self) -> None:
        with self._lock:
            self._client.delete_collection(self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
