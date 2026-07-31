"""
Django settings for the Enterprise Service Desk platform.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Optional .env loading without hard dependency failure
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    raw = env(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: str = "") -> list[str]:
    raw = env(key, default) or ""
    return [part.strip() for part in raw.split(",") if part.strip()]


SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-change-me-enterprise-service-desk-2026",
)

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,testserver")

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000",
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Third party
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    # Core platform
    "apps.service_desk.apps.ServiceDeskConfig",
    # ITIL & enterprise modules
    "apps.incident_management.apps.IncidentManagementConfig",
    "apps.problem_management.apps.ProblemManagementConfig",
    "apps.change_management.apps.ChangeManagementConfig",
    "apps.cmdb.apps.CMDBConfig",
    "apps.customer_portal.apps.CustomerPortalConfig",
    "apps.billing.apps.BillingConfig",
    "apps.webhooks.apps.WebhooksConfig",
    "apps.mfa.apps.MFAConfig",
    "apps.identity_management.apps.IdentityManagementConfig",
    "apps.ai_engine.apps.AIEngineConfig",
    "apps.release_management.apps.ReleaseManagementConfig",
    "apps.vendor_management.apps.VendorManagementConfig",
    "apps.monitoring_engine.apps.MonitoringEngineConfig",
    "apps.cab_management.apps.CABManagementConfig",
    "apps.network_discovery.apps.NetworkDiscoveryConfig",
    "apps.compliance.apps.ComplianceConfig",
    "apps.chatbot.apps.ChatbotConfig",
    "apps.asset_lifecycle_management.apps.AssetLifecycleManagementConfig",
    "apps.field_service.apps.FieldServiceConfig",
    "apps.soc_center.apps.SOCCenterConfig",
    "apps.vulnerability_management.apps.VulnerabilityManagementConfig",
    "apps.it_financial_management.apps.ITFinancialManagementConfig",
    "apps.scheduled_reports.apps.ScheduledReportsConfig",
    "apps.graphql_api.apps.GraphQLAPIConfig",
    "apps.warranty.apps.WarrantyConfig",
    "apps.marketplace.apps.MarketplaceConfig",
    "apps.pam.apps.PAMConfig",
    "apps.offline_sync.apps.OfflineSyncConfig",
    "apps.document_indexing.apps.DocumentIndexingConfig",
    "apps.form_builder.apps.FormBuilderConfig",
    "apps.event_engine.apps.EventEngineConfig",
    "apps.business_rules.apps.BusinessRulesConfig",
    "apps.forecasting.apps.ForecastingConfig",
    "apps.rbac.apps.RBACConfig",
    "apps.multi_tenant.apps.MultiTenantConfig",
    "apps.analytics_engine.apps.AnalyticsEngineConfig",
    "apps.executive_dashboard.apps.ExecutiveDashboardConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.procurement.apps.ProcurementConfig",
    "apps.integrations.apps.IntegrationsConfig",
    "apps.approval_engine.apps.ApprovalEngineConfig",
    "apps.sla_engine.apps.SLAEngineConfig",
    "apps.escalation_engine.apps.EscalationEngineConfig",
    "apps.assignment_engine.apps.AssignmentEngineConfig",
    "apps.automation.apps.AutomationConfig",
    "apps.service_catalog.apps.ServiceCatalogConfig",
    "apps.knowledge_management.apps.KnowledgeManagementConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.service_desk.middleware.RequestLoggingMiddleware",
    "apps.service_desk.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "ticketing.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.service_desk.context_processors.service_desk_globals",
            ],
        },
    },
]

WSGI_APPLICATION = "ticketing.wsgi.application"
ASGI_APPLICATION = "ticketing.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

_db_engine = env("DATABASE_ENGINE", "django.db.backends.sqlite3")
if _db_engine == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / env("DATABASE_NAME", "db.sqlite3"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": _db_engine,
            "NAME": env("DATABASE_NAME", "esd"),
            "USER": env("DATABASE_USER", "esd"),
            "PASSWORD": env("DATABASE_PASSWORD", "esd"),
            "HOST": env("DATABASE_HOST", "localhost"),
            "PORT": env("DATABASE_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Africa/Johannesburg")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "service_desk:dashboard"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "600/minute",
    },
    "EXCEPTION_HANDLER": "apps.service_desk.api.exceptions.custom_exception_handler",
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "")

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "servicedesk@example.com")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587") or "587")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)

# ---------------------------------------------------------------------------
# Cache / Celery
# ---------------------------------------------------------------------------

REDIS_URL = env("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "esd-local",
        }
    }

CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL or "memory://")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "cache+memory://")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", True)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ---------------------------------------------------------------------------
# Security hardening (production toggles)
# ---------------------------------------------------------------------------

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_AGE = 60 * 60 * 8

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "service_desk.log"),
            "maxBytes": 5_000_000,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps.service_desk": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# Platform defaults
ESD_DEFAULT_COMPANY_SLUG = env("DEFAULT_COMPANY_SLUG", "default")
ESD_DEFAULT_COMPANY_NAME = env("DEFAULT_COMPANY_NAME", "Default Organization")
ESD_TICKETS_PER_PAGE = 25
ESD_MAX_ATTACHMENT_MB = 25

# Inbound email (IMAP)
EMAIL_IMAP_HOST = env("EMAIL_IMAP_HOST", "")
EMAIL_IMAP_USER = env("EMAIL_IMAP_USER", "")
EMAIL_IMAP_PASSWORD = env("EMAIL_IMAP_PASSWORD", "")
EMAIL_IMAP_MAILBOX = env("EMAIL_IMAP_MAILBOX", "INBOX")

# AI providers
OPENAI_API_KEY = env("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
AI_DEFAULT_PROVIDER = env("AI_DEFAULT_PROVIDER", "local")

# Upload limits (25 MB default; override via ESD_MAX_ATTACHMENT_MB)
_ESD_MAX_MB = int(env("ESD_MAX_ATTACHMENT_MB", "25") or "25")
DATA_UPLOAD_MAX_MEMORY_SIZE = _ESD_MAX_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = _ESD_MAX_MB * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
