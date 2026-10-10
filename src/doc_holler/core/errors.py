class DocHollerError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UnsupportedFormatError(DocHollerError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=400)


class EmptyDocumentError(DocHollerError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=400)


class ExtractionError(DocHollerError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=422)


class DocumentNotFoundError(DocHollerError):
    def __init__(self, document_id: str) -> None:
        super().__init__(message=f"Document '{document_id}' not found", status_code=404)


class NoDocumentsIndexedError(DocHollerError):
    def __init__(self, message: str = "No documents are currently indexed") -> None:
        super().__init__(message=message, status_code=400)


class LLMConfigurationError(DocHollerError):
    def __init__(self, message: str = "OpenRouter is not configured") -> None:
        super().__init__(message=message, status_code=503)


class LLMProviderError(DocHollerError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=502)


class RetrievalError(DocHollerError):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=500)
