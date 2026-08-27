# WP-0A RAG Baseline

- Date: 2026-08-27
- Repository: `D:\hoctap\WCB\rag` (remote repository name: `API_RAG`)
- Remote: `https://github.com/DauDinhQuangAnh/API_RAG.git`
- Baseline commit: `a4a3969` (`fix: remove duplicate /extract route, add psycopg2-binary, add llms/__init__.py`)
- Working branch: `codex/wp-0a-baseline`

WP-0A result: **PASS** — inventory is complete; the current local startup failure and P0 exposure risk are recorded below.

## Scope and invariants

This work package changed documentation only. It did not install/upgrade Python packages, download models, modify Chroma collections, ingest documents, query an external LLM, access production data, or deploy anything.

## Runtime and repository inventory

- FastAPI application at `API_RAG_NEW.main:app`, served by Uvicorn on port 8000.
- Local diagnostic runtime: portable Python `3.11.9` and pip `26.1.2` under `D:\hoctap\python`.
- Docker and GitHub Actions target Python 3.12, so local and deployment minor versions differ.
- 35 tracked files, including 27 Python files; no tracked Python tests were found.
- Dependencies are declared as unpinned names in `requirements.txt`; there is no deterministic lock file.
- Main flow:
  - extraction for PDF/DOCX/TXT/XLSX inputs;
  - semantic/hybrid chunking;
  - local sentence-transformer embeddings;
  - persistent Chroma storage;
  - retrieval and optional neighbor expansion;
  - reranking;
  - Gemini generation with citations/no-context behavior.
- Bounded concurrency exists for query, LLM, ingest and embedding work.
- Chroma data defaults to `db/`; embedding/model state and caches are local generated state and ignored by Git.
- `database.py` provides PostgreSQL access for recommendation-related data using `psycopg2`.

## API surface and security boundary

Primary routes include:

- Health/runtime: `GET /health`, `GET /runtime-config`, `GET /runtime-status`
- Direct generation: `POST /chat/gemini`, company recommendations and product recommendations
- Collection CRUD/records for `/collections/*` and duplicated `/local/collections/*` compatibility routes
- Document ingest/extract/list/delete
- Query and streaming query endpoints

`require_internal_api_key` checks `X-Internal-API-Key` with constant-time comparison when `RAG_INTERNAL_API_KEY` is configured. Its current behavior is fail-open when the key is absent unless `RAG_REQUIRE_INTERNAL_API_KEY=true`.

Important current behavior:

- `/health` is intentionally unauthenticated.
- `/chat/gemini` and the two recommendation endpoints do not declare the internal-key dependency.
- Most collection, runtime, ingest, extract and query routes declare the dependency, but remain effectively unauthenticated when no key is configured and strict mode is false.
- Frontend Caddy config publicly reverse-proxies `/rag/*` to this service.
- Production Compose does not inject `RAG_INTERNAL_API_KEY` or `RAG_REQUIRE_INTERNAL_API_KEY`.

This combination is a confirmed P0 configuration/design risk. `WP-S2` must run immediately after WP-0A.

## Cross-service contracts

- Backend proxies chat, recommendations, administration, collection, ingest and query operations and can send `X-Internal-API-Key`.
- Frontend mostly consumes the backend proxy, but two recommendation helpers retain a direct RAG HTTP path.
- Request/response models in `API_RAG_NEW/schemas.py`, citation fields in `citations.py`, collection naming/metadata and SSE event behavior are compatibility boundaries.
- RAG `ROOT_PATH=/rag` is expected by the current public Caddy route.
- Persistent source documents/metadata and Chroma collection identity must be preserved until later evaluation/storage work proves a safe migration or reindex path.

## Environment variables

No `.env` values were read or copied. `.env`, `db/`, Python caches and `.embedding_model_state.json` are ignored and not tracked.

Secrets:

- `GEMINI_API_KEY`
- `RAG_INTERNAL_API_KEY`
- `DB_PASSWORD`
- `HF_TOKEN` when used by the deployment/model download path

Non-secret/configuration:

- Service/network/storage: `ROOT_PATH`, `RAG_CORS_ORIGINS`, `CHROMA_DB_PATH`, `CHROMA_DB_PATH_LOCAL`
- Models/retrieval: `GEMINI_MODEL`, `GEMINI_RERANKER_MODEL`, `RAG_LOCAL_EMBEDDING_MODEL`, `RAG_LOCAL_EMBEDDING_DIMENSION`, `RAG_RERANKER_TYPE`, `RAG_CROSS_ENCODER_MODEL`, `RAG_INITIAL_TOP_K`, `RAG_FINAL_TOP_N`, `RAG_CHUNKING_PROFILE`, `RAG_INCLUDE_NEIGHBORS`, `RAG_ENABLE_DISTANCE_GUARD`, `RAG_MAX_DISTANCE`, `RAG_MAX_CONTEXT_EXPANSION_PER_CANDIDATE`, `RAG_MAX_TOTAL_CANDIDATES`
- Concurrency/timeouts: maximum concurrent queries, LLM calls, ingests and embedding calls plus their queue timeouts
- Behavior/debug: `RAG_ENABLE_FINAL_ANSWER_FALLBACK`, `RAG_DEBUG_MODE`, `RAG_EMBEDDING_CACHE_SIZE`, `RAG_REQUIRE_INTERNAL_API_KEY`
- PostgreSQL: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`

`.env.example` includes the internal key only as an optional commented placeholder, but omits the strict-mode flag, PostgreSQL variables and several configuration values referenced by code. This is documentation/configuration drift.

## Dependency state

Declared dependencies are unpinned. The supplied portable Python currently contains the major ML/web dependencies, but two declared runtime packages are absent:

- `openpyxl` — missing; this is the first startup-import failure.
- `psycopg2-binary` — missing as an installed distribution.

`pip check` reports no broken relationships among packages that are installed, but it does not detect packages missing from `requirements.txt` expectations.

## Docker and CI/CD inventory

- `Dockerfile` uses `python:3.12-slim`, installs build tools, performs an unpinned `pip install -r requirements.txt`, copies the full filtered context and runs Uvicorn on port 8000.
- The container currently runs as root.
- `.dockerignore` excludes Git, virtual environments, `.env`, Python/test caches and logs, but does not explicitly exclude all model/cache forms.
- Only `rag-deploy.yml` exists. It deploys from `main`, runs `compileall` only when deploy secrets are available, SSHes to the VPS, pulls all three repositories and invokes the frontend deployment script.
- There is no independent required pull-request CI for RAG, no automated unit/evaluation gate and no locked-install check.

## Verification evidence

| Check | Result | Evidence |
|---|---|---|
| Git pre-check | PASS | `main` was clean and tracked `origin/main`; branch `codex/wp-0a-baseline` created. |
| `python -m compileall -q ...` | PASS | All tracked Python modules compiled successfully. |
| Declared-package inventory | PARTIAL | Most packages are installed; `openpyxl` and `psycopg2-binary` are missing from the supplied portable environment. |
| `python -m pip check` | PASS with limitation | Installed distributions have no broken requirements; missing top-level declared packages are listed separately. |
| `import API_RAG_NEW.main` | FAIL (pre-existing environment) | `ModuleNotFoundError: openpyxl`; no model download or service startup was attempted after this failure. |
| Automated tests | UNAVAILABLE | No tracked Python test files or test command were found. |
| Uvicorn startup/health | BLOCKED | Application import fails before startup because declared packages are missing locally. |
| Docker build/image inspection | UNAVAILABLE | Docker CLI/daemon is not available in the current execution environment. |

## Pre-existing findings and risks

1. **P0 — public/fail-open RAG security:** current Caddy exposure plus missing strict internal-key configuration leaves privileged/expensive endpoints reachable without guaranteed authentication.
2. **Reproducibility:** all Python requirements are unpinned; local Python 3.11 differs from Docker/CI Python 3.12.
3. **Local startup blocked:** the supplied Python environment is missing two declared packages.
4. **No automated test/evaluation suite:** syntax compilation is the only local/CI-equivalent verification currently available.
5. **Deployment coupling:** the RAG workflow pulls and redeploys all three repositories rather than promoting one immutable RAG artifact.
6. **Container security/size:** the runtime is root and includes compiler tooling in the final image; ML dependencies are expected to make it large, but size cannot be measured without Docker.
7. **Default database password in code:** `database.py` falls back to a literal development password. Production must always provide `DB_PASSWORD`; removal/hardening belongs to a later scoped security package.

## Likely performance- and quality-sensitive paths (not yet measured)

- Local embedding model load/cold start and memory footprint.
- Semantic chunking and large document extraction/ingestion.
- Chroma batch writes and query latency.
- Candidate expansion, cross-encoder/LLM reranking and Gemini generation.
- Citation construction and streaming responses.

Cold-start, memory, image-size, latency and retrieval-quality measurements belong to `WP-0B`/RAG evaluation packages; no improvement is claimed here.

## Rollback

Delete this documentation file and revert the WP-0A documentation commit. No runtime rollback, migration rollback, collection restore or data restore is required.
