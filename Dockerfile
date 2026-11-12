# syntax=docker/dockerfile:1

# Imagem única do Metis: a API (web) e os workers Celery rodam dela; só o command muda.
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:${PATH}" \
    GUNICORN_CMD_ARGS="--bind 0.0.0.0:8000 --workers 2 --access-logfile -"

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --no-create-home app \
    && mkdir -p /data/media \
    && chown app:app /data/media

# Dependências antes do código, para o cache da camada sobreviver às mudanças no código.
# O flower monta a própria imagem com UV_SYNC_ARGS="--extra flower".
ARG UV_SYNC_ARGS=""
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev ${UV_SYNC_ARGS}

COPY . .

# Defesa extra: se o .dockerignore deixar passar um .env, o build para aqui.
RUN if find /app \( -name ".env" -o -name ".env.*" \) | grep -q .; then \
        echo "Um arquivo .env entrou no contexto de build; confira o .dockerignore." >&2; \
        exit 1; \
    fi

RUN python manage.py collectstatic --noinput

USER app

EXPOSE 8000

# Testa o banco pelo /health/. Workers, beat e flower desligam o healthcheck no compose.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=4)"]

CMD ["gunicorn", "projects.correction.metis.wsgi:application"]
