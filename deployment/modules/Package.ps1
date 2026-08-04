<#
=========================================================================
 Enterprise Service Desk
 Production Package Engine

 Module:
 deployment\modules\Package.ps1
=========================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:EngineName    = "Enterprise Service Desk Package Engine"
$script:EngineVersion = "1.1.0"
$script:ExitCode      = 0
$script:StartTime     = Get-Date

$ScriptPath     = $MyInvocation.MyCommand.Path
$ModulePath     = Split-Path -Parent $ScriptPath
$DeploymentPath = Split-Path -Parent $ModulePath
$RootPath       = Split-Path -Parent $DeploymentPath

$ArtifactPath = Join-Path $DeploymentPath "artifacts"
$ReleasePath  = Join-Path $DeploymentPath "releases"
$ReportPath   = Join-Path $DeploymentPath "reports"
$LogPath      = Join-Path $DeploymentPath "logs"

$script:TimeStamp        = Get-Date -Format "yyyyMMdd_HHmmss"
$script:PackageLog      = Join-Path $LogPath "package_$($script:TimeStamp).log"
$script:PackageReportFile = Join-Path $ReportPath "package_report_$($script:TimeStamp).json"

foreach ($Dir in @($ArtifactPath, $ReleasePath, $ReportPath, $LogPath)) {
    if (-not (Test-Path $Dir)) { New-Item -ItemType Directory -Path $Dir -Force | Out-Null }
}
if (-not (Test-Path $script:PackageLog)) { New-Item -ItemType File -Path $script:PackageLog -Force | Out-Null }

$script:PackageResults   = @()
$script:BuildInformation  = $null
$script:PackageVersion    = $null
$script:PackageName       = $null
$script:PackageFile       = $null
$script:PackageHash       = $null
$script:ReleaseFolder     = $null
$script:BuildInfoFile     = $null
$script:ManifestFile      = $null
$script:ChecksumFile      = $null

function Write-PackageLog {
    param ([string]$Message = "")
    if ([string]::IsNullOrWhiteSpace($Message)) {
        Write-Host ""
        Add-Content -Path $script:PackageLog -Value ""
        return
    }
    $Entry = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $Entry
    Add-Content -Path $script:PackageLog -Value $Entry
}

function Add-PackageResult {
    param ([string]$Task, [string]$Status, [string]$Details)
    $Result = [PSCustomObject]@{
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Task      = $Task
        Status    = $Status
        Details   = $Details
    }
    $script:PackageResults += $Result
    Write-PackageLog "$Status | $Task | $Details"
}

function Test-RequiredFile {
    param ([string]$Path, [string]$Description)
    if (Test-Path $Path) {
        $Item = Get-Item $Path
        Add-PackageResult -Task $Description -Status "OK" -Details ("{0} ({1:N2} KB)" -f $Item.Name, ($Item.Length / 1KB))
        return $true
    }
    Add-PackageResult -Task $Description -Status "FAILED" -Details "Missing file: $Path"
    return $false
}

function Export-PackageJson {
    param ([object]$Object, [string]$OutputFile)
    $Dir = Split-Path $OutputFile -Parent
    if (-not (Test-Path $Dir)) { New-Item -ItemType Directory -Path $Dir -Force | Out-Null }
    $Json = $Object | ConvertTo-Json -Depth 30
    [System.IO.File]::WriteAllText($OutputFile, $Json, [System.Text.UTF8Encoding]::new($false))
    Add-PackageResult -Task "JSON Export" -Status "OK" -Details (Split-Path $OutputFile -Leaf)
}

function Import-BuildInformation {
    param ([string]$BuildInfoFile)
    if (-not (Test-Path $BuildInfoFile)) { throw "build_info.json not found." }
    $script:BuildInformation = Get-Content -Path $BuildInfoFile -Raw | ConvertFrom-Json
    if ($null -eq $script:BuildInformation) { throw "build_info.json could not be parsed." }
    
    $script:PackageVersion = $script:BuildInformation.Version
    $script:PackageName    = "EnterpriseServiceDesk-v$($script:PackageVersion).zip"
    $script:PackageFile    = Join-Path $ArtifactPath $script:PackageName
    $script:ReleaseFolder  = Join-Path $ReleasePath ("EnterpriseServiceDesk-{0}-{1}" -f $script:PackageVersion, $script:TimeStamp)
    Add-PackageResult -Task "Build Information" -Status "OK" -Details ("Version {0}" -f $script:PackageVersion)
}

function Test-BuildArtifacts {
    Write-PackageLog "Validating build artifacts..."
    $script:BuildInfoFile = Join-Path $ArtifactPath "build_info.json"
    $script:ManifestFile  = Join-Path $ArtifactPath "manifest.json"
    $script:ChecksumFile  = Join-Path $ArtifactPath "SHA256SUMS"

    $Valid = $true
    if (-not (Test-RequiredFile -Path $script:BuildInfoFile -Description "Build Information")) { $Valid = $false }
    if (-not (Test-RequiredFile -Path $script:ManifestFile  -Description "Build Manifest"))     { $Valid = $false }
    if (-not (Test-RequiredFile -Path $script:ChecksumFile  -Description "SHA256 Checksums"))   { $Valid = $false }

    Import-BuildInformation -BuildInfoFile $script:BuildInfoFile

    if (-not (Test-RequiredFile -Path $script:PackageFile -Description "Deployment Package Archive")) { $Valid = $false }
    if (-not $Valid) { throw "Missing required build artifacts." }
}

function Test-BuildMetadata {
    Write-PackageLog "Validating build metadata..."
    $Required = @("Application", "Version", "BuildDate")
    foreach ($Property in $Required) {
        if (-not ($script:BuildInformation.PSObject.Properties.Name -contains $Property)) {
            throw "Missing build metadata property: $Property"
        }
    }
    Add-PackageResult -Task "Build Metadata Schema" -Status "OK" -Details "Schema validated"
}

function Test-Manifest {
    Write-PackageLog "Validating manifest..."
    $Manifest = Get-Content $script:ManifestFile -Raw | ConvertFrom-Json
    foreach ($Property in @("Application", "Version", "Files")) {
        if (-not ($Manifest.PSObject.Properties.Name -contains $Property)) {
            throw "Manifest missing $Property"
        }
    }
    if ($Manifest.Files.Count -eq 0) { throw "Manifest contains no files" }
    Add-PackageResult -Task "Manifest Validation" -Status "OK" -Details ("{0} files validated" -f $Manifest.Files.Count)
}

function Test-PackageSize {
    Write-PackageLog "Checking package size guard..."
    $Package = Get-Item $script:PackageFile
    if ($Package.Length -lt 10240) { throw "Package size below minimum threshold (10KB)" }
    Add-PackageResult -Task "Package Size" -Status "OK" -Details ("{0:N2} MB" -f ($Package.Length / 1MB))
}

function Test-PackageChecksum {
    Write-PackageLog "Verifying SHA256 checksum..."
    $ChecksumLine = (Get-Content $script:ChecksumFile | Where-Object { $_.Trim() -ne "" } | Select-Object -First 1).Trim()
    $ExpectedHash   = ($ChecksumLine -split '\s+')[0].Trim().ToUpper()
    $CalculatedHash = (Get-FileHash -Path $script:PackageFile -Algorithm SHA256).Hash.ToUpper()

    if ($ExpectedHash -ne $CalculatedHash) { throw "Checksum mismatch!" }
    $script:PackageHash = $CalculatedHash
    Add-PackageResult -Task "SHA256 Validation" -Status "OK" -Details $CalculatedHash
}

function Test-PackageArchive {
    Write-PackageLog "Verifying ZIP entry stream integrity..."
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Archive = $null
    try {
        $Archive = [System.IO.Compression.ZipFile]::OpenRead($script:PackageFile)
        $Entries = @($Archive.Entries)
        if ($Entries.Count -eq 0) { throw "ZIP archive contains no entries." }
        foreach ($Entry in $Entries) {
            if ([string]::IsNullOrWhiteSpace($Entry.FullName)) { throw "Invalid ZIP entry detected." }
            $Stream = $null
            try {
                $Stream = $Entry.Open()
                $Buffer = New-Object byte[] 4096
                while ($Stream.Read($Buffer, 0, $Buffer.Length) -gt 0) {
                    # Stream traversal validation
                }
            } finally {
                if ($null -ne $Stream) { $Stream.Dispose() }
            }
        }
        Add-PackageResult -Task "ZIP Integrity" -Status "OK" -Details ("{0} ZIP entries verified" -f $Entries.Count)
    } catch {
        Add-PackageResult -Task "ZIP Integrity" -Status "FAILED" -Details $_.Exception.Message
        throw
    } finally {
        if ($null -ne $Archive) { $Archive.Dispose() }
    }
}

function New-ReleaseDirectory {
    Write-PackageLog "Creating release folder..."
    if (-not (Test-Path $script:ReleaseFolder)) { New-Item -ItemType Directory -Path $script:ReleaseFolder -Force | Out-Null }
    Add-PackageResult -Task "Release Folder" -Status "OK" -Details $script:ReleaseFolder
}

function Copy-ReleaseArtifacts {
    Write-PackageLog "Copying artifacts..."
    foreach ($File in @($script:PackageFile, $script:BuildInfoFile, $script:ManifestFile, $script:ChecksumFile)) {
        Copy-Item -Path $File -Destination $script:ReleaseFolder -Force
        Add-PackageResult -Task "Copy Artifact" -Status "OK" -Details (Split-Path $File -Leaf)
    }
}

function New-ReleaseMetadata {
    Write-PackageLog "Generating release metadata..."
    try {
        $Metadata = [PSCustomObject]@{
            Engine        = $script:EngineName
            EngineVersion = $script:EngineVersion
            Application   = $script:BuildInformation.Application
            Version       = $script:PackageVersion
            Package       = $script:PackageName
            SHA256        = $script:PackageHash
            ReleaseDate   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            ReleaseFolder = $script:ReleaseFolder
            User          = $env:USERNAME
            Computer      = $env:COMPUTERNAME
            PowerShell    = $PSVersionTable.PSVersion.ToString()
        }
        $OutputFile = Join-Path $script:ReleaseFolder "release_metadata.json"
        Export-PackageJson -Object $Metadata -OutputFile $OutputFile
        Add-PackageResult -Task "Release Metadata" -Status "OK" -Details "release_metadata.json"
    } catch {
        Add-PackageResult -Task "Release Metadata" -Status "FAILED" -Details $_.Exception.Message
        throw
    }
}

function New-DeploymentManifest {
    Write-PackageLog "Generating deployment manifest..."
    try {
        $Files = Get-ChildItem -Path $script:ReleaseFolder -File
        $Manifest = [PSCustomObject]@{
            Application = $script:BuildInformation.Application
            Version     = $script:PackageVersion
            Generated   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            FileCount   = $Files.Count
            Files       = foreach ($File in $Files) {
                [PSCustomObject]@{
                    Name   = $File.Name
                    SizeKB = [Math]::Round($File.Length / 1KB, 2)
                    SHA256 = (Get-FileHash $File.FullName -Algorithm SHA256).Hash
                }
            }
        }
        $OutputFile = Join-Path $script:ReleaseFolder "deployment_manifest.json"
        Export-PackageJson -Object $Manifest -OutputFile $OutputFile
        Add-PackageResult -Task "Deployment Manifest" -Status "OK" -Details "deployment_manifest.json"
    } catch {
        Add-PackageResult -Task "Deployment Manifest" -Status "FAILED" -Details $_.Exception.Message
        throw
    }
}

function Export-PackageReport {
    $ReportData = [PSCustomObject]@{
        Engine   = $script:EngineName
        Started  = $script:StartTime
        Finished = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Results  = $script:PackageResults
    }
    Export-PackageJson -Object $ReportData -OutputFile $script:PackageReportFile
}

# PIPELINE EXECUTION
try {
    Write-PackageLog "========================================"
    Write-PackageLog " Starting Package Module Execution"
    Write-PackageLog "========================================"
    
    # 1. Validation Phase
    Test-BuildArtifacts
    Test-BuildMetadata
    Test-Manifest
    Test-PackageSize
    Test-PackageChecksum
    Test-PackageArchive


    # 2. Release Assembly Phase
    New-ReleaseDirectory
    Copy-ReleaseArtifacts
    New-ReleaseMetadata
    New-DeploymentManifest

    # 3. Report Phase
    Export-PackageReport
    Write-PackageLog "Package module executed successfully."
    $script:ExitCode = 0
} catch {
    $script:ExitCode = 1
    Add-PackageResult -Task "Package Engine" -Status "FAILED" -Details $_.Exception.Message
    try { Export-PackageReport } catch {}
    Write-PackageLog "Package module failed: $_"
} finally {
    $EndTime = Get-Date
    $Elapsed = $EndTime - $script:StartTime
    Write-PackageLog ("Duration: {0:c}" -f $Elapsed)
    Write-PackageLog "Process complete."
}

return $script:ExitCode