<#
=========================================================
 Enterprise Service Desk
 Production Validation Engine

 Module:
 Validate.ps1

 Called by:

 .\Deploy.ps1 validate

=========================================================
#>


$RootPath =
Split-Path `
-Parent `
(Split-Path `
-Parent `
$MyInvocation.MyCommand.Path)



$DeploymentPath =
Join-Path $RootPath "deployment"


$ReportPath =
Join-Path $DeploymentPath "reports"



if(!(Test-Path $ReportPath)){

    New-Item `
    -ItemType Directory `
    -Path $ReportPath `
    -Force | Out-Null

}



$Results = @()



# ======================================================
# RESULT ENGINE
# ======================================================

function Add-Result {


param(

[string]$Category,

[string]$Check,

[string]$Status,

[string]$Message

)


$global:Results += [PSCustomObject]@{

Category=$Category

Check=$Check

Status=$Status

Message=$Message

}

Write-Host "

[$Status]
$Category
$Check
$Message

"


}




# ======================================================
# ENVIRONMENT VALIDATION
# ======================================================


function Test-Python {


try {


$version =
python --version 2>&1


Add-Result `
"Environment" `
"Python Version" `
"PASS" `
$version


}

catch {


Add-Result `
"Environment" `
"Python Version" `
"FAIL" `
"Python unavailable"


}


}




function Test-VirtualEnvironment {


if(Test-Path ".\venv"){


Add-Result `
"Environment" `
"Virtual Environment" `
"PASS" `
"venv directory found"


}

else {


Add-Result `
"Environment" `
"Virtual Environment" `
"WARN" `
"No venv directory detected"


}


}





function Test-Requirements {


if(Test-Path ".\requirements.txt"){


Add-Result `
"Environment" `
"Requirements File" `
"PASS" `
"requirements.txt found"


}

else {


Add-Result `
"Environment" `
"Requirements File" `
"FAIL" `
"requirements.txt missing"


}


}




function Test-Env {


if(Test-Path ".env"){


Add-Result `
"Environment" `
"Environment File" `
"PASS" `
".env exists"


}

else {


Add-Result `
"Environment" `
"Environment File" `
"WARN" `
".env missing"


}


}




# ======================================================
# DJANGO VALIDATION
# ======================================================


function Test-Django {


if(Test-Path ".\manage.py"){


Add-Result `
"Django" `
"manage.py" `
"PASS" `
"manage.py found"


}

else {


Add-Result `
"Django" `
"manage.py" `
"FAIL" `
"manage.py missing"


}



try{


python manage.py check


Add-Result `
"Django" `
"System Check" `
"PASS" `
"Django configuration valid"


}

catch {


Add-Result `
"Django" `
"System Check" `
"FAIL" `
"Django check failed"


}


}





function Test-Apps {


try{


python manage.py shell -c "from django.conf import settings; print(settings.INSTALLED_APPS)"


Add-Result `
"Django" `
"Installed Apps" `
"PASS" `
"Applications loaded"


}

catch{


Add-Result `
"Django" `
"Installed Apps" `
"FAIL" `
"Unable to load applications"


}


}





# ======================================================
# FILE STRUCTURE VALIDATION
# ======================================================


function Test-Templates {


if(Test-Path ".\templates"){


Add-Result `
"Frontend" `
"Templates" `
"PASS" `
"templates directory exists"


}

else {


Add-Result `
"Frontend" `
"Templates" `
"FAIL" `
"templates directory missing"


}


}




function Test-Static {


if(Test-Path ".\static"){


Add-Result `
"Frontend" `
"Static Files" `
"PASS" `
"static directory exists"


}

else {


Add-Result `
"Frontend" `
"Static Files" `
"WARN" `
"static directory missing"


}


}





# ======================================================
# INFRASTRUCTURE
# ======================================================


function Test-Docker {


try{


docker --version


Add-Result `
"Infrastructure" `
"Docker" `
"PASS" `
"Docker installed"


}

catch {


Add-Result `
"Infrastructure" `
"Docker" `
"WARN" `
"Docker unavailable"


}


}




function Test-Git {


try{


$status =
git status --short


if(!$status){


Add-Result `
"Infrastructure" `
"Git Status" `
"PASS" `
"Working tree clean"


}

else {


Add-Result `
"Infrastructure" `
"Git Status" `
"WARN" `
"Uncommitted changes detected"


}


}

catch{


Add-Result `
"Infrastructure" `
"Git" `
"WARN" `
"Git unavailable"


}


}





# ======================================================
# SYSTEM
# ======================================================


function Test-Disk {


$drive =
Get-PSDrive C


$free =
[math]::Round(
$drive.Free/1GB,
2
)



Add-Result `
"System" `
"Disk Space" `
"PASS" `
"$free GB available"



}





# ======================================================
# REPORT GENERATION
# ======================================================


function Save-Report {


$ReportFile =
Join-Path `
$ReportPath `
"validation_report.json"



$Results |
ConvertTo-Json -Depth 5 |
Set-Content $ReportFile



Write-Host "

====================================

Validation Complete

Report:

$ReportFile

====================================

"


}





# ======================================================
# EXECUTION
# ======================================================


Write-Host "

====================================
 Enterprise Service Desk
 Production Validation Engine
====================================

"



Test-Python

Test-VirtualEnvironment

Test-Requirements

Test-Env

Test-Django

Test-Apps

Test-Templates

Test-Static

Test-Docker

Test-Git

Test-Disk


Save-Report
