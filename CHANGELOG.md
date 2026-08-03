# Changelog

All notable changes to Enterprise Service Desk are documented in this file.

## [1.0.0-rc.1] — 2026-07-31

### Added
- Full service desk core: tickets, SLA, automation, notifications, audit, REST API, technician UI
- ITIL: incidents (major + timeline), problems, changes/CAB, releases
- CMDB CIs, discovery ingest, network discovery scans
- Customer portal, executive dashboard, form builder, chatbot
- Security: MFA, SSO helpers, RBAC, PAM, compliance controls, SOC playbooks
- Inventory + procurement (PR/PO receive into stock)
- Billing, marketplace installs, multi-tenant domains/settings
- Integrations connection registry (email/LDAP/M365/Slack/Teams)
- Analytics engine snapshots + exports; forecasting; scheduled reports
- AI engine copilot; GraphQL-compatible API; document index; offline sync
- Event bus + business rules engine
- Project status, API docs, Docker/compose/nginx/k8s manifests, CI workflows

### Security
- CSRF/session auth for UI; token auth for APIs
- Webhook HMAC signatures
- Secrets via environment (`.env.example`)

### Fixed
- Empty phase-scaffold runtime path replaced with working modules
- Migration integrity for installed apps
- URL namespace collisions on API gateway includes

## [0.1.0] — 2026-07-30

### Added
- Initial Django project scaffold and phase directory generators
