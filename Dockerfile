# Enterprise Service Desk — production image
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/media /app/staticfiles \
    && chmod +x /app/deployment/scripts/entrypoint.sh || true

EXPOSE 8000

ENV DJANGO_SETTINGS_MODULE=ticketing.settings \
    DJANGO_DEBUG=False

CMD ["gunicorn", "ticketing.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
