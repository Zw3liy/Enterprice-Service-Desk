$ErrorActionPreference="Continue"

Write-Host "
=========================================================
PHASE 2.2 TEMPLATE RUNTIME DIAGNOSTIC
=========================================================
"

Write-Host "`n[1] CURRENT AUTHORITY"
git branch --show-current
git log -1 --oneline


Write-Host "`n[2] DJANGO SETTINGS"
python manage.py shell -c "
from django.conf import settings
print('ROOT_URLCONF:', settings.ROOT_URLCONF)
print('TEMPLATES:')
for t in settings.TEMPLATES:
    print(t)
"


Write-Host "`n[3] TEMPLATE LOADER TEST"

python manage.py shell -c "
from django.template.loader import get_template

template='service_desk/dashboard.html'

try:
    t=get_template(template)
    print('SUCCESS')
    print('NAME:',t.origin.name)
except Exception as e:
    print('FAILED')
    print(type(e).__name__)
    print(e)
"


Write-Host "`n[4] DASHBOARD VIEW EXECUTION"

python manage.py shell -c "
from apps.service_desk.views import DashboardView
print(DashboardView.template_name)
"


Write-Host "`n[5] CACHE CLEAN"

Get-ChildItem -Recurse -Directory -Filter __pycache__ |
Remove-Item -Recurse -Force

Write-Host 'Python cache removed'


Write-Host "`n[6] VALIDATION"

python manage.py check

python manage.py test apps.service_desk.tests -v 2