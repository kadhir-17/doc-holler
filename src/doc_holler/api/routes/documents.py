import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from doc_holler.core.config import Settings
from doc_holler.core.errors import (
    DocHollerError,
    DocumentNotFoundError,
)
from doc_holler.dependencies import (
    provide_document_repository,
    provide_ingestion_service,
    provide_settings,
)
from doc_holler.repositories.document_repository import DocumentRepository
from doc_holler.schemas.documents import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentRecord,
    DocumentUploadResponse,
    UploadErrorItem,
)
from doc_holler.services.document_ingestion import DocumentIngestionService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents(
    doc_repo: DocumentRepository = Depends(provide_document_repository),
) -> DocumentListResponse:
    records = doc_repo.list_all()
    return DocumentListResponse(documents=records)


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: list[UploadFile],
    settings: Settings = Depends(provide_settings),
    ingestion_service: DocumentIngestionService = Depends(provide_ingestion_service),
) -> DocumentUploadResponse:
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided in upload request",
        )

    if len(files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exceeded maximum file upload limit of {settings.max_files_per_upload} files",
        )

    successful_records: list[DocumentRecord] = []
    failures: list[UploadErrorItem] = []

    for upload_file in files:
        raw_filename = upload_file.filename or "unknown"
        safe_filename = Path(raw_filename).name

        suffix = Path(safe_filename).suffix.lower()
        if suffix not in settings.allowed_extensions:
            allowed_str = ", ".join(settings.allowed_extensions)
            failures.append(
                UploadErrorItem(
                    filename=safe_filename,
                    error=f"Unsupported file extension '{suffix}'. Allowed: {allowed_str}",
                )
            )
            continue

        temp_path = None
        try:
            max_bytes = settings.max_upload_size_bytes
            total_bytes = 0
            chunk_size = 64 * 1024

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_path = Path(temp_file.name)
                while chunk := await upload_file.read(chunk_size):
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        break
                    temp_file.write(chunk)

            if total_bytes == 0:
                failures.append(
                    UploadErrorItem(
                        filename=safe_filename,
                        error="File is empty",
                    )
                )
                continue

            if total_bytes > max_bytes:
                failures.append(
                    UploadErrorItem(
                        filename=safe_filename,
                        error=f"File exceeds maximum allowed size of {max_bytes} bytes",
                    )
                )
                continue

            content_type = upload_file.content_type or "application/octet-stream"
            record = await asyncio.to_thread(
                ingestion_service.ingest_document,
                file_path=temp_path,
                original_filename=safe_filename,
                file_size=total_bytes,
                content_type=content_type,
            )
            successful_records.append(record)

        except DocHollerError as exc:
            failures.append(
                UploadErrorItem(
                    filename=safe_filename,
                    error=exc.message,
                )
            )
        except Exception as exc:
            failures.append(
                UploadErrorItem(
                    filename=safe_filename,
                    error=f"Ingestion failed: {exc}",
                )
            )
        finally:
            if temp_path and temp_path.exists():
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    if not successful_records and failures:
        first_error = failures[0].error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=first_error,
        )

    return DocumentUploadResponse(
        documents=successful_records,
        failed=failures,
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(
    document_id: str,
    ingestion_service: DocumentIngestionService = Depends(provide_ingestion_service),
) -> DocumentDeleteResponse:
    try:
        ingestion_service.delete_document(document_id)
        return DocumentDeleteResponse(
            success=True,
            document_id=document_id,
            message="Document deleted successfully",
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found",
        )
