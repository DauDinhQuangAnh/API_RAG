# WP-S3 RAG Repository Hygiene

- Date: 2026-08-28
- Baseline commit: `dfaa8aa`
- Result: **PASS**
- RAG behavior changes: none

## Artifact and dependency audit

No runtime artifact was tracked. Existing local Chroma data, Python bytecode, pytest caches, environment files and embedding-model state are already ignored.

`.gitignore` now also covers Ruff/coverage output, local artifacts, uploads, backups and restore drills. `.dockerignore` now excludes the local Chroma `db`, embedding state, caches, tests, docs, CI metadata, artifacts, uploads and the backend database schema. These files are not runtime source for the RAG image.

All 16 direct requirements have a proven source, Docker or framework consumer. In particular, `uvicorn` is the container command and `python-multipart` is loaded by FastAPI for `File`/`Form` routes even though neither appears as a normal application import. No requirement was removed.

Requirements are still unpinned and resolve to current registry versions. That reproducibility gap is deliberately assigned to WP-R1; WP-S3 did not broaden into dependency locking or runtime slimming.

## Docker context evidence

Docker is unavailable locally, so the same uncompressed tar approximation was measured before and after:

| Measurement | Before | After | Change |
| --- | ---: | ---: | ---: |
| Approximate context bytes | 2,805,760 | 225,280 | -2,580,480 (-91.97%) |
| Archive entries | 93 | 36 | -57 (-61.29%) |

Most of the reduction comes from excluding local Chroma/vector state and Python caches. CI/VPS Docker build remains the authoritative image build validation.

## Fresh-install and test evidence

The supplied portable Python lacks the standard `venv` module. To retain isolation, pip installed `requirements.txt` with `--ignore-installed --no-cache-dir --target` into a new empty directory outside all three repositories.

- Fresh target install: PASS; 46,024 files and 1,383,430,835 bytes before cleanup.
- Isolated imports: PASS for Chroma, FastAPI/Uvicorn, multipart, Google GenAI, NumPy, Transformers, Torch, PDF/DOCX/XLSX parsers, backoff, NLTK, dotenv, sentence-transformers and psycopg2.
- `pytest -q`: PASS, 8 tests.
- Temporary install target: removed after verification; it is reproducible from `requirements.txt`.
- `git diff --check`: PASS.

No embedding model was downloaded, no paid LLM was called, and no PostgreSQL or production data was accessed.

## Rollback

Revert the WP-S3 commit to restore the earlier ignore rules. Local Chroma data is not modified and no index rebuild or data restore is required.
