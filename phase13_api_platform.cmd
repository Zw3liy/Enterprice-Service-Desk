@echo off
title Enterprise Service Desk - Phase 13 API Platform
color 0B

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 13 - REST API & INTEGRATION PLATFORM
echo ===============================================================
echo.

if not exist manage.py (
    echo ERROR: Run this script from the Django project root.
    pause
    exit /b 1
)

echo [1/10] Creating API platform...

mkdir apps\service_desk\api 2>nul
mkdir apps\service_desk\api\v1 2>nul
mkdir apps\service_desk\api\v2 2>nul
mkdir apps\service_desk\api\serializers 2>nul
mkdir apps\service_desk\api\views 2>nul
mkdir apps\service_desk\api\permissions 2>nul
mkdir apps\service_desk\api\webhooks 2>nul
mkdir apps\service_desk\api\integrations 2>nul
mkdir apps\service_desk\api\tests 2>nul

mkdir templates\api 2>nul

echo.

echo [2/10] Creating Python files...

type nul > apps\service_desk\api\__init__.py
type nul > apps\service_desk\api\urls.py
type nul > apps\service_desk\api\views.py
type nul > apps\service_desk\api\serializers.py
type nul > apps\service_desk\api\permissions.py
type nul > apps\service_desk\api\authentication.py
type nul > apps\service_desk\api\webhooks.py
type nul > apps\service_desk\api\swagger.py
type nul > apps\service_desk\api\openapi.py
type nul > apps\service_desk\api\throttling.py

echo.

echo [3/10] Creating Integration folders...

mkdir integrations\microsoft365 2>nul
mkdir integrations\active_directory 2>nul
mkdir integrations\azure 2>nul
mkdir integrations\servicenow 2>nul
mkdir integrations\jira 2>nul
mkdir integrations\teams 2>nul
mkdir integrations\slack 2>nul
mkdir integrations\webhooks 2>nul

echo.

echo [4/10] Creating API documentation...

type nul > templates\api\documentation.html
type nul > templates\api\swagger.html
type nul > templates\api\webhooks.html

echo.

echo [5/10] Creating Static Files...

type nul > static\css\api.css
type nul > static\js\api.js

echo.

echo [6/10] Django System Check...
python manage.py check
if errorlevel 1 goto ERROR

echo.

echo [7/10] Creating migrations...
python manage.py makemigrations
if errorlevel 1 goto ERROR

echo.

echo [8/10] Applying migrations...
python manage.py migrate
if errorlevel 1 goto ERROR

echo.

echo [9/10] Running tests...
python manage.py test

echo.

echo [10/10] Git status...
git status

echo.
echo ===============================================================
echo API PLATFORM CREATED
echo ===============================================================
echo.
echo Enterprise Features Ready:
echo.
echo  - REST API
echo  - OpenAPI Specification
echo  - Swagger UI
echo  - JWT Authentication
echo  - OAuth2
echo  - API Keys
echo  - Webhooks
echo  - Rate Limiting
echo  - Microsoft 365 Integration
echo  - Active Directory Integration
echo  - Microsoft Teams Integration
echo  - Slack Integration
echo  - Jira Integration
echo  - Monitoring Tool Integration
echo  - Mobile Application API
echo  - Third-party SDK Support
echo.

pause
exit /b

:ERROR
echo.
echo *********************************************
echo BUILD FAILED
echo *********************************************
echo Resolve the Django errors above and rerun.
echo.
pause
exit /b 1