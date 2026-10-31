# AgentAudit web service (REST hook + UI). The Clocked key is supplied at runtime, never baked in:
#   docker build -t agentaudit .
#   docker run -p 7860:7860 -e CLOCKED_API_KEY=... agentaudit
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN useradd -m app
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY src ./src
RUN uv sync --frozen --no-dev
COPY web ./web
COPY examples ./examples
ENV PATH="/app/.venv/bin:$PATH" PORT=7860 \
    AGENTAUDIT_CACHE=/tmp/agentaudit-cache AGENTAUDIT_LEDGER=/tmp/agentaudit-ledger.jsonl \
    AGENTAUDIT_DAILY_CREDITS=1500
USER app
EXPOSE 7860
CMD ["sh", "-c", "uvicorn agentaudit.server:app --host 0.0.0.0 --port ${PORT}"]
