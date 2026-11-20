FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev && useradd --create-home --uid 10001 buildwise
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" PORT=8000
USER buildwise
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.scripts.seed_sample && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT} --no-access-log"]
