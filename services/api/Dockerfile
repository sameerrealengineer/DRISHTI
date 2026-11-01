# Build from the repo root: docker build -f services/api/Dockerfile .
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/venv PATH="/venv/bin:$PATH"
WORKDIR /repo/services/api
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY services/api/ ./
COPY seed/ /repo/seed/
COPY ml/ /repo/ml/
ENV SEED_DIR=/repo/seed
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed.loader && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
