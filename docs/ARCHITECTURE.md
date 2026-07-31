# Architecture

## Overview
Enterprise Service Desk (ESD) is a Django monolith with modular apps under `apps/`, REST (DRF) APIs, optional Celery workers, and Jinja/Django templates for technician and portal UI.

```
Browser / API clients
        │
        ▼
ticketing/urls.py  ──► app urlconfs ──► views / viewsets
                              │
                              ▼
                     services (domain logic)
                              │
                              ▼
                     models (PostgreSQL/SQLite)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
           Redis cache    Celery tasks    Media/static
```

## Layers
1. **Presentation** — Django templates + DRF serializers/viewsets
2. **Application services** — `services.py` per app (transactions, orchestration)
3. **Domain models** — Django ORM aggregates (`Ticket`, `Company`, CMDB CI, etc.)
4. **Infrastructure** — email, webhooks, LDAP/M365 connectors, storage

## Tenancy
`Company` is the tenant boundary. `apps.service_desk.tenancy` resolves active company from session/agent profile. Multi-tenant metadata lives in `apps.multi_tenant`.

## Cross-cutting
- **Audit:** `AuditLog` + SIEM export
- **Events:** `apps.event_engine.EventBus`
- **Automation:** `AutomationRule` + business rules
- **AuthZ:** Django permissions + `apps.rbac`

## Key packages
| Package | Responsibility |
|---------|----------------|
| `service_desk` | Core case management |
| `incident/problem/change/release_*` | ITIL processes |
| `cmdb` / `network_discovery` | Configuration & discovery |
| `billing` / `marketplace` | Commercial platform |
| `ai_engine` | Classification & copilot |
| `inventory` / `procurement` | Stock & purchasing |
