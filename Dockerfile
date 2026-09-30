# MedReg AI API image: code and dependencies only.
# The Chroma index is mounted at /app/db at run time, and OPENAI_API_KEY
# comes from the environment — neither is ever part of the image.
FROM python:3.13-slim

# uv, copied from its official image; pinned to the version used locally
COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first: this layer is reused until pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Then the code, plus the parsed regulation text needed to (re)build the index
COPY src/ src/
COPY scripts/ scripts/
COPY data/processed/ data/processed/

# Run as an unprivileged user; it only needs to write to the index directory
RUN useradd --create-home app && mkdir -p db && chown app db
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
