<#
=========================================================
 Enterprise Service Desk
 Automated Test Engine

 Module:
 deployment\modules\Test.ps1

 Command:
 .\Deploy.ps1 test
=========================================================
#>

$RootPath = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))

$DeploymentPath = Join-Path $RootPath "deployment"
$LogPath = Join-Path $DeploymentPath "logs"
$ReportPath = Join-Path $DeploymentPath "reports"

foreach ($dir in @($LogPath, $ReportPath)) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
}

$LogFile = Join-Path $LogPath ("test_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

$script:TestResults = @()

function Write-TestLog {

    param([string]$Message)

    $Entry = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message

    Write-Host $Entry

    Add-Content -Path $LogFile -Value $Entry
}

function Add-TestResult {

    param(

        [string]$Task,

        [ValidateSet("OK","FAILED","WARNING","SKIPPED")]
        [string]$Status,

        [string]$Details

    )

    $script:TestResults += [PSCustomObject]@{

        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

        Task = $Task

        Status = $Status

        Details = $Details

    }

    Write-TestLog "$Status | $Task | $Details"
}

Write-Host @"

========================================
 Enterprise Service Desk
 Automated Test Engine
========================================

"@

#
# Python
#

try {

    python --version | Out-Null

    Add-TestResult "Python" "OK" "Python detected"

}
catch {

    Add-TestResult "Python" "FAILED" "Python not installed"

}

#
# manage.py
#

$Manage = Join-Path $RootPath "manage.py"

if (!(Test-Path $Manage)) {

    Add-TestResult "manage.py" "FAILED" "manage.py missing"

}
else {

    Add-TestResult "manage.py" "OK" "manage.py found"

}

#
# Django check
#

if (Test-Path $Manage) {

    try {

        python manage.py check

        if ($LASTEXITCODE -eq 0) {

            Add-TestResult "Django Check" "OK" "System check passed"

        }
        else {

            Add-TestResult "Django Check" "FAILED" "System check failed"

        }

    }
    catch {

        Add-TestResult "Django Check" "FAILED" $_.Exception.Message

    }

}

#
# Migration check
#

if (Test-Path $Manage) {

    try {

        python manage.py makemigrations --check --dry-run

        if ($LASTEXITCODE -eq 0) {

            Add-TestResult "Migration Check" "OK" "No pending migrations"

        }
        else {

            Add-TestResult "Migration Check" "WARNING" "Pending migrations"

        }

    }
    catch {

        Add-TestResult "Migration Check" "FAILED" $_.Exception.Message

    }

}

#
# Django tests
#

if (Test-Path $Manage) {

    try {

        python manage.py test

        if ($LASTEXITCODE -eq 0) {

            Add-TestResult "Unit Tests" "OK" "All tests passed"

        }
        else {

            Add-TestResult "Unit Tests" "FAILED" "One or more tests failed"

        }

    }
    catch {

        Add-TestResult "Unit Tests" "FAILED" $_.Exception.Message

    }

}

#
# Staticfiles
#

$Static = Join-Path $RootPath "staticfiles"

if (Test-Path $Static) {

    Add-TestResult "Static Files" "OK" "staticfiles directory exists"

}
else {

    Add-TestResult "Static Files" "WARNING" "staticfiles directory missing"

}

#
# Report
#

$ReportFile = Join-Path $ReportPath "test_report.json"

$script:TestResults |
ConvertTo-Json -Depth 5 |
Set-Content $ReportFile

$Passed = ($script:TestResults | Where-Object Status -eq "OK").Count
$Failed = ($script:TestResults | Where-Object Status -eq "FAILED").Count
$Warnings = ($script:TestResults | Where-Object Status -eq "WARNING").Count

Write-Host @"

========================================

TEST SUMMARY

Passed : $Passed

Failed : $Failed

Warnings : $Warnings

Report :

$ReportFile

========================================

"@

if ($Failed -gt 0) {

    exit 1

}

exit 0