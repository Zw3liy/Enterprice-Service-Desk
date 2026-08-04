<#
=========================================================
 Enterprise Service Desk
 Automatic Repair Engine

 Module:
 Repair.ps1

 Phase:
 2 - Automatic Repair

 Command:

 .\Deploy.ps1 repair

=========================================================
#>


# ======================================================
# PATH INITIALIZATION
# ======================================================

$RootPath = Split-Path `
-Parent `
(Split-Path `
-Parent `
(Split-Path `
-Parent `
$MyInvocation.MyCommand.Path))


$DeploymentPath = Join-Path $RootPath "deployment"

$LogDirectory = Join-Path $DeploymentPath "logs"

$ReportDirectory = Join-Path $DeploymentPath "reports"


foreach($Directory in @(
    $LogDirectory,
    $ReportDirectory
)){

    if(!(Test-Path $Directory)){

        New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force |
        Out-Null

    }

}



$LogFile =
Join-Path `
$LogDirectory `
("repair_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))



# ======================================================
# GLOBAL STATE
# ======================================================


$global:RepairResults = @()



# ======================================================
# LOGGING
# ======================================================


function Write-RepairLog {


param(
[string]$Message
)


$Time =
Get-Date -Format "yyyy-MM-dd HH:mm:ss"


$Entry =
"[$Time] $Message"


Write-Host $Entry


Add-Content `
-Path $LogFile `
-Value $Entry


}




# ======================================================
# RESULT ENGINE
# ======================================================


function Add-RepairResult {


param(

[string]$Action,

[string]$Status,

[string]$Details

)


$global:RepairResults +=
[PSCustomObject]@{

Action=$Action

Status=$Status

Details=$Details

}


Write-RepairLog "$Status | $Action | $Details"


}





# ======================================================
# DIRECTORY REPAIR
# ======================================================


function Repair-Directories {


$Required=@(

"deployment",

"deployment\modules",

"deployment\logs",

"deployment\reports",

"deployment\backups",

"deployment\artifacts",

"deployment\releases",

"staticfiles",

"media"

)



foreach($Directory in $Required){


$Path =
Join-Path `
$RootPath `
$Directory



if(!(Test-Path $Path)){


New-Item `
-ItemType Directory `
-Path $Path `
-Force |
Out-Null


Add-RepairResult `
"Directory" `
"FIXED" `
"$Directory created"


}

else {


Add-RepairResult `
"Directory" `
"OK" `
"$Directory exists"


}


}



}




# ======================================================
# ENVIRONMENT REPAIR
# ======================================================


function Repair-EnvironmentFile {


$Env =
Join-Path `
$RootPath `
".env"



$Example =
Join-Path `
$RootPath `
".env.example"



if(!(Test-Path $Env)){


if(Test-Path $Example){


Copy-Item `
$Example `
$Env `
-Force


Add-RepairResult `
"Environment" `
"FIXED" `
".env created"


}

else {


New-Item `
$Env `
-ItemType File `
-Force |
Out-Null


Add-RepairResult `
"Environment" `
"FIXED" `
"Empty .env created"


}


}

else {


Add-RepairResult `
"Environment" `
"OK" `
".env exists"


}


}





# ======================================================
# STATIC ROOT
# ======================================================


function Repair-StaticRoot {


$Static =
Join-Path `
$RootPath `
"staticfiles"



if(!(Test-Path $Static)){


New-Item `
-ItemType Directory `
-Path $Static `
-Force |
Out-Null


Add-RepairResult `
"STATIC_ROOT" `
"FIXED" `
"staticfiles created"


}

else {


Add-RepairResult `
"STATIC_ROOT" `
"OK" `
"staticfiles exists"


}


}





# ======================================================
# DJANGO DATABASE
# ======================================================


function Repair-DjangoDatabase {


$Manage =
Join-Path `
$RootPath `
"manage.py"



if(!(Test-Path $Manage)){


Add-RepairResult `
"Django Migration" `
"SKIPPED" `
"manage.py missing"


return

}



try{


Push-Location $RootPath


python manage.py makemigrations

python manage.py migrate


Pop-Location


Add-RepairResult `
"Django Migration" `
"FIXED" `
"Migrations completed"


}

catch{


Add-RepairResult `
"Django Migration" `
"FAILED" `
$_


}


}





# ======================================================
# COLLECT STATIC
# ======================================================


function Repair-CollectStatic {


try{


Push-Location $RootPath


python manage.py collectstatic --noinput


Pop-Location


Add-RepairResult `
"Collect Static" `
"FIXED" `
"Static collection completed"


}

catch{


Add-RepairResult `
"Collect Static" `
"FAILED" `
$_


}


}





# ======================================================
# PERMISSION CHECK
# ======================================================


function Repair-Permissions {


$TestFile =
Join-Path `
$LogDirectory `
"permission_test.tmp"



try{


"test" |
Set-Content $TestFile


Remove-Item `
$TestFile `
-Force



Add-RepairResult `
"Permissions" `
"OK" `
"Write access confirmed"


}

catch{


Add-RepairResult `
"Permissions" `
"FAILED" `
$_


}



}




# ======================================================
# DEPLOYMENT FILE CHECK
# ======================================================


function Repair-DeploymentFiles {


$Files=@(

"Deploy.ps1",

"deployment\modules\Repair.ps1"

)



foreach($File in $Files){


if(Test-Path (Join-Path $RootPath $File)){


Add-RepairResult `
"Deployment File" `
"OK" `
"$File exists"


}

else{


Add-RepairResult `
"Deployment File" `
"WARNING" `
"$File missing"


}


}



}





# ======================================================
# REPORT
# ======================================================


function Export-RepairReport {


$Report =
Join-Path `
$ReportDirectory `
"repair_report.json"



$global:RepairResults |
ConvertTo-Json `
-Depth 5 |
Set-Content `
$Report



Write-Host "

Report:

$Report

"


}




# ======================================================
# SUMMARY
# ======================================================


function Show-RepairSummary {


$Fixed =
($global:RepairResults |
Where-Object Status -eq "FIXED").Count


$Failed =
($global:RepairResults |
Where-Object Status -eq "FAILED").Count



Write-Host @"

========================================

Enterprise Service Desk
Repair Completed


Fixed:
$Fixed


Failed:
$Failed


========================================

"@


}





# ======================================================
# MAIN EXECUTION PIPELINE
# ======================================================


Write-Host @"

========================================
 Enterprise Service Desk
 Automatic Repair Engine
========================================

"@


Repair-Directories

Repair-EnvironmentFile

Repair-StaticRoot

Repair-DjangoDatabase

Repair-CollectStatic

Repair-Permissions

Repair-DeploymentFiles

Export-RepairReport

Show-RepairSummary