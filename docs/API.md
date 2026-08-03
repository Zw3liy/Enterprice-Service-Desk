# Enterprise Service Desk API

Base URL: `/api/v1/`

## Authentication

- Session cookie (browser)
- Token header: `Authorization: Token <key>`

Create a token:

```python
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
user = get_user_model().objects.get(username="admin")
token, _ = Token.objects.get_or_create(user=user)
print(token.key)
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/` | API index |
| GET | `/api/v1/dashboard/` | KPI summary |
| GET/POST | `/api/v1/tickets/` | List / create tickets |
| GET/PATCH | `/api/v1/tickets/{id}/` | Retrieve / update |
| POST | `/api/v1/tickets/{id}/comments/` | Add comment |
| POST | `/api/v1/tickets/{id}/assign/` | Assign / auto-assign |
| POST | `/api/v1/tickets/{id}/worklogs/` | Add work log |
| GET | `/api/v1/tickets/{id}/recommendations/` | AI KB suggestions |
| GET/POST | `/api/v1/assets/` | CMDB assets |
| GET/POST | `/api/v1/knowledge/` | Knowledge articles |
| GET | `/api/v1/notifications/` | User notifications |
| GET | `/api/v1/audit/` | Audit trail |
| POST | `/api/v1/ai/classify/` | Classify free text |
| GET | `/healthz/` | Liveness |
| GET | `/ready/` | Readiness |

## Create ticket example

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tickets/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "VPN down",
    "description": "Branch offline",
    "ticket_type": "incident",
    "auto_assign": true
  }'
```
