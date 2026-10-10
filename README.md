# Doc Holler — RAG Document Chat

Doc Holler is a transparent, modular Retrieval-Augmented Generation (RAG) web application built with FastAPI, Sentence Transformers, Chroma, and OpenRouter. It enables users to upload multiple documents across PDF, TXT, and DOCX formats, query across the entire collection, view grounded answers with explicit source references, and receive an explicit abstention when documents lack sufficient information.

The frontend is adapted directly from the Preline AI Chat Interface template, providing a clean, accessible, and responsive user experience without frontend build tooling or client-side frameworks.

---

## Key Features

- **Multi-Document Ingestion**: Upload PDF, TXT, and DOCX files in single or multi-file batches.
- **Custom Text Chunking**: Configurable word-based text chunker preserving page boundaries, paragraph structure, and source metadata without relying on external orchestration frameworks.
- **Local Dense Embeddings**: Sentence Transformers (`sentence-transformers/all-MiniLM-L6-v2`) generate document and query embeddings locally.
- **In-Memory Vector Search**: Ephemeral Chroma collection using cosine distance for fast, isolated, session-scoped retrieval.
- **Grounded Answer Generation**: Direct integration with OpenRouter's OpenAI-compatible chat completions API via HTTPX.
- **Strict Evidence Policy & Abstention**: Queries with insufficient retrieved evidence return an exact fallback message without invoking the LLM or hallucinating answers.
- **Source Citations**: Answers display traceable references including filename, page number (for PDFs), and chunk identifiers.
- **Document Management**: View indexed documents, chunk counts, and file sizes, and delete documents with automatic vector cleanup.
- **Preline UI Aesthetics**: Adaptive light/dark theme, responsive mobile navigation, and safe DOM rendering.
- **Temporary Storage Lifecycle**: Ephemeral storage cleans up on shutdown with no persistent database dependencies.

---

## Architecture & Workflows

### 1. Document Ingestion Workflow

1. The client submits one or more files (`.pdf`, `.txt`, `.docx`) via multipart form upload to `POST /api/v1/documents`.
2. The server validates file types, size limits, and non-empty content, generating a unique document ID.
3. The extractor parses document content:
   - **PDF**: PyMuPDF extracts text per page, recording 1-indexed page boundaries.
   - **DOCX**: `python-docx` extracts paragraphs and table text.
   - **TXT**: Native Python text handling decodes UTF-8 (with fallback to Latin-1).
4. The custom chunking service splits sections into word-bounded chunks with overlap, retaining source document ID, filename, chunk index, and page number.
5. The embedding service converts chunk texts into 384-dimensional dense vectors using Sentence Transformers.
6. Chroma registers chunk IDs, embeddings, document texts, and metadata in memory.
7. The document repository records the document as indexed.

### 2. Question Answering Workflow

1. The client submits a question to `POST /api/v1/chat`.
2. The server embeds the query using the same Sentence Transformers model.
3. Chroma performs an approximate nearest neighbor search to retrieve top candidate chunks.
4. The retrieval service evaluates candidate chunks against the configurable relevance distance threshold (`RELEVANCE_DISTANCE_THRESHOLD=1.0`).
5. **Sufficient Evidence**:
   - Chunks meeting the distance threshold are formatted with explicit source headers.
   - A system prompt instructs the OpenRouter model to ground answers solely in the excerpts and report insufficient evidence if unanswered.
   - The generated response is returned alongside structured source citations (`document_id`, `filename`, `page`, `chunk_id`).
6. **Insufficient Evidence**:
   - If no chunks pass the threshold, the backend immediately returns:
     `"I couldn't find sufficient information in the uploaded documents to answer this question."`
   - `answer_found` is set to `false`, sources is set to `[]`, and no external LLM API call is made.

---

## Technology Stack

| Component | Technology | Responsibility |
|---|---|---|
| Runtime | Python 3.12 | Core application language |
| Package Management | `uv` | Locked, reproducible dependency management |
| Web Framework | FastAPI & Uvicorn | Async HTTP API, request validation, static file serving |
| PDF Extraction | PyMuPDF (`pymupdf`) | Page-aware text extraction from PDF files |
| DOCX Extraction | `python-docx` | Paragraph and table text extraction from Word documents |
| Text Chunking | Custom Python Implementation | Word-bounded chunking with configurable overlap |
| Embeddings | `sentence-transformers` | Generates dense vector representations |
| Vector Store | Chroma (`chromadb`) | In-memory ephemeral collection with cosine distance |
| LLM Integration | HTTPX & OpenRouter | Direct HTTP calls to OpenRouter chat completions |
| Frontend | Vanilla HTML, CSS, JavaScript | Preline AI Chat Interface adapted for document Q&A |
| Containerization | Docker & Docker Compose | Container runtime and orchestration |

---

## Prerequisites

- **Python 3.12** or **uv** installed locally.
- **OpenRouter API Key**: Required for LLM answer generation. Obtain one from [openrouter.ai](https://openrouter.ai).
- **Docker & Docker Compose** (optional): For containerized execution.

---

## Environment Configuration

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | `""` | OpenRouter API authentication token |
| `OPENROUTER_MODEL` | `anthropic/claude-3.5-haiku` | Model identifier on OpenRouter |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter completions endpoint |
| `OPENROUTER_TIMEOUT_SECONDS` | `60.0` | HTTP request timeout for LLM calls |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Hugging Face embedding model |
| `CHROMA_COLLECTION_NAME` | `doc_holler_chunks` | In-memory Chroma collection name |
| `RETRIEVAL_TOP_K` | `5` | Maximum candidate chunks to retrieve |
| `RELEVANCE_DISTANCE_THRESHOLD` | `1.0` | Maximum cosine distance to qualify as relevant |
| `CHUNK_SIZE_WORDS` | `250` | Maximum words per chunk |
| `CHUNK_OVERLAP_WORDS` | `40` | Overlap words between consecutive chunks |
| `MAX_UPLOAD_SIZE_BYTES` | `15728640` | Maximum upload size per file (15 MB) |
| `MAX_FILES_PER_UPLOAD` | `10` | Maximum files per batch upload |

---

## Local Setup & Execution

### 1. Install Dependencies with `uv`

```bash
uv sync
```

### 2. Run the Application

```bash
uv run uvicorn doc_holler.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Application Web UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## Running Automated Tests & Linting

### Run Test Suite

```bash
uv run pytest
```

The automated test suite covers:
- PDF, TXT, and DOCX document extraction.
- Empty document and corrupt file validation.
- Text chunking, overlap calculations, and metadata preservation.
- Vector store operations, distance evaluation, and threshold filtering.
- In-memory document repository additions and deletions.
- API endpoints: `/health`, `/documents`, `/chat`.
- Missing-answer fallback behavior and provider failure handling.

### Run Linting & Formatting Checks

```bash
uv run ruff check .
uv run ruff format --check .
```

---

## Docker Deployment

### 1. Build and Run with Docker Compose

```bash
docker compose up --build
```

### 2. Run Container with Docker Directly

```bash
docker build -t doc-holler:latest .
docker run -p 8000:8000 --env-file .env doc-holler:latest
```

The container runs as non-root user `appuser`, exposes port 8000, and includes a native health check calling `/api/v1/health`.

---

## API Contract Summary

### `GET /api/v1/health`
Health check endpoint.
```json
{"status": "ok"}
```

### `GET /api/v1/documents`
Lists all currently indexed documents in the active application instance.
```json
{
  "documents": [
    {
      "id": "a1b2c3d4e5f6",
      "filename": "annual_report.pdf",
      "content_type": "application/pdf",
      "size_bytes": 1048576,
      "status": "indexed",
      "chunk_count": 14
    }
  ]
}
```

### `POST /api/v1/documents`
Uploads one or more files via multipart form data (`files`).
Returns HTTP 201 with successfully indexed documents and any individual failures.

### `DELETE /api/v1/documents/{document_id}`
Deletes the specified document metadata and purges all related chunks from Chroma.
Returns HTTP 200 on success or HTTP 404 if not found.

### `POST /api/v1/chat`
Submits a question across all uploaded documents.
Request:
```json
{"question": "What were the total revenues in Q3?"}
```
Response when evidence is found:
```json
{
  "answer": "According to the financial statement, Q3 revenues reached $4.2M.",
  "sources": [
    {
      "document_id": "a1b2c3d4e5f6",
      "filename": "annual_report.pdf",
      "page": 4,
      "chunk_id": "a1b2c3d4e5f6_chunk_3"
    }
  ],
  "answer_found": true
}
```
Response when evidence is insufficient:
```json
{
  "answer": "I couldn't find sufficient information in the uploaded documents to answer this question.",
  "sources": [],
  "answer_found": false
}
```

---

## Important Constraints & Behavior

1. **Temporary Storage & Ephemeral Lifecycle**:
   All vector indexes, chunk stores, document records, and temporary files exist strictly in memory or temporary OS directories for the lifespan of the running application instance. Restarting the process or container resets all uploaded documents and indices.
2. **Missing-Answer Policy**:
   The application applies an explicit relevance threshold on vector distance. When retrieved passages do not pass this threshold, or when the LLM reports lack of context, the application returns the exact missing-answer response without attempting to guess.
3. **Scanned PDF & OCR Limitations**:
   Optical Character Recognition (OCR) is not included in this release. Image-only or scanned PDFs without embedded text layers produce zero extractable text and are rejected with a clear validation error.
4. **Security & Authentication**:
   Doc Holler has no authentication or user tenancy in this version. All uploaded documents are visible and searchable by anyone with access to the running instance. It is intended for local execution or protected intranet environments.
5. **Embedding Weight Initialization**:
   On first execution, Sentence Transformers downloads the model weights for `all-MiniLM-L6-v2` (~90 MB) from Hugging Face into `~/.cache/huggingface/hub`. Subsequent executions load cached weights immediately.
