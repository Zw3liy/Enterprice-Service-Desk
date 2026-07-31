# Release Notes — v1.0.0-rc.1

**Codename:** Enterprise Service Desk Release Candidate 1  
**Date:** 2026-07-31

## Highlights
- Production-shaped ITSM core with ITIL processes, CMDB, portal, security, and automation
- REST APIs across modules + constrained GraphQL endpoint
- Billing, multi-tenant metadata, marketplace integrations
- Inventory/procurement, SOC, vulnerabilities, analytics/forecasting

## Upgrade
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap_esd --with-demo
python manage.py collectstatic --noinput
python manage.py runserver
```

## Verification performed
- `manage.py check` — clean
- `makemigrations --check` — clean
- Full ESD test suite — pass
- Smoke: login, dashboard, ticket/asset/knowledge CRUD, SLA, workflow, APIs

## Known limitations
- Full Docker/Postgres/Redis stack requires host services
- Some legacy empty directories outside installed apps remain as roadmap placeholders
- GraphQL surface is intentionally limited

## Security notes
- Change `DJANGO_SECRET_KEY` and bootstrap admin password before any shared deploy
- Set `DJANGO_DEBUG=False` and HTTPS cookie flags in production
