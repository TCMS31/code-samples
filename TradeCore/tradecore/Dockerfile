# syntax=docker/dockerfile:1

# ---- build stage: resolve wheels once, without build tools in the runtime ----
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /wheels
COPY requirements.txt .
RUN python -m pip wheel --wheel-dir /wheels -r requirements.txt


# ---- runtime ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN python -m pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=appuser:appuser . .

# /app itself is root-owned, so SQLite needs a directory appuser can write to.
# Compose mounts a named volume here.
RUN mkdir -p /app/data && chown appuser:appuser /app/data
ENV SQLITE_PATH=/app/data/db.sqlite3

USER appuser

EXPOSE 8000

# The admin login page answers 200 without a user or a token. /api/user/1 was
# used before, but urlopen raises on its 404, so a fresh container never
# turned healthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/admin/login/', timeout=4)" \
    || exit 1

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
