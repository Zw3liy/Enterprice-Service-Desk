@echo off
title Enterprise Service Desk - Phase 8 SLA Engine
color 0E

echo ==========================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 8 - SLA & BUSINESS HOURS ENGINE
echo ==========================================================
echo.

if not exist manage.py (
    echo ERROR: manage.py not found.
    echo Run this script from the Django project root.
    pause
    exit /b 1
)

echo [1/10] Creating SLA folders...

mkdir apps\service_desk\sla 2>nul
mkdir apps\service_desk\sla\services 2>nul
mkdir apps\service_desk\sla\forms 2>nul
mkdir apps\service_desk\sla\views 2>nul
mkdir apps\service_desk\sla\tests 2>nul

mkdir templates\sla 2>nul

echo.

echo [2/10] Creating Python files...

type nul > apps\service_desk\sla\__init__.py
type nul > apps\service_desk\sla\models.py
type nul > apps\service_desk\sla\views.py
type nul > apps\service_desk\sla\forms.py
type nul > apps\service_desk\sla\admin.py
type nul > apps\service_desk\sla\urls.py
type nul > apps\service_desk\sla\services.py

echo.

echo [3/10] Creating templates...

type nul > templates\sla\dashboard.html
type nul > templates\sla\policy_list.html
type nul > templates\sla\policy_detail.html
type nul > templates\sla\calendar.html
type nul > templates\sla\business_hours.html
type nul > templates\sla\holiday_schedule.html

echo.

echo [4/10] Creating CSS and JavaScript...

type nul > static\css\sla.css
type nul > static\css\calendar.css

type nul > static\js\sla.js
type nul > static\js\calendar.js

echo.

echo [5/10] Running Django system check...
python manage.py check
if errorlevel 1 goto ERROR

echo.

echo [6/10] Creating migrations...
python manage.py makemigrations
if errorlevel 1 goto ERROR

echo.

echo [7/10] Applying migrations...
python manage.py migrate
if errorlevel 1 goto ERROR

echo.

echo [8/10] Running tests...
python manage.py test

echo.

echo [9/10] Collecting static files...
python manage.py collectstatic --noinput

echo.

echo [10/10] Git status...
git status

echo.
echo ==========================================================
echo SLA ENGINE FRAMEWORK CREATED
echo ==========================================================
echo.
echo Planned Features:
echo.
echo  - SLA Policies
echo  - Business Hours
echo  - Holiday Calendars
echo  - Response Targets
echo  - Resolution Targets
echo  - Pause / Resume Timers
echo  - Breach Detection
echo  - Escalation Rules
echo  - SLA Dashboards
echo  - SLA Reports
echo  - Ticket Timers
echo  - Priority-based SLAs
echo.

pause
exit /b

:ERROR
echo.
echo **********************************************
echo BUILD FAILED
echo **********************************************
echo Resolve the reported Django errors and rerun.
echo.
pause
exit /b 1