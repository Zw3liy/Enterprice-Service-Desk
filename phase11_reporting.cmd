@echo off
title Enterprise Service Desk - Phase 11 Reporting & Analytics
color 03

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 11 - REPORTING & ANALYTICS
echo ===============================================================
echo.

if not exist manage.py (
    echo ERROR: manage.py not found.
    echo Run this script from the Django project root.
    pause
    exit /b 1
)

echo [1/10] Creating Reporting module...

mkdir apps\service_desk\reporting 2>nul
mkdir apps\service_desk\reporting\services 2>nul
mkdir apps\service_desk\reporting\charts 2>nul
mkdir apps\service_desk\reporting\exports 2>nul
mkdir apps\service_desk\reporting\tests 2>nul

mkdir templates\reporting 2>nul

echo.

echo [2/10] Creating Python files...

type nul > apps\service_desk\reporting\__init__.py
type nul > apps\service_desk\reporting\models.py
type nul > apps\service_desk\reporting\views.py
type nul > apps\service_desk\reporting\urls.py
type nul > apps\service_desk\reporting\admin.py
type nul > apps\service_desk\reporting\services.py
type nul > apps\service_desk\reporting\dashboard.py
type nul > apps\service_desk\reporting\exports.py
type nul > apps\service_desk\reporting\metrics.py

echo.

echo [3/10] Creating Templates...

type nul > templates\reporting\dashboard.html
type nul > templates\reporting\executive_dashboard.html
type nul > templates\reporting\agent_dashboard.html
type nul > templates\reporting\reports.html
type nul > templates\reporting\scheduled_reports.html
type nul > templates\reporting\exports.html

echo.

echo [4/10] Creating Static Resources...

type nul > static\css\reporting.css
type nul > static\css\charts.css

type nul > static\js\reporting.js
type nul > static\js\charts.js

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
echo ===============================================================
echo REPORTING FRAMEWORK CREATED
echo ===============================================================
echo.
echo Planned Features:
echo.
echo  - Executive Dashboard
echo  - Agent Dashboard
echo  - Ticket KPIs
echo  - SLA Compliance Reports
echo  - Department Performance
echo  - Technician Workload
echo  - Customer Satisfaction Reports
echo  - Trend Analysis
echo  - Asset Reports
echo  - Scheduled Reports
echo  - PDF Export
echo  - Excel Export
echo  - CSV Export
echo  - Interactive Charts
echo  - Custom Report Builder
echo  - Drill-down Analytics
echo.

pause
exit /b

:ERROR
echo.
echo ****************************************************
echo BUILD FAILED
echo ****************************************************
echo Resolve the reported Django errors and rerun.
echo.
pause
exit /b 1