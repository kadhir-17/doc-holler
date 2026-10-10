from fastapi import APIRouter, Depends, HTTPException, status

from doc_holler.core.errors import (
    LLMConfigurationError,
    LLMProviderError,
    NoDocumentsIndexedError,
    RetrievalError,
)
from doc_holler.dependencies import provide_answer_generation_service
from doc_holler.schemas.chat import ChatRequest, ChatResponse
from doc_holler.services.answer_generation import AnswerGenerationService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    answer_service: AnswerGenerationService = Depends(provide_answer_generation_service),
) -> ChatResponse:
    cleaned_question = request.question.strip()
    if not cleaned_question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty or whitespace only",
        )

    try:
        return answer_service.answer_question(cleaned_question)
    except NoDocumentsIndexedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        )
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message,
        )
    except RetrievalError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
        )
