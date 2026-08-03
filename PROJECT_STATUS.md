# Enterprise Service Desk — Project Status

**Version:** 1.0.0-rc.1  
**Last updated:** 2026-07-31  
**Branch:** `arena/019fb8f0-enterprice-service-desk`

### Batch metrics (latest)
| Metric | Value |
|--------|------:|
| Installed ESD apps | 48 |
| ORM models | 105 |
| Test count (broad suite) | 78+ |
| `manage.py check` | clean |
| Docs set | README, STATUS, CHANGELOG, ROADMAP, CONTRIBUTING, SECURITY, LICENSE, architecture/deploy/admin/user/backup |

## Release readiness

| Criterion | Status |
|-----------|--------|
| Django system check | Pass |
| Migrations apply / `--check` clean | Pass |
| Unit/integration test suite | Pass (expanding) |
| collectstatic | Pass |
| SQLite local runtime | Pass |
| PostgreSQL / Redis / Docker runtime | Environment-dependent |
| CI workflows present | Yes (`.github/workflows/`) |

## Completed modules (installed runtime)

### Core ITSM
- `service_desk` — tickets, SLA, queues, automation, notifications, audit, REST API, UI
- `incident_management` — major incidents, timeline
- `problem_management` — problem records, RCA, known errors
- `change_management` — RFC, CAB approvals, meetings
- `release_management` — releases + tasks
- `cab_management` — CAB facade over change management
- `cmdb` — CI classes, CIs, relationships, discovery ingest
- `asset_lifecycle_management` — lifecycle transitions
- `knowledge_management` / knowledge UI in service_desk
- `service_catalog` — catalog over request types
- `sla_engine` / `escalation_engine` / `assignment_engine` / `automation` / `approval_engine`

### Portals & experience
- `customer_portal` — self-service portal
- `executive_dashboard` — board pack KPIs
- `form_builder` — dynamic forms → tickets
- `chatbot` — intent + copilot

### Security & identity
- `mfa` — TOTP + backup codes
- `identity_management` — OAuth/SAML SSO helpers
- `rbac` — roles, assignments, groups
- `pam` — privileged access requests/sessions
- `compliance` — ISO27001-style controls
- `soc_center` — security incidents + playbooks
- `webhooks` — outbound signed webhooks

### Operations & assets
- `monitoring_engine` — alert ingest → incidents
- `network_discovery` — scan jobs + CMDB sync
- `vulnerability_management` — CVE findings
- `vendor_management` / `warranty`
- `inventory` — warehouses, stock, movements
- `procurement` — PR/PO → inventory receipt
- `field_service` — work orders

### Platform / data / AI
- `billing` — plans, subscriptions, invoices, usage
- `marketplace` — integration catalog installs
- `multi_tenant` — domains, settings, provision
- `integrations` — connection registry + email/LDAP/M365
- `analytics_engine` — snapshots, KPI/SLA/agent reports, export
- `forecasting` — volume + staffing
- `scheduled_reports`
- `document_indexing` / `offline_sync`
- `event_engine` / `business_rules`
- `ai_engine` / `graphql_api`
- `it_financial_management` — cost centers, budgets, chargeback

## Modules in progress
- Deep LDAP live bind (connector data model + sync ready; directory bind is config-driven)
- Live Redis/Celery worker + Postgres compose validation on hosts with Docker

## Remaining (scaffold dirs not yet first-class runtime apps)
Many historical empty trees under `apps/*` remain as architectural placeholders (e.g. advanced SIEM connectors, full mobile PWA offline client). Prefer promoting them only when vertical slices are needed.

## Quality metrics (latest local run)

| Metric | Value |
|--------|------:|
| Installed ESD apps | 48+ (including facades) |
| Models (approx.) | 100+ |
| Test count (ESD suite) | 64+ and growing |
| Coverage (`apps/`) | ~74% baseline |

## Migration status
All installed apps with models have initial migrations applied.  
`makemigrations --check` reports no pending model changes.

## Known issues
1. Docker/Redis/Postgres not available in some CI sandboxes — app falls back to SQLite + LocMem + eager Celery.
2. Some historical empty files remain under **non-installed** `apps/*` directories from phase scaffolding.
3. GraphQL is a constrained JSON GraphQL-compatible executor (not full Graphene schema).

## Resolved issues
- Broken/empty service desk core replaced with working domain + API + UI
- Migration history reset to coherent enterprise domain for `service_desk`
- Duplicate URL namespaces cleaned for ITIL/API gateways
- Webhook + domain event side-effects on ticket create

## Default credentials (bootstrap)
```bash
python manage.py migrate
python manage.py bootstrap_esd --with-demo
# admin / admin123!
```
