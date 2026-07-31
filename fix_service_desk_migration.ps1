# ==========================================================
# Enterprise Service Desk Migration Repair Script
# Converts old ticketing app references to service_desk
# ==========================================================

Write-Host ""
Write-Host "=============================================="
Write-Host " Service Desk Migration Repair"
Write-Host "=============================================="
Write-Host ""

$migration = ".\apps\service_desk\migrations\0002_enterprise_domain_model.py"


# Check migration exists
if (!(Test-Path $migration)) {

    Write-Host "ERROR: Migration file not found:"
    Write-Host $migration
    exit 1

}


Write-Host "[+] Backup migration file"

Copy-Item `
    $migration `
    "$migration.backup" `
    -Force


Write-Host "[+] Updating app namespace..."

$content = Get-Content $migration -Raw


# Replace old Django app name
$content = $content.Replace(
    '"ticketing"',
    '"service_desk"'
)


$content = $content.Replace(
    'to="ticketing.',
    'to="service_desk.'
)


$content = $content.Replace(
    'apps.get_model("ticketing"',
    'apps.get_model("service_desk"'
)


Set-Content `
    $migration `
    $content `
    -Encoding UTF8


Write-Host ""
Write-Host "[+] Migration repair completed"
Write-Host ""

Write-Host "Checking remaining ticketing references..."

Select-String `
    -Path $migration `
    -Pattern "ticketing"


Write-Host ""
Write-Host "=============================================="
Write-Host " Finished"
Write-Host " Backup created:"
Write-Host "$migration.backup"
Write-Host "=============================================="