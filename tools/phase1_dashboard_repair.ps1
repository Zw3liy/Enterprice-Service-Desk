$ErrorActionPreference = "Stop"

Write-Host "
=================================================
PHASE 1 DASHBOARD TEMPLATE STABILIZATION
AUTOMATED ANALYSIS + REPAIR ENGINE
=================================================
"

$ViewFile = "apps\service_desk\views.py"

if (!(Test-Path $ViewFile)) {
    Write-Host "ERROR: views.py not found"
    exit 1
}

Write-Host "`n[1] Detecting dashboard render calls..."

$dashboardRefs = Select-String `
    -Path $ViewFile `
    -Pattern "render\(.*dashboard|dashboard\.html|get_template"

$dashboardRefs


Write-Host "`n[2] Searching templates..."

$templates = Get-ChildItem `
    -Recurse `
    -Filter "*.html" `
    -Path templates,apps `
    -ErrorAction SilentlyContinue


$templates | 
Select-Object FullName,Length |
Format-Table


Write-Host "`n[3] Detecting dashboard templates..."

$dashboardTemplates =
$templates | Where-Object {
    $_.Name -match "dashboard"
}


if ($dashboardTemplates) {

    Write-Host "
FOUND EXISTING DASHBOARD TEMPLATE
Architecture rule:
DO NOT CREATE DUPLICATE TEMPLATE
"

    $dashboardTemplates |
    Select FullName,Length

}
else {

    Write-Host "
NO DASHBOARD TEMPLATE FOUND
Template creation required.
"
}


Write-Host "`n[4] Extracting dashboard context..."

Select-String `
-Path $ViewFile `
-Pattern "def dashboard" `
-Context 0,80


Write-Host "`n[5] Running Django validation..."

python manage.py check


Write-Host "`n[6] Checking migrations..."

python manage.py makemigrations --check --dry-run


Write-Host "
=================================================
DISCOVERY COMPLETE
=================================================
"