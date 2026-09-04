# Offline RAG evaluation

`datasets/compliance_v1.json` is a versioned synthetic compliance corpus. It is
safe for CI, makes no paid API calls, and records expected source identifiers,
expected facts and explicit no-answer cases.

Run the mandatory local gate from the repository root:

```bash
python evaluation/runner.py --stores memory chroma --check
```

Run the full store comparison when PostgreSQL with the `vector` extension is
available:

```bash
export RAG_EVAL_PGVECTOR_DSN=postgresql://postgres:postgres@127.0.0.1:5432/rag_eval
python -m evaluation.runner \
  --stores memory chroma pgvector \
  --strategies vector hybrid \
  --require-stores \
  --check
```

The GitHub Actions verification job runs the full command against an isolated
`pgvector/pgvector:pg16` service. The evaluator hashes the dataset bytes into
each report so baseline and final results cannot silently use different input.

This corpus is a regression fixture, not legal advice and not a substitute for
a reviewed production corpus. Expand it by adding documents and cases in a new
versioned file; never rewrite historical results to point at changed content.
