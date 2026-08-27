# WP-0B RAG Performance and Delivery Baseline

- Measurement date: 2026-08-27
- Commit measured: `cf13e065f9d254837b87f66e382a9ce160a4f0a2`
- Result: **PARTIAL** — local import/readiness/memory and lightweight endpoints
  are measured; Docker image and retrieval/LLM workloads are unavailable.
- Product behavior changes: none

## Measurement environment

- Windows 11 Pro 64-bit, Intel Core i5-6500 (4 cores / 4 threads), 15.43 GiB RAM
- Portable Python `3.11.9`; Docker/CI use Python 3.12
- Repository: `D:\hoctap\WCB\rag`
- `openpyxl 3.1.5` was added to the supplied portable environment for the
  measurement. `psycopg2-binary` download repeatedly stalled and remains absent.
- The application import/startup path used below does not access PostgreSQL,
  download an embedding model, query Chroma or call a paid LLM.

## Static and validation baseline

| Measurement | Baseline |
| --- | ---: |
| Tracked files / bytes | 42 / 260,205 |
| Python files / bytes | 32 / 195,691 |
| Local Chroma files / bytes | 21 / 2,468,660 |
| `compileall` wall time | 0.264 s |
| `pytest -q` | 8 pass; 1.735 s external wall time (0.63 s pytest time) |

## Import, readiness and idle memory

Method: add the repository root to `sys.path`, import `API_RAG_NEW.main`, then in
a separate process start Uvicorn on loopback with strict internal auth enabled.
Readiness is the first successful `/health` response.

| Measurement | Baseline |
| --- | ---: |
| One application import | 19.274 s |
| Uvicorn readiness | 17,576.585 ms |
| Idle working set at readiness | 541,335,552 bytes (516.26 MiB) |
| Idle private bytes at readiness | 733,859,840 bytes (699.86 MiB) |

These are process-level local measurements with OS file cache effects. They do
not include embedding model initialization; a first real query may be materially
slower and use more memory.

## Lightweight endpoint latency

Each route was measured in a separate local process after 5 warm-up requests,
then 50 sequential loopback requests. `/runtime-config` included a valid internal
API key. Results include Python HTTP client overhead, not browser/network time.

| Route | p50 | p95 | Mean | Max |
| --- | ---: | ---: | ---: | ---: |
| `GET /health` | 9.753 ms | 29.945 ms | 13.067 ms | 57.987 ms |
| `GET /runtime-config` | 5.197 ms | 6.006 ms | 5.281 ms | 6.198 ms |

The two rows are not a route-vs-route performance comparison because they came
from separate process runs. They are repeatable baselines for their own method.

## CI and deployment baseline

- RAG workflow run `33036476965`: success in 19 s overall.
- Verify job: 10 s; deploy job: 4 s.
- The deploy job intentionally skipped VPS access because `DEPLOY_HOST`,
  `DEPLOY_USER` and `DEPLOY_SSH_KEY` are not configured in the RAG repository.
- Current delivery builds RAG from source on the VPS; unlike frontend/backend,
  there is no immutable registry image to inspect for this commit.

## Unavailable measurements and repeat plan

- Docker image size, container cold start and container memory: Docker is absent.
- First embedding model load, query p50/p95, ingest throughput and retrieval/LLM
  latency: not run because they require a pinned model/cache, representative
  corpus/evaluation queries and explicit permission for any paid LLM call.
- CPU utilization under concurrency: no load scenario is defined yet.

Repeat image/runtime measurements after WP-R1 on the same Docker runner. Query
quality/performance baselines belong to WP-R2 and must use a versioned offline
evaluation set. No optimization claim is made here. Rollback is reverting this
documentation-only commit.
