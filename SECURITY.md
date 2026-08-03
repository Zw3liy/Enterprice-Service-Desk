# Security Policy

## Supported versions
| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes |
| 0.x     | No |

## Reporting a vulnerability
Email security issues to the repository maintainers (do not open public issues for active exploits).

Include: affected component, reproduction steps, impact, and any suggested fix.

## Hardening checklist (production)
- Set strong `DJANGO_SECRET_KEY` via environment
- `DJANGO_DEBUG=False`
- Configure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`
- Enable `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- Use PostgreSQL + Redis; disable `CELERY_TASK_ALWAYS_EAGER`
- Rotate bootstrap admin password
- Restrict `/admin/` and management endpoints via network policy
- Review webhook secrets and integration credentials
- Enable MFA for privileged users (`/mfa/setup/`)

## Built-in controls
- Django CSRF middleware and session security flags
- DRF authentication (session + token) and throttling
- RBAC groups/roles and object-level staff checks on sensitive APIs
- Tenant company scoping helpers
- Audit log model + SIEM export (`/api/security/siem/export/`)
- Webhook HMAC signing (`X-ESD-Signature`)
- Password validators (Django defaults)

## OWASP notes
Input validation is enforced in forms, serializers, and service layers. File uploads use Django `FileField` under `MEDIA_ROOT`. Always serve media via a hardened reverse proxy in production.
