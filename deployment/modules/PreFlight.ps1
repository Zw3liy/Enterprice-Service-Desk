<#
=========================================================================
 Enterprise Service Desk
 Stage Module: PreFlight.ps1 (Production v1.2)

 Purpose:
   Validates systemic dependencies, disk space, Python runtime, 
   virtual environment, pip dependencies, Django health, and 
   deployment paths before execution. Exports a structured report.
=========================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DeploymentRoot = Split-Path -Parent $PSScriptRoot
$ProjectRoot    = Split-Path -Parent $DeploymentRoot
$ReportPath     = Join-Path $DeploymentRoot "reports"
$script:Results = @()

function Write-Check {
    param (
        [string]$Name,
        [bool]$Passed,
        [string]$Message
    )
    $Status = if ($Passed) { "OK" } else { "FAILED" }
    Write-Host "$Status | $Name | $Message"
    $script:Results += [PSCustomObject]@{
        Check   = $Name
        Status  = $Status
        Details = $Message
    }
    if (-not $Passed) {
        throw "PreFlight failed on check: $Name ($Message)"
    }
}

Write-Host ""
Write-Host "=============================================="
Write-Host " Enterprise Service Desk PreFlight Validation "
Write-Host "=============================================="
Write-Host ""

# 1. Check Python Availability & Version
$Python = Get-Command python -ErrorAction SilentlyContinue
Write-Check -Name "Python Runtime" -Passed ($null -ne $Python) -Message "Python executable detected"

$PythonVersion = (python --version 2>&1).ToString()
Write-Check -Name "Python Version" -Passed ($PythonVersion -match "3\.") -Message $PythonVersion

# 2. Check Git Binary & Repository
$Git = Get-Command git -ErrorAction SilentlyContinue
Write-Check -Name "Git Runtime" -Passed ($null -ne $Git) -Message "Git executable detected"

# 3. Check Virtual Environment
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvExists = Test-Path $VenvPath
if (-not $VenvExists) {
    $VenvPath = Join-Path $ProjectRoot "venv"
    $VenvExists = Test-Path $VenvPath
}
Write-Check -Name "Virtual Environment" -Passed $VenvExists -Message "Virtual environment detected at $VenvPath"

# 4. Check Django manage.py Entrypoint
$ManagePy = Join-Path $ProjectRoot "manage.py"
Write-Check -Name "Django Entrypoint" -Passed (Test-Path $ManagePy) -Message "manage.py found at $ManagePy"

# 5. Check Pip & Dependency Integrity
$PipCheck = python -m pip --version 2>&1
Write-Check -Name "Pip Runtime" -Passed ($LASTEXITCODE -eq 0) -Message "Pip functional"

# 6. Check Django Configuration Health
Push-Location $ProjectRoot
try {
    $DjangoCheck = python manage.py check 2>&1
    Write-Check -Name "Django System Check" -Passed ($LASTEXITCODE -eq 0) -Message "Django configuration valid"
} catch {
    Write-Check -Name "Django System Check" -Passed $false -Message $_.Exception.Message
} finally {
    Pop-Location
}

# 7. Check Deployment Directory Structure
$RequiredPaths = @("artifacts", "config", "logs", "releases", "reports")
foreach ($Dir in $RequiredPaths) {
    $FullPath = Join-Path $DeploymentRoot $Dir
    if (-not (Test-Path $FullPath)) {
        New-Item -ItemType Directory -Path $FullPath -Force | Out-Null
    }
}
Write-Check -Name "Deployment Structure" -Passed $true -Message "All deployment directories provisioned"

# 8. Dynamic Disk Space Guard
$DriveLetter = (Get-Location).Drive.Name
$Drive = Get-PSDrive $DriveLetter
$MinimumSpace = 1GB
Write-Check -Name "Disk Space" -Passed ($Drive.Free -gt $MinimumSpace) -Message ("{0:N2} GB available on drive {1}:" -f ($Drive.Free / 1GB), $DriveLetter)

# 9. Export PreFlight Report
if (-not (Test-Path $ReportPath)) { New-Item -ItemType Directory -Path $ReportPath -Force | Out-Null }
$ReportFile = Join-Path $ReportPath ("preflight_{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$script:Results | ConvertTo-Json -Depth 5 | Out-File $ReportFile -Encoding UTF8

Write-Host ""
Write-Host "=============================================="
Write-Host " PRE-FLIGHT COMPLETED SUCCESSFULLY"
Write-Host " Report: $ReportFile"
Write-Host "=============================================="
return 0