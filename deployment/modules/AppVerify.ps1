<#
=========================================================================
 Enterprise Service Desk
 Stage Module: AppVerify.ps1 (Production v1.2)

 Purpose: Application release verification gate.
 Checks:
   - Django system health
   - Migration status
   - Template integrity
   - Critical route availability (Strict Fail Gate)
   - Deployment readiness report

 Integration: Called by DeploymentEngine.ps1
 Exit: return 0 = success, return 1 = failure
=========================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DeploymentRoot     = Split-Path -Parent $PSScriptRoot
$ProjectRoot        = Split-Path -Parent $DeploymentRoot
$ReportPath         = Join-Path $DeploymentRoot "reports"

if (-not (Test-Path $ReportPath)) { 
    New-Item -ItemType Directory -Path $ReportPath -Force | Out-Null 
}

$script:Results      = @()
$script:FailedChecks = 0

function Add-Verification {
    param (
        [string]$Name,
        [bool]$Passed,
        [string]$Details
    )
    $Status = if ($Passed) { "PASS" } else { "FAIL" }
    Write-Host "$Status | $Name | $Details"
    
    $script:Results += [PSCustomObject]@{
        Check   = $Name
        Status  = $Status
        Details = $Details
    }
    
    if (-not $Passed) {
        $script:FailedChecks++
    }
    return $Passed
}

Write-Host ""
Write-Host "======================================"
Write-Host " Enterprise Service Desk App Verify   "
Write-Host "======================================"
Write-Host ""

try {
    Push-Location $ProjectRoot

    # 1. Django System Check
    $CheckOutput = python manage.py check 2>&1
    Add-Verification -Name "Django System Check" -Passed ($LASTEXITCODE -eq 0) -Details "Django configuration healthy"

    # 2. Migration Check
    $MigrateOutput = python manage.py showmigrations --plan 2>&1
    Add-Verification -Name "Migration Status" -Passed ($LASTEXITCODE -eq 0) -Details "Migration framework available"

    # 3. Template Integrity Check
    $RequiredTemplates = @(
        "templates\base.html",
        "templates\registration\login.html",
        "templates\includes\navbar.html",
        "templates\includes\sidebar.html",
        "templates\includes\form_fields.html"
    )

    foreach ($Template in $RequiredTemplates) {
        $FullPath = Join-Path $ProjectRoot $Template
        Add-Verification -Name "Template $Template" -Passed (Test-Path $FullPath) -Details $FullPath
    }

    # 4. Critical URL Route Smoke Tests
    $Routes = @("/", "/tickets/", "/tickets/new/")
    foreach ($Route in $Routes) {
        try {
            $Response = Invoke-WebRequest -Uri "http://127.0.0.1:8000$Route" -UseBasicParsing -TimeoutSec 5
            Add-Verification -Name "Route $Route" -Passed ($Response.StatusCode -eq 200) -Details "HTTP $($Response.StatusCode)"
        } catch {
            Add-Verification -Name "Route $Route" -Passed $false -Details $_.Exception.Message
        }
    }

    Pop-Location
} catch {
    Write-Host "CRITICAL ERROR DURING VERIFICATION: $_"
    $script:FailedChecks++
}

# Export Report JSON
$ReportFile = Join-Path $ReportPath ("appverify_{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$script:Results | ConvertTo-Json -Depth 5 | Out-File $ReportFile -Encoding UTF8

Write-Host ""
Write-Host "======================================"
if ($script:FailedChecks -gt 0) {
    Write-Host " APPLICATION VERIFICATION FAILED"
    Write-Host " Total Failed Checks: $script:FailedChecks"
    Write-Host " Report: $ReportFile"
    Write-Host "======================================"
    return 1
} else {
    Write-Host " APPLICATION VERIFY PASSED"
    Write-Host " Report: $ReportFile"
    Write-Host "======================================"
    return 0
}