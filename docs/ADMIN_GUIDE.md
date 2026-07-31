# Administrator Guide

## First login
1. Run `bootstrap_esd`.
2. Sign in as `admin` and change the password.
3. Enable MFA at `/mfa/setup/`.

## Django admin
`/admin/` manages all domain models (tickets, CMDB, billing, inventory, etc.).

## Tenants
- Companies are tenants.
- Domains & feature flags: `/tenants/api/` or admin `TenantDomain` / `TenantSettings`.
- Provision: `POST /tenants/api/provision/` (staff).

## RBAC
- Bootstrap roles: `POST /rbac/api/bootstrap/`
- Assign: `POST /rbac/api/assign/` with `user_id`, `role_code`
- Current user: `GET /rbac/api/me/`

## SLA & automation
- Define SLA records and escalation policies in admin.
- Run `python manage.py scan_sla` on a schedule (cron/Celery).
- Automation rules: admin `AutomationRule` (trigger + JSON actions).

## Integrations
- Registry UI/API: `/integrations/api/connections/`
- Providers: email IMAP, LDAP, M365, Slack, Teams, SMS
- Test: `POST .../connections/{id}/test/`

## Billing
- `/billing/` dashboard, plans, invoices, usage snapshot.

## Marketplace
- Seed catalog via bootstrap or `MarketplaceService.seed_catalog()`.
- Install apps with config (creates webhook endpoints when applicable).

## Inventory & procurement
- Warehouses/items/movements under `/inventory/api/`
- Purchase requests/orders under `/procurement/api/`
- Receiving a PO can create stock receipts.

## Security operations
- SOC: `/soc/api/`
- Vulnerabilities: `/vulns/api/`
- SIEM export: `/api/security/siem/export/?format=json|cef`
- PAM: `/pam/api/`

## Reports
- Executive UI: `/executive/`
- Analytics API: `/analytics/api/`
- Scheduled reports: `/reports-engine/api/` + `run_due_reports` command
