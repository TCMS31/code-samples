# syntax=docker/dockerfile:1

# ---- build stage: pandas/numpy wheels resolved here, not in the runtime ----
FROM python:3.10-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /wheels
COPY requirements.txt .
RUN python -m pip wheel --wheel-dir /wheels -r requirements.txt


# ---- runtime ----
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN python -m pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=appuser:appuser . .

# Analysis output is written at runtime.
RUN mkdir -p /app/aviyel_api/output_files && chown appuser:appuser /app/aviyel_api/output_files

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/analysis/?keyword=travel', timeout=4).status < 500 else 1)" \
    || exit 1

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
