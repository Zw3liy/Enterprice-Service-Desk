@echo off
title Enterprise Service Desk - Phase 3 Dashboard
color 0A

echo ======================================================
echo Enterprise Service Desk
echo PHASE 3 - Dashboard Module Generator
echo ======================================================
echo.

if not exist manage.py (
    echo ERROR: Run this script from the folder containing manage.py
    pause
    exit /b
)

echo [1/9] Creating dashboard folders...

mkdir apps\service_desk\views 2>nul
mkdir apps\service_desk\services 2>nul
mkdir apps\service_desk\selectors 2>nul
mkdir apps\service_desk\tests 2>nul

mkdir templates\dashboard 2>nul
mkdir templates\components 2>nul

mkdir static\css 2>nul
mkdir static\js 2>nul

echo.

echo [2/9] Creating dashboard files...

type nul > apps\service_desk\views\dashboard.py
type nul > apps\service_desk\services\dashboard_service.py
type nul > apps\service_desk\selectors\dashboard_selector.py

type nul > templates\dashboard\index.html
type nul > templates\components\dashboard_cards.html
type nul > templates\components\sidebar.html
type nul > templates\components\navbar.html

type nul > static\css\dashboard.css
type nul > static\css\widgets.css
type nul > static\js\dashboard.js

echo.

echo [3/9] Running Django system check...
python manage.py check

if errorlevel 1 (
    echo.
    echo Django check failed.
    pause
    exit /b
)

echo.

echo [4/9] Making migrations...
python manage.py makemigrations

echo.

echo [5/9] Applying migrations...
python manage.py migrate

echo.

echo [6/9] Collecting static files...
python manage.py collectstatic --noinput

echo.

echo [7/9] Running tests...
python manage.py test

echo.

echo [8/9] Creating Git status...
git status

echo.

echo ======================================================
echo PHASE 3 COMPLETE
echo ======================================================
echo.
echo Dashboard framework created.
echo Ready for KPI widgets, charts, ticket analytics,
echo SLA indicators and activity feeds.
echo.

pause