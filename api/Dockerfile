FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --no-dev --no-install-project

COPY api/src/ src/
COPY docs/source_registry_br_v1.csv /app/docs/source_registry_br_v1.csv
COPY infra/scripts/api-readiness.py /app/api-readiness.py
ENV BRACC_SOURCE_REGISTRY_PATH=/app/docs/source_registry_br_v1.csv

RUN uv sync --no-dev

LABEL org.brasil-em-rede.api-source-catalog="v1"
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "bracc.main:app", "--host", "0.0.0.0", "--port", "8000"]
