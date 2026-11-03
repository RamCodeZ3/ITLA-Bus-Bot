FROM ghcr.io/astral-sh/uv:0.8.22 AS uv
FROM python:3.12-slim-trixie AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-trixie AS runtime
ARG TARGETARCH
ARG LIGHTPANDA_VERSION=1.0.2
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright \
    PATH="/app/.venv/bin:$PATH" \
    PORT=10000
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && case "$TARGETARCH" in \
       amd64) LP_ARCH=x86_64 ;; arm64) LP_ARCH=aarch64 ;; *) exit 1 ;; esac \
    && curl -fL "https://github.com/lightpanda-io/browser/releases/download/${LIGHTPANDA_VERSION}/lightpanda-${LP_ARCH}-linux" -o /usr/local/bin/lightpanda \
    && chmod 755 /usr/local/bin/lightpanda \
    && useradd --create-home --uid 10001 api
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/* \
    && chmod -R a+rX /opt/playwright
COPY --chown=api:api app ./app
USER api
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','10000')+'/health',timeout=4)"
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port \"${PORT:-10000}\" --workers 1 --no-access-log"]
