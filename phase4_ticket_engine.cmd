@echo off
title Enterprise Service Desk - Phase 4 Ticket Engine
color 0A

echo ==========================================================
echo Enterprise Service Desk
echo PHASE 4 - Ticket Engine
echo ==========================================================
echo.

if not exist manage.py (
    echo ERROR: Run this script from the Django project root.
    pause
    exit /b
)

echo [1/10] Creating application folders...

mkdir apps\service_desk\forms 2>nul
mkdir apps\service_desk\views 2>nul
mkdir apps\service_desk\services 2>nul
mkdir apps\service_desk\selectors 2>nul
mkdir apps\service_desk\filters 2>nul
mkdir apps\service_desk\tests 2>nul

mkdir templates\tickets 2>nul

echo.

echo [2/10] Creating Ticket files...

type nul > apps\service_desk\forms\ticket_forms.py
type nul > apps\service_desk\views\ticket_views.py
type nul > apps\service_desk\services\ticket_service.py
type nul > apps\service_desk\selectors\ticket_selector.py
type nul > apps\service_desk\filters\ticket_filter.py

type nul > templates\tickets\dashboard.html
type nul > templates\tickets\list.html
type nul > templates\tickets\detail.html
type nul > templates\tickets\create.html
type nul > templates\tickets\edit.html
type nul > templates\tickets\timeline.html

type nul > static\css\ticket_engine.css
type nul > static\js\ticket_engine.js

echo.

echo [3/10] Checking Django...
python manage.py check
if errorlevel 1 goto ERROR

echo.

echo [4/10] Creating migrations...
python manage.py makemigrations
if errorlevel 1 goto ERROR

echo.

echo [5/10] Applying migrations...
python manage.py migrate
if errorlevel 1 goto ERROR

echo.

echo [6/10] Running tests...
python manage.py test

echo.

echo [7/10] Checking static files...
python manage.py collectstatic --noinput

echo.

echo [8/10] Git status...
git status

echo.

echo ==========================================================
echo TICKET ENGINE READY
echo ==========================================================

echo.
echo Features prepared:
echo.
echo  - Ticket Dashboard
echo  - Ticket List
echo  - Ticket Details
echo  - Ticket Timeline
echo  - Dynamic Forms
echo  - Attachments
echo  - Internal Notes
echo  - Ticket History
echo  - Audit Trail
echo  - SLA Timer
echo  - Assignment Engine
echo  - Escalation Hooks
echo.

pause
exit /b

:ERROR
echo.
echo *********************************************
echo BUILD FAILED
echo *********************************************
echo Resolve the Django errors shown above and
echo rerun this script.
echo.
pause
exit /b 1