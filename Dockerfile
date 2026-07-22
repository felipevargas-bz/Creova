FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system creova && useradd --system --gid creova --create-home creova

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install .

USER creova
EXPOSE 8000
CMD ["creova-api"]
