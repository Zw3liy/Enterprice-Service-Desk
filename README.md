# Enterprise Service Desk (ESD)

Production-oriented ITSM platform built with **Django 5** and **Django REST Framework**.

Comparable capability areas: ticketing, ITIL processes, CMDB, portal, SLA/automation, security (MFA/SSO/RBAC/PAM/SOC), billing, inventory/procurement, analytics, and AI assist.

**Version:** see [`VERSION`](VERSION) (`1.0.0-rc.1`)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py bootstrap_esd --with-demo
python manage.py runserver
```

Open http://127.0.0.1:8000/ — bootstrap user **`admin` / `admin123!`** (change immediately).

## Documentation
| Doc | Description |
|-----|-------------|
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Completion status & metrics |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [ROADMAP.md](ROADMAP.md) | Upcoming work |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev workflow |
| [SECURITY.md](SECURITY.md) | Security policy |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deploy guide |
| [docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) | Administrator guide |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | End-user guide |
| [docs/API.md](docs/API.md) | REST API |
| [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md) | Backup/DR |
| [docs/RELEASE_NOTES_1.0.0-rc.1.md](docs/RELEASE_NOTES_1.0.0-rc.1.md) | RC notes |

## API
Base: `/api/v1/` (core tickets/assets/knowledge) plus module APIs (`/incidents/`, `/cmdb/`, `/billing/`, `/graphql/`, …).

```bash
# Token
python manage.py shell -c "from rest_framework.authtoken.models import Token; from django.contrib.auth import get_user_model; u=get_user_model().objects.get(username='admin'); t,_=Token.objects.get_or_create(user=u); print(t.key)"
curl -H "Authorization: Token <token>" http://127.0.0.1:8000/api/v1/tickets/
```

## Tests
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Docker
```bash
docker compose -f docker-compose.development.yml up --build
# full stack:
docker compose up --build
```

## License
See [LICENSE](LICENSE).
 
