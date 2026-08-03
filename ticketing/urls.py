"""Root URL configuration for Enterprise Service Desk."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.service_desk.views import (
    ServiceDeskLoginView,
    ServiceDeskLogoutView,
    healthz,
    readiness,
    register,
)

admin.site.site_header = "Enterprise Service Desk Administration"
admin.site.site_title = "ESD Admin"
admin.site.index_title = "Platform control plane"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", ServiceDeskLoginView.as_view(), name="login"),
    path("logout/", ServiceDeskLogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),
    path("healthz/", healthz, name="healthz"),
    path("ready/", readiness, name="readiness"),
    # Core service desk
    path("", include(("apps.service_desk.urls", "service_desk"), namespace="service_desk")),
    path(
        "ticketing/",
        include(("apps.service_desk.urls", "service_desk"), namespace="ticketing"),
    ),
    # ITIL
    path("incidents/", include("apps.incident_management.urls")),
    path("problems/", include("apps.problem_management.urls")),
    path("changes/", include("apps.change_management.urls")),
    path("cmdb/", include("apps.cmdb.urls")),
    # Portal / billing / security
    path("portal/", include("apps.customer_portal.urls")),
    path("billing/", include("apps.billing.urls")),
    path("webhooks/", include("apps.webhooks.urls")),
    path("mfa/", include("apps.mfa.urls")),
    path("identity/", include("apps.identity_management.urls")),
    path("ai/", include("apps.ai_engine.urls")),
    path("releases/", include("apps.release_management.urls")),
    path("vendors/", include("apps.vendor_management.urls")),
    path("monitoring/", include("apps.monitoring_engine.urls")),
    path("discovery/", include("apps.network_discovery.urls")),
    path("compliance/", include("apps.compliance.urls")),
    path("chatbot/", include("apps.chatbot.urls")),
    path("field/", include("apps.field_service.urls")),
    path("soc/", include("apps.soc_center.urls")),
    path("vulns/", include("apps.vulnerability_management.urls")),
    path("finance/", include("apps.it_financial_management.urls")),
    path("reports-engine/", include("apps.scheduled_reports.urls")),
    path("graphql/", include("apps.graphql_api.urls")),
    path("warranty/", include("apps.warranty.urls")),
    path("marketplace/", include("apps.marketplace.urls")),
    path("pam/", include("apps.pam.urls")),
    path("sync/", include("apps.offline_sync.urls")),
    path("search/", include("apps.document_indexing.urls")),
    path("forms/", include("apps.form_builder.urls")),
    path("events/", include("apps.event_engine.urls")),
    path("rules/", include("apps.business_rules.urls")),
    path("forecast/", include("apps.forecasting.urls")),
    path("rbac/", include("apps.rbac.urls")),
    path("tenants/", include("apps.multi_tenant.urls")),
    path("analytics/", include("apps.analytics_engine.urls")),
    path("executive/", include("apps.executive_dashboard.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("procurement/", include("apps.procurement.urls")),
    path("integrations/", include("apps.integrations.urls")),
    path("approvals/", include("apps.approval_engine.urls")),
    # Top-level API gateways (module mirrors)
    path("api/itil/", include("api.itil.urls")),
    path("api/cmdb/", include("api.cmdb.urls")),
    path("api/knowledge/", include("api.knowledge.urls")),
    path("api/workflow/", include("api.workflow.urls")),
    path("api/security/", include("api.security.urls")),
    path("api/tenant/", include("api.tenant.urls")),
    path("api/analytics/", include("api.analytics.urls")),
    path("api/mobile/", include("api.mobile.urls")),
    path("api/ai/", include("api.ai.urls")),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
