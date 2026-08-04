<#
=========================================================================
 Enterprise Service Desk
 Stage Module: Build.ps1 (Production v1.0)

 Purpose: Creates production build metadata and static assets.
 Actions:
   - Git metadata capture
   - Django collectstatic
   - Build manifest generation

 Exit: return 0 success, return 1 failure
=========================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$DeploymentRoot = Split-Path -Parent $PSScriptRoot
$ProjectRoot    = Split-Path -Parent $DeploymentRoot
$ArtifactPath   = Join-Path $DeploymentRoot "artifacts"

if (-not (Test-Path $ArtifactPath)) { 
    New-Item -ItemType Directory -Path $ArtifactPath -Force | Out-Null 
}

Write-Host ""
Write-Host "======================================"
Write-Host " Enterprise Service Desk Build        "
Write-Host "======================================"
Write-Host ""

try {
    Push-Location $ProjectRoot

    # 1. Git Metadata
    $GitCommit = git rev-parse HEAD 2>$null
    $GitBranch = git branch --show-current 2>$null
    Write-Host "Git Commit: $GitCommit"
    Write-Host "Git Branch: $GitBranch"

    # 2. Collect Static Assets
    python manage.py collectstatic --noinput
    if ($LASTEXITCODE -ne 0) { throw "collectstatic failed" }
    Write-Host "Static collection completed"

    # 3. Build Manifest
    $BuildInfo = [PSCustomObject]@{
        Application   = "Enterprise Service Desk"
        Version       = "1.0.0"
        BuildTime     = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        GitCommit     = $GitCommit
        GitBranch     = $GitBranch
        PythonVersion = (python --version 2>&1).ToString()
        Machine       = $env:COMPUTERNAME
    }

    $BuildFile = Join-Path $ArtifactPath "build-info.json"
    $BuildInfo | ConvertTo-Json -Depth 5 | Out-File $BuildFile -Encoding UTF8
    Write-Host ""
    Write-Host "Build artifact created: $BuildFile"
    Pop-Location
} catch {
    Write-Host ""
    Write-Host "BUILD FAILED"
    Write-Host $_
    return 1
}

Write-Host ""
Write-Host "BUILD COMPLETED SUCCESSFULLY"
return 0