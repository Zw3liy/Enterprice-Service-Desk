<#
=========================================================================
 Enterprise Service Desk
 Stage Module: PreFlight.ps1

 Purpose:
   Validates systemic dependencies, disk space, and runtime environments
   before initiating build/deployment phases.
=========================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Running Pre-Flight Environment Checks..."

# 1. Check Python Availability
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "PreFlight Check Failed: Python execution engine is not installed or not in PATH."
}

# 2. Check Git Availability
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "PreFlight Check Failed: Git binary not detected."
}

# 3. Check Disk Space Threshold (Minimum 1 GB free)
$Drive = Get-PSDrive C
if ($Drive.Free -lt 1GB) {
    throw ("PreFlight Check Failed: Insufficient disk space on drive C:. Available: {0:N2} MB" -f ($Drive.Free / 1MB))
}

Write-Host "OK | Pre-Flight checks passed successfully."
exit 0