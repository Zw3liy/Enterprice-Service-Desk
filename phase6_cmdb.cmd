@echo off
title Enterprise Service Desk - Phase 6 CMDB
color 0B

echo ==========================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 6 - CMDB / ASSET MANAGEMENT
echo ==========================================================
echo.

if not exist manage.py (
    echo ERROR: Run this script from the Django project root.
    pause
    exit /b 1
)

echo [1/10] Creating CMDB folders...

mkdir apps\service_desk\cmdb 2>nul
mkdir apps\service_desk\cmdb\models 2>nul
mkdir apps\service_desk\cmdb\services 2>nul
mkdir apps\service_desk\cmdb\views 2>nul
mkdir apps\service_desk\cmdb\forms 2>nul
mkdir apps\service_desk\cmdb\tests 2>nul

mkdir templates\cmdb 2>nul

echo.

echo [2/10] Creating Python files...

type nul > apps\service_desk\cmdb\__init__.py
type nul > apps\service_desk\cmdb\models.py
type nul > apps\service_desk\cmdb\views.py
type nul > apps\service_desk\cmdb\forms.py
type nul > apps\service_desk\cmdb\services.py
type nul > apps\service_desk\cmdb\admin.py
type nul > apps\service_desk\cmdb\urls.py

echo.

echo [3/10] Creating HTML templates...

type nul > templates\cmdb\dashboard.html
type nul > templates\cmdb\asset_list.html
type nul > templates\cmdb\asset_detail.html
type nul > templates\cmdb\asset_create.html
type nul > templates\cmdb\asset_edit.html
type nul > templates\cmdb\asset_history.html

echo.

echo [4/10] Creating CSS/JS...

type nul > static\css\cmdb.css
type nul > static\js\cmdb.js

echo.

echo [5/10] Running Django check...
python manage.py check
if errorlevel 1 goto ERROR

echo.

echo [6/10] Making migrations...
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
echo CMDB FRAMEWORK CREATED
echo ==========================================================
echo.
echo Planned enterprise features:
echo.
echo  - Asset inventory
echo  - Configuration Items (CI)
echo  - Asset categories
echo  - Hardware lifecycle
echo  - Software inventory
echo  - Vendors
echo  - Warranties
echo  - Licenses
echo  - Network devices
echo  - Servers
echo  - Workstations
echo  - Mobile devices
echo  - Ticket-to-asset relationships
echo  - Asset audit history
echo.

pause
exit /b

:ERROR
echo.
echo *******************************************
echo BUILD FAILED
echo *******************************************
echo Resolve the Django errors shown above.
echo.
pause
exit /b 1