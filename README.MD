# WeaveCarbon — RAG Service

A **FastAPI** retrieval-augmented-generation service that gives WeaveCarbon its
compliance intelligence: it ingests export-market and regulatory documents into a
vector store and answers questions / generates recommendations **grounded in that
corpus with citations**, rather than free-form LLM guesses.

> Do **not** commit `.env`, API keys, user data, sample uploads, runtime logs, or
> collection contents.

## Role in the platform

The main API (`BE_weavecarbon`) calls this service to:

- answer compliance questions over ingested market-requirement documents;
- generate **company** and **product** recommendations grounded in that corpus;
- keep answers auditable via citations back to the source chunks.

## How it works

Ingest → **semantic chunking** → **embeddings** (local SBERT or an online
provider) → vector store (Chroma). Query → retrieve → **rerank** → LLM answer with
citations. Ingest and query run under bounded concurrency slots. Every route
except `/health` requires the internal API key.

## Run locally

```bash
python -m venv .venv
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn API_RAG_NEW.main:app --host 0.0.0.0 --port 8000
```

Or the portable Python bundled in the repo, if present:

```bash
.\python\python.exe -m uvicorn API_RAG_NEW.main:app --host 0.0.0.0 --port 8000
```

Default local base URL: `http://127.0.0.1:8000`. Do not expose this service
directly with a public tunnel or reverse proxy; the Node backend is the public
control plane.

## Configuration

Copy `.env.example` to `.env` and fill in local values — `.env` holds secrets and
must not be committed. Configure the same long random `RAG_INTERNAL_API_KEY` in
this service and the Node backend. Internal authentication is required by
default. For isolated loopback-only development, it can be explicitly disabled
with `RAG_REQUIRE_INTERNAL_API_KEY=false`; never use that setting in staging or
production. An explicitly empty `RAG_CORS_ORIGINS` disables browser origins.

## Main API

- `GET /health` — minimal unauthenticated server check
- `GET /runtime-config` — authenticated non-secret runtime config
- `POST /chat/gemini` — direct chat
- `POST /recommendations/company/{id}` · `POST /recommendations/product/{id}`
- `GET /collections` · `POST /collections` — list / create
- `GET|PATCH|DELETE /collections/{name}` — inspect / update / delete
- `GET /collections/{name}/records` — records in a collection
- `POST /ingest` — ingest a document (PDF / DOCX / TXT)
- `POST /collections/{name}/query` — RAG Q&A over a collection

### Examples

Ingest:

```bash
curl -X POST http://127.0.0.1:8000/ingest ^
  -H "X-Internal-API-Key: replace_with_internal_secret" ^
  -F "file=@document.pdf" ^
  -F "collection_name=rag_collection_demo"
```

Query:

```bash
curl -X POST http://127.0.0.1:8000/collections/rag_collection_demo/query ^
  -H "X-Internal-API-Key: replace_with_internal_secret" ^
  -H "Content-Type: application/json" ^
  -d "{\"query\": \"Tom tat tai lieu\", \"number_docs_retrieval\": 3}"
```
