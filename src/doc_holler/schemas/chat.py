from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)


class SourceReference(BaseModel):
    document_id: str
    filename: str
    page: int | None = None
    chunk_id: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    answer_found: bool
