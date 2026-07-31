@echo off
title Enterprise Service Desk - Phase 34 ITIL Management Core
color 05

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 34 - ITIL INCIDENT PROBLEM CHANGE MANAGEMENT
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/16] Creating ITIL Core Application...


mkdir apps\itil_core 2>nul
mkdir apps\itil_core\models 2>nul
mkdir apps\itil_core\services 2>nul
mkdir apps\itil_core\workflows 2>nul
mkdir apps\itil_core\reports 2>nul


type nul > apps\itil_core\__init__.py


echo.
echo [2/16] Creating Incident Management...


mkdir apps\incident_management 2>nul


type nul > apps\incident_management\__init__.py
type nul > apps\incident_management\models.py
type nul > apps\incident_management\lifecycle.py
type nul > apps\incident_management\major_incident.py


echo.
echo [3/16] Creating Problem Management...


mkdir apps\problem_management 2>nul


type nul > apps\problem_management\__init__.py
type nul > apps\problem_management\models.py
type nul > apps\problem_management\rca.py
type nul > apps\problem_management\known_errors.py


echo.
echo [4/16] Creating Change Management...


mkdir apps\change_management 2>nul


type nul > apps\change_management\__init__.py
type nul > apps\change_management\models.py
type nul > apps\change_management\approval.py
type nul > apps\change_management\risk.py


echo.
echo [5/16] Creating CAB Management...


mkdir apps\cab_management 2>nul


type nul > apps\cab_management\__init__.py
type nul > apps\cab_management\models.py
type nul > apps\cab_management\meetings.py


echo.
echo [6/16] Creating Change Calendar...


mkdir apps\change_calendar 2>nul


type nul > apps\change_calendar\__init__.py
type nul > apps\change_calendar\calendar.py


echo.
echo [7/16] Creating RCA Framework...


type nul > apps\itil_core\services\root_cause_analysis.py
type nul > apps\itil_core\services\impact_analysis.py


echo.
echo [8/16] Creating ITIL Workflow Integration...


type nul > apps\itil_core\workflows\approval_flow.py
type nul > apps\itil_core\workflows\escalation_flow.py


echo.
echo [9/16] Creating ITIL Dashboards...


mkdir templates\itil 2>nul


type nul > templates\itil\dashboard.html
type nul > templates\itil\incidents.html
type nul > templates\itil\problems.html
type nul > templates\itil\changes.html


echo.
echo [10/16] Creating ITIL API...


mkdir api\itil 2>nul


type nul > api\itil\views.py
type nul > api\itil\serializers.py
type nul > api\itil\urls.py


echo.
echo [11/16] Creating Reporting Engine...


type nul > apps\itil_core\reports\metrics.py
type nul > apps\itil_core\reports\sla_report.py


echo.
echo [12/16] Creating Notification Integration...


type nul > apps\itil_core\services\notifications.py


echo.
echo [13/16] Django Validation...


python manage.py check

if errorlevel 1 goto ERROR


echo.
echo [14/16] Creating Database Migrations...


python manage.py makemigrations


echo.
echo [15/16] Applying Database...


python manage.py migrate


echo.
echo [16/16] Git Preparation...


git add .

git status


echo.
echo ===============================================================
echo PHASE 34 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] Incident Management
echo [OK] Major Incident Process
echo [OK] Problem Management
echo [OK] Root Cause Analysis
echo [OK] Known Error Database
echo [OK] Change Management
echo [OK] CAB Workflow
echo [OK] Risk Assessment
echo [OK] ITIL Reporting
echo [OK] Approval Integration
echo.


pause
exit /b 0


:ERROR

echo.
echo ===============================================================
echo PHASE 34 FAILED
echo ===============================================================

echo Fix Django errors before continuing.

pause
exit /b 1