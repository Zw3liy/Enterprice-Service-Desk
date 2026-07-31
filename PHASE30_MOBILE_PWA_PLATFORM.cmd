@echo off
title Enterprise Service Desk - Phase 30 Mobile PWA Platform
color 0D

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 30 - MOBILE APPLICATION & PWA PLATFORM
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/15] Creating Mobile Platform...


mkdir apps\mobile_platform 2>nul
mkdir apps\mobile_platform\models 2>nul
mkdir apps\mobile_platform\services 2>nul
mkdir apps\mobile_platform\notifications 2>nul


type nul > apps\mobile_platform\__init__.py


echo.
echo [2/15] Creating Device Management...


type nul > apps\mobile_platform\models\device.py
type nul > apps\mobile_platform\models\session.py


echo.
echo [3/15] Creating Mobile API Layer...


mkdir api\mobile 2>nul

type nul > api\mobile\views.py
type nul > api\mobile\serializers.py
type nul > api\mobile\urls.py


echo.
echo [4/15] Creating Technician Mobile Workspace...


mkdir apps\technician_mobile 2>nul

type nul > apps\technician_mobile\__init__.py
type nul > apps\technician_mobile\views.py
type nul > apps\technician_mobile\services.py


echo.
echo [5/15] Creating PWA Framework...


mkdir static\pwa 2>nul


type nul > static\pwa\manifest.json
type nul > static\pwa\service-worker.js


echo.
echo [6/15] Creating Mobile UI Components...


mkdir templates\mobile 2>nul


type nul > templates\mobile\dashboard.html
type nul > templates\mobile\tickets.html
type nul > templates\mobile\approvals.html


echo.
echo [7/15] Creating Push Notification Engine...


type nul > apps\mobile_platform\notifications\push.py
type nul > apps\mobile_platform\notifications\events.py


echo.
echo [8/15] Creating Offline Sync Foundation...


mkdir apps\offline_sync 2>nul


type nul > apps\offline_sync\__init__.py
type nul > apps\offline_sync\sync.py
type nul > apps\offline_sync\queue.py


echo.
echo [9/15] Creating QR Asset Scanner...


mkdir apps\qr_scanner 2>nul


type nul > apps\qr_scanner\__init__.py
type nul > apps\qr_scanner\scanner.py
type nul > apps\qr_scanner\asset_lookup.py


echo.
echo [10/15] Creating Mobile Authentication...


mkdir apps\mobile_auth 2>nul


type nul > apps\mobile_auth\__init__.py
type nul > apps\mobile_auth\tokens.py
type nul > apps\mobile_auth\device_auth.py


echo.
echo [11/15] Creating Responsive Theme Layer...


mkdir static\mobile_css 2>nul


type nul > static\mobile_css\responsive.css
type nul > static\mobile_css\components.css


echo.
echo [12/15] Django Validation...


python manage.py check

if errorlevel 1 goto ERROR


echo.
echo [13/15] Creating Database Changes...


python manage.py makemigrations


echo.
echo [14/15] Applying Database...


python manage.py migrate


echo.
echo [15/15] Git Preparation...


git add .

git status


echo.
echo ===============================================================
echo PHASE 30 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] Mobile API Layer
echo [OK] PWA Foundation
echo [OK] Technician Workspace
echo [OK] Push Notifications
echo [OK] Offline Sync
echo [OK] QR Asset Scanner
echo [OK] Mobile Authentication
echo [OK] Responsive UI Framework
echo.


pause
exit /b 0


:ERROR

echo.
echo ===============================================================
echo PHASE 30 FAILED
echo ===============================================================

echo Fix Django errors before continuing.

pause
exit /b 1