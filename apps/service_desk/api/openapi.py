"""Minimal OpenAPI document for ESD API v1."""

OPENAPI = {
    "openapi": "3.0.3",
    "info": {
        "title": "Enterprise Service Desk API",
        "version": "1.0.0",
        "description": "REST API for tickets, CMDB, knowledge, SLA, and AI assist.",
    },
    "paths": {
        "/api/v1/tickets/": {
            "get": {"summary": "List tickets"},
            "post": {"summary": "Create ticket"},
        },
        "/api/v1/dashboard/": {"get": {"summary": "Dashboard KPIs"}},
        "/api/v1/ai/classify/": {"post": {"summary": "Classify free text"}},
    },
}
