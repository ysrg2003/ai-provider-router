FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
COPY config ./config

RUN python -m pip install --no-cache-dir .

ENTRYPOINT ["ai-router"]
CMD ["--config-dir", "config", "summary"]
