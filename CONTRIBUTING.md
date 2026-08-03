# Contributing

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py bootstrap_esd --with-demo
python manage.py runserver
```

Default bootstrap login: `admin` / `admin123!` (change immediately).

## Branching
- Work on feature branches from the session branch / `main`.
- Keep commits focused and green (`manage.py check`, `test`).

## Code standards
- PEP 8, type hints on public services, docstrings on modules/services.
- Business logic in `services.py`; thin views/serializers.
- No empty files, TODOs, `pass`-only stubs, or `NotImplementedError`.
- Tenant-aware querysets must filter by `company` when applicable.

## Tests
```bash
python manage.py test
# or module-focused:
python manage.py test apps.service_desk apps.inventory -v 1
```

## Migrations
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

Never rewrite applied migrations.

## Pull requests
Include: summary, test commands run, migration notes, security impact.
