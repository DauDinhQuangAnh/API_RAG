FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    NLTK_DATA=/app/.cache/nltk

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 rag \
    && useradd --system --uid 10001 --gid rag --home-dir /app --shell /usr/sbin/nologin rag

COPY requirements.txt .

ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN python -m pip install --index-url "${TORCH_INDEX_URL}" torch==2.12.1 \
    && python -m pip install --requirement requirements.txt

COPY --chown=rag:rag . .
RUN mkdir -p /app/db /app/.cache/huggingface /app/.cache/nltk \
    && chown -R rag:rag /app/db /app/.cache

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3).read()"]

CMD ["uvicorn", "API_RAG_NEW.main:app", "--host", "0.0.0.0", "--port", "8000"]
