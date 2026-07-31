@echo off
title Enterprise Service Desk - Phase 7 Knowledge Base
color 0A

echo =============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 7 - KNOWLEDGE BASE & SELF-SERVICE PORTAL
echo =============================================================
echo.

if not exist manage.py (
    echo ERROR: manage.py not found.
    echo Run this script from your Django project root.
    pause
    exit /b 1
)

echo [1/10] Creating Knowledge Base folders...

mkdir apps\service_desk\knowledge 2>nul
mkdir apps\service_desk\knowledge\services 2>nul
mkdir apps\service_desk\knowledge\forms 2>nul
mkdir apps\service_desk\knowledge\views 2>nul
mkdir apps\service_desk\knowledge\tests 2>nul

mkdir templates\knowledge 2>nul
mkdir templates\portal 2>nul

echo.

echo [2/10] Creating Python modules...

type nul > apps\service_desk\knowledge\__init__.py
type nul > apps\service_desk\knowledge\models.py
type nul > apps\service_desk\knowledge\views.py
type nul > apps\service_desk\knowledge\forms.py
type nul > apps\service_desk\knowledge\admin.py
type nul > apps\service_desk\knowledge\urls.py
type nul > apps\service_desk\knowledge\services.py

echo.

echo [3/10] Creating templates...

type nul > templates\knowledge\dashboard.html
type nul > templates\knowledge\article_list.html
type nul > templates\knowledge\article_detail.html
type nul > templates\knowledge\article_create.html
type nul > templates\knowledge\article_edit.html

type nul > templates\portal\home.html
type nul > templates\portal\search.html
type nul > templates\portal\faq.html

echo.

echo [4/10] Creating CSS and JavaScript...

type nul > static\css\knowledge.css
type nul > static\css\portal.css

type nul > static\js\knowledge.js
type nul > static\js\portal.js

echo.

echo [5/10] Running Django system check...
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
echo =============================================================
echo KNOWLEDGE BASE FRAMEWORK CREATED
echo =============================================================
echo.
echo Planned Features:
echo.
echo  - Knowledge Articles
echo  - Categories
echo  - Tags
echo  - Rich Text Editor
echo  - Attachments
echo  - FAQ Management
echo  - Article Search
echo  - Related Articles
echo  - Article Ratings
echo  - Comments
echo  - Version History
echo  - Publishing Workflow
echo  - Self-Service Portal
echo  - Suggested Articles on Ticket Creation
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