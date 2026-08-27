# WP-S2 RAG Service Lockdown

- Date: 2026-08-27
- Status: verified

All FastAPI routes except `/health` now require `X-Internal-API-Key`. Strict mode
defaults to enabled and a missing server key returns HTTP 503 rather than silently
opening routes. An explicit empty CORS value disables browser origins, while a
wildcard origin is rejected. Lightweight runtime/security settings are isolated
from model and vector-store imports so security tests remain fast and deterministic.

The `main` deployment workflow now runs compile and eight security/config/route
policy tests before the production deploy job. The route-policy test fails if a
new unprotected app route or an unreviewed included router is introduced.

Verification:

- `python -m compileall -q API_RAG_NEW chunking llms`: PASS.
- `python -m pytest -q`: PASS, 8/8 tests in 0.80 seconds.
- Runtime container smoke: unavailable locally because Docker is not installed.

Rollback must not re-expose RAG publicly. If necessary, revert this application
commit while keeping Caddy private and the shared key in Compose, then perform a
full-stack redeploy and verify backend-mediated chat/recommendation calls.
