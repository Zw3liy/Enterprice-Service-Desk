@echo off
title Enterprise Service Desk - Phase 10 Notification Center
color 09

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 10 - EMAIL & NOTIFICATION CENTER
echo ===============================================================
echo.

if not exist manage.py (
    echo ERROR: Run this script from the Django project root.
    pause
    exit /b 1
)

echo [1/10] Creating notification module...

mkdir apps\service_desk\notifications 2>nul
mkdir apps\service_desk\notifications\services 2>nul
mkdir apps\service_desk\notifications\providers 2>nul
mkdir apps\service_desk\notifications\email 2>nul
mkdir apps\service_desk\notifications\sms 2>nul
mkdir apps\service_desk\notifications\push 2>nul
mkdir apps\service_desk\notifications\templates 2>nul
mkdir apps\service_desk\notifications\tests 2>nul

mkdir templates\notifications 2>nul

echo.

echo [2/10] Creating Python files...

type nul > apps\service_desk\notifications\__init__.py
type nul > apps\service_desk\notifications\models.py
type nul > apps\service_desk\notifications\views.py
type nul > apps\service_desk\notifications\urls.py
type nul > apps\service_desk\notifications\admin.py
type nul > apps\service_desk\notifications\forms.py
type nul > apps\service_desk\notifications\services.py
type nul > apps\service_desk\notifications\signals.py
type nul > apps\service_desk\notifications\tasks.py

echo.

echo [3/10] Creating Templates...

type nul > templates\notifications\dashboard.html
type nul > templates\notifications\email_templates.html
type nul > templates\notifications\notification_center.html
type nul > templates\notifications\history.html
type nul > templates\notifications\settings.html

echo.

echo [4/10] Creating Static Files...

type nul > static\css\notifications.css
type nul > static\js\notifications.js

echo.

echo [5/10] Running Django Checks...
python manage.py check
if errorlevel 1 goto ERROR

echo.

echo [6/10] Creating Migrations...
python manage.py makemigrations
if errorlevel 1 goto ERROR

echo.

echo [7/10] Applying Migrations...
python manage.py migrate
if errorlevel 1 goto ERROR

echo.

echo [8/10] Running Tests...
python manage.py test

echo.

echo [9/10] Collecting Static Files...
python manage.py collectstatic --noinput

echo.

echo [10/10] Git Status...
git status

echo.
echo ===============================================================
echo NOTIFICATION CENTER FRAMEWORK CREATED
echo ===============================================================
echo.
echo Planned Features:
echo.
echo  - SMTP email integration
echo  - Ticket email notifications
echo  - HTML email templates
echo  - Email-to-ticket processing
echo  - Notification center
echo  - Browser notifications
echo  - SMS provider integration
echo  - Push notifications
echo  - Reminder scheduler
echo  - Escalation alerts
echo  - Notification history
echo  - Delivery status tracking
echo  - User notification preferences
echo.

pause
exit /b

:ERROR
echo.
echo **************************************************
echo BUILD FAILED
echo **************************************************
echo Fix the Django errors above and rerun.
echo.
pause
exit /b 1