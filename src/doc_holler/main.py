from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from doc_holler.api.routes.chat import router as chat_router
from doc_holler.api.routes.documents import router as documents_router
from doc_holler.api.routes.health import router as health_router
from doc_holler.core.config import get_settings
from doc_holler.core.errors import DocHollerError
from doc_holler.dependencies import (
    provide_document_repository,
    provide_vector_store,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    provide_vector_store().clear()
    provide_document_repository().clear()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Doc Holler",
        description="Retrieval-Augmented Generation (RAG) Document Chat",
        version="0.1.0",
        lifespan=lifespan,
    )

    allow_credentials = False if settings.cors_origins == ["*"] else True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DocHollerError)
    async def doc_holler_exception_handler(request: Request, exc: DocHollerError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(documents_router, prefix=settings.api_prefix)
    app.include_router(chat_router, prefix=settings.api_prefix)

    if settings.static_dir.exists():
        app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

        @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
        async def serve_index() -> FileResponse:
            index_path = settings.static_dir / "index.html"
            return FileResponse(index_path)

    return app


app = create_app()
