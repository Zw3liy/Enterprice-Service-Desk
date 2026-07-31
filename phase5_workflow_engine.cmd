@echo off
title Enterprise Service Desk - Phase 5 Workflow Engine
color 0A

echo ==========================================================
echo Enterprise Service Desk
echo PHASE 5 - Workflow & Approval Engine
echo ==========================================================
echo.

if not exist manage.py (
    echo ERROR: Please run this script from the folder containing manage.py.
    pause
    exit /b 1
)

echo [1/9] Creating workflow directories...

mkdir apps\service_desk\workflow 2>nul
mkdir apps\service_desk\workflow\rules 2>nul
mkdir apps\service_desk\workflow\services 2>nul
mkdir apps\service_desk\workflow\signals 2>nul
mkdir apps\service_desk\workflow\tests 2>nul

mkdir templates\workflow 2>nul

echo.

echo [2/9] Creating workflow files...

type nul > apps\service_desk\workflow\__init__.py
type nul > apps\service_desk\workflow\rules.py
type nul > apps\service_desk\workflow\engine.py
type nul > apps\service_desk\workflow\approvals.py
type nul > apps\service_desk\workflow\notifications.py
type nul > apps\service_desk\workflow\signals.py

type nul > templates\workflow\designer.html
type nul > templates\workflow\approval_queue.html
type nul > templates\workflow\history.html

type nul > static\css\workflow.css
type nul > static\js\workflow.js

echo.

echo [3/9] Running Django system check...
python manage.py check
if errorlevel 1 goto ERROR

echo.

echo [4/9] Creating migrations...
python manage.py makemigrations
if errorlevel 1 goto ERROR

echo.

echo [5/9] Applying migrations...
python manage.py migrate
if errorlevel 1 goto ERROR

echo.

echo [6/9] Running tests...
python manage.py test

echo.

echo [7/9] Collecting static files...
python manage.py collectstatic --noinput

echo.

echo [8/9] Git status...
git status

echo.

echo ==========================================================
echo WORKFLOW ENGINE SCAFFOLD CREATED
echo ==========================================================
echo.
echo Planned capabilities:
echo.
echo  - Workflow definitions
echo  - Approval chains
echo  - Automatic ticket routing
echo  - Status transitions
echo  - Escalation triggers
echo  - Notification hooks
echo  - Audit history
echo  - Business rule engine
echo.

pause
exit /b

:ERROR
echo.
echo ********************************************
echo BUILD FAILED
echo ********************************************
echo Fix the reported Django errors and rerun.
echo.
pause
exit /b 1