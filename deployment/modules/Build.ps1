# ======================================================
# BUILD STATE
# ======================================================

if ($null -eq $script:BuildResults) {
    $script:BuildResults = @()
}

# ======================================================
# RESULT TRACKER
# ======================================================

function Add-BuildResult {

    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,

        [Parameter(Mandatory = $true)]
        [ValidateSet("OK","FAILED","WARNING","SKIPPED","INFO")]
        [string]$Status,

        [Parameter(Mandatory = $true)]
        [string]$Details
    )

    if ($null -eq $script:BuildResults) {
        $script:BuildResults = @()
    }

    $Result = [PSCustomObject]@{
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Task      = $Task
        Status    = $Status
        Details   = $Details
    }

    $script:BuildResults += $Result

    if (Get-Command Write-BuildLog -ErrorAction SilentlyContinue) {
        Write-BuildLog ("[{0}] {1} | {2}" -f $Status, $Task, $Details)
    }

    return $Result
}