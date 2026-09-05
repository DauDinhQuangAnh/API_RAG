# RAG Modernization Summary

RAG modernization closed on 2026-09-05. Historical work-package reports and point-in-time baselines were removed from the active source tree; Git history preserves them.

## Final status

Status: **PASS**

The service now provides:

- private backend-to-RAG authentication with direct public routes removed;
- pinned runtime dependencies, a non-root hardened container and readiness checks;
- bounded query, ingest, embedding and LLM concurrency;
- deterministic Memory, Chroma and pgvector evaluation coverage;
- hybrid retrieval, evidence guards, reranking and citation/source invariants;
- correlation IDs, structured operational counters and stage latency metrics;
- persistent Chroma storage with a documented future pgvector migration boundary;
- CI gates for tests, evaluation, security, container health, image publishing and VPS deployment.

## Ongoing gates

- Run the pytest suite for code changes.
- Run `python -m evaluation.runner --stores memory chroma --strategies vector hybrid --require-stores` for retrieval changes.
- Treat `README.md`, `evaluation/README.md`, `.env.example`, `Dockerfile` and `.github/workflows/rag-deploy.yml` as active documentation and configuration.
- Cross-service capacity and recovery certification remains deferred until the frontend repository's full isolated staging workflow runs.
