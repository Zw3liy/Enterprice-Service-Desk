# Roadmap

## v1.0.0 (Production)
- [x] Core ticketing + ITIL (incident/problem/change/release)
- [x] CMDB + discovery + monitoring ingest
- [x] Portal, executive dashboard, form builder, chatbot
- [x] MFA, SSO helpers, RBAC, PAM, compliance, SOC
- [x] Billing, multi-tenant metadata, marketplace
- [x] Inventory + procurement
- [x] Analytics, forecasting, scheduled reports
- [x] AI copilot, GraphQL-compatible API, offline sync
- [ ] Host verification: Docker + Postgres + Redis + Celery worker (requires infra)
- [ ] Coverage ≥ 90% overall

## v1.1
- Full Graphene/Strawberry GraphQL schema
- Live LDAP bind connector UI
- Inbound email worker scheduling (django-celery-beat)
- Mobile PWA offline client packaging
- Advanced SIEM shippers (Splunk HEC, Elastic)

## v1.2
- Multi-region tenancy
- Advanced CMDB topology visualization
- ML-based priority models with training pipeline
