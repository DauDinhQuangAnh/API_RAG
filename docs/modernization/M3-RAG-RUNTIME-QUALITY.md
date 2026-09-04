# Macro Phase M3 - RAG Runtime, Evaluation and Retrieval Quality

Status: PASS

Date: 2026-09-04

## Entry gate

- `WP-S2` RAG lockdown is PASS.
- Backend M1 database/query evidence is recorded in
  `BE_weavecarbon/docs/modernization/M1-BACKEND-DATA-INTEGRITY-SECURITY.md`.
- `BE_weavecarbon`, `Weavecarbon` and `rag` were clean, on `main`, and aligned
  with `origin/main` before implementation.
- Pre-change RAG tests: 8/8 pass.

## Delivered outcome

M3 makes the retrieval path deterministic by default, gives it a non-paid
quality gate, fails closed when retrieved context has insufficient evidence,
preserves real source identifiers in citations, and measures Chroma and
pgvector through one evaluation-store contract. No production collection was
modified or reindexed.

### Runtime and dependency control

- Runtime, development and lightweight evaluation requirement files use exact
  direct dependency pins; `scripts/check_dependency_pins.py` prevents an
  unpinned entry from entering CI.
- CI creates a fresh Python 3.12 environment from `requirements-eval.txt` for
  every run. The runtime image performs a fresh install from `requirements.txt`.
- The container no longer keeps compiler tooling, installs CPU-only Torch,
  includes a health check, and runs as UID/GID `10001` instead of root.
- `sentence-transformers` and Torch are lazy-loaded on the first embedding use,
  rather than during FastAPI import/readiness.

Local process measurements use the same Windows host and portable Python 3.11.9
as `PERFORMANCE_BASELINE.md`. They do not initialize the embedding model.

| Measurement | Immediate pre-change | M3 final | Change |
| --- | ---: | ---: | ---: |
| Uvicorn readiness | 25,053.5 ms | 11,093.8 ms | -55.7% |
| Idle working set | 534,806,528 bytes | 265,654,272 bytes | -50.3% |
| Idle private bytes | 731,340,800 bytes | 432,623,616 bytes | -40.8% |

The historical WP-0B readiness result was 17,576.6 ms and working set was
541,335,552 bytes. Startup timings are sensitive to OS cache, so the memory
reduction and repeatable CI container measurement are the stronger regression
signals. Docker is unavailable locally; CI records image bytes, container cold
start and idle memory in its job summary.

### Versioned evaluation corpus

The immutable input for this phase is
`evaluation/datasets/compliance_v1.json`:

- dataset id: `weavecarbon-compliance-v1`;
- schema version: 1;
- SHA-256: `348e0f3b6205de57b544910488a9727b63b64f28e6a6b0e3207398e10e9d50ad`;
- 8 synthetic compliance documents;
- 10 answerable queries with expected sources/facts;
- 3 explicit no-answer queries;
- deterministic 256-dimensional feature-hash embeddings;
- zero model downloads and zero paid API calls.

The evaluator writes the dataset hash into every report. A baseline and final
result therefore cannot be compared after silently changing their corpus.

### Baseline and final retrieval results

Both rows for each store use the same dataset hash above. Latency is a local
microbenchmark over a very small fixture and is a regression signal, not a
production capacity claim.

| Store | Strategy | Recall@1 | Recall@3 | Citation integrity | Grounded facts | No-answer accuracy | p50 | p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Memory | vector baseline | 90% | 100% | 100% | 100% | 0% | 1.46 ms | 2.33 ms |
| Memory | hybrid final | 90% | 100% | 100% | 100% | 100% | 2.43 ms | 4.63 ms |
| Chroma | vector baseline | 90% | 100% | 100% | 100% | 0% | 1.49 ms | 4.10 ms |
| Chroma | hybrid final | 90% | 100% | 100% | 100% | 100% | 2.61 ms | 4.81 ms |
| pgvector (CI) | vector baseline | 90% | 100% | 100% | 100% | 0% | 0.47 ms | 1.06 ms |
| pgvector (CI) | hybrid final | 90% | 100% | 100% | 100% | 100% | 0.89 ms | 1.10 ms |

The additional local latency buys deterministic evidence rejection: all three
out-of-corpus questions that vector-only retrieval incorrectly treated as
answerable now return an empty context and the explicit Vietnamese no-answer
message. The default reranker is now local `hybrid`; `llm` and `crossencoder`
remain opt-in configurations.

### Citation and metadata invariants

- Ingested `doc_id` is copied to `source_id` when an explicit source identifier
  is absent, before metadata is written to the store.
- Citation responses expose `source_id` while retaining the existing `source`
  and `doc_id` fields.
- Metadata without `source_id`, `doc_id`, or `source` cannot create a citation.
- Citation ordinals are presentation indexes only; no source identifier is
  synthesized from the ordinal or vector rank.

## Vector-store decision

Decision: **retain Chroma for production in M3; do not migrate to pgvector**.

The common `EvaluationVectorStore` contract runs the identical corpus,
embeddings, top-k settings and metrics against Memory, Chroma and pgvector. CI
uses an isolated `pgvector/pgvector:pg16` service and fails if either real store
cannot run. Quality parity alone is not sufficient reason to move production
data. A migration would also need representative production-scale evidence for
latency, write throughput, index build time, storage, backup/restore and operator
ownership. M3 has no such evidence, so moving data would add risk without a
demonstrated product gain.

Operational tradeoffs:

- Chroma keeps the current deployment and collection identity simple, but its
  local persistent files require explicit volume backup and single-service
  ownership.
- pgvector could consolidate backup, access control and observability with
  PostgreSQL, but introduces extension/version management, vector index tuning,
  database load isolation and a potentially expensive re-embed/index migration.
- The evaluation interface is deliberately not a production dual-write layer.
  It prevents benchmark drift while leaving current storage behavior unchanged.

## Future migration and reindex plan

A later proposal may reconsider pgvector only with a production-sized, reviewed
corpus and the same evaluation contract. The safe sequence is:

1. Freeze the embedding model name, dimension, chunking profile and dataset hash.
2. Back up the Chroma volume and export every record id, document and metadata.
3. Create a separate pgvector schema/table and build the chosen vector index;
   do not write into existing PostgreSQL application tables.
4. Reindex from the exported source records, preserving record id, `source_id`,
   `doc_id`, source location, chunk order and embedding version.
5. Compare counts and metadata hashes, then run the full corpus and a reviewed
   shadow production sample against both stores.
6. Cut reads over behind a separately reviewed runtime store selector. Keep
   Chroma read-only during the observation window.
7. Roll back by selecting Chroma again; do not delete either store until backup,
   restore and observation gates pass.

## Verification and rollback

Local evidence before push:

- dependency pin policy: PASS (3 files);
- Python compileall: PASS;
- pytest: PASS, 19/19;
- offline Memory + Chroma evaluation quality gate: PASS;
- workflow YAML parse: PASS;
- `git diff --check`: PASS.

GitHub Actions run `33850105712` for implementation commit `cb0131c` completed
successfully:

- `verify`: fresh Python 3.12.14 evaluation install, `pip check`, compileall,
  19 tests, and Memory/Chroma/pgvector gates passed;
- `container`: fresh full runtime install and `pip check` passed; final image
  size was 1,797,371,938 bytes, cold start was 3,323 ms, and idle memory was
  196.9 MiB;
- `deploy`: VPS built the CPU-only image, changed only the mounted RAG data/cache
  ownership to UID/GID 10001, recreated RAG, and observed RAG and proxy healthy.

The supporting deployment change is frontend commit `e28d5df`. The application
implementation is RAG commit `cb0131c`. Production retained the existing Chroma
volume; no collection was deleted or reindexed.

Application rollback is a normal revert of the M3 commit. Existing Chroma files
remain compatible because M3 has no schema migration and no automatic reindex.
During an incident, operators may temporarily set `RAG_RERANKER_TYPE=llm` and
`RAG_ENABLE_EVIDENCE_GUARD=false` only if the resulting paid-call and unsupported
answer risk is explicitly accepted. The preferred rollback is reverting the
application while retaining the locked dependency and non-root container work.
