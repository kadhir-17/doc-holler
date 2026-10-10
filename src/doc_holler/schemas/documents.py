from pydantic import BaseModel


class DocumentRecord(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentRecord]


class UploadErrorItem(BaseModel):
    filename: str
    error: str


class DocumentUploadResponse(BaseModel):
    documents: list[DocumentRecord]
    failed: list[UploadErrorItem] = []


class DocumentDeleteResponse(BaseModel):
    success: bool
    document_id: str
    message: str
