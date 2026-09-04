# M4 RAG Operations Evidence

Status: implementation complete; immutable production evidence is emitted by
`rag-deploy.yml`.

- `/health` is model-independent liveness and `/ready` verifies the persistent
  Chroma store without eagerly loading the embedding model.
- Middleware validates or creates `X-Correlation-ID`, returns it to the caller,
  writes structured JSON request logs, and records low-cardinality metrics.
- `/metrics` is protected by the internal API key. Logs contain only an explicit
  operational allowlist and never request headers or bodies.
- Embedding cache keys include an explicit cache version and hit/miss counters.
- FastAPI lifespan marks readiness false during graceful shutdown.
- CI covers pull requests, syntax, unit/policy tests, retrieval quality, vector-store
  parity, Critical image scanning, SBOM generation, non-root enforcement, size/cold
  start/memory measurement, and immutable digest publication with provenance.
- Production deploy promotes that exact digest and automatically restores the
  previous digest if readiness smoke testing fails.

Local verification: `python -m compileall -q API_RAG_NEW` and `python -m pytest -q`.
