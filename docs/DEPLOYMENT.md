# Deployment Guide

## Local (SQLite)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py bootstrap_esd --with-demo
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000
```

## Docker Compose (Postgres + Redis)
```bash
cp .env.example .env
# set DJANGO_SECRET_KEY, DEBUG=False for shared envs
docker compose up --build
```

Services: `web` (gunicorn), `db` (Postgres 16), `redis`, `worker` (Celery).

## Environment variables
See `.env.example` for:
- Django secret/debug/hosts
- Database engine and credentials
- Redis / Celery URLs
- Email / IMAP
- Azure AD / Google OAuth
- AI provider keys

## Kubernetes
Manifests under `deployment/kubernetes/`:
- `deployment.yaml`, `service.yaml`, `ingress.yaml`

Provide secrets: `esd-app` (`secret-key`), `esd-db` (`username`/`password`).

## Nginx
`deployment/nginx/nginx.conf` proxies to gunicorn and serves `/static/` and `/media/`.

## Health
- Liveness: `GET /healthz/`
- Readiness: `GET /ready/`

## Backups
```bash
./deployment/scripts/backup.sh
```
For Postgres use `pg_dump`. Restore media tarballs alongside DB restore.

## Celery
```bash
celery -A ticketing worker -l info
python manage.py scan_sla
python manage.py run_due_reports
```
