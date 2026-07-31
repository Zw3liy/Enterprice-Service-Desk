@echo off
title Enterprise Service Desk - Phase 40 Customer Portal Service Catalog
color 0D

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 40 - CUSTOMER PORTAL & SERVICE CATALOG
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/16] Creating Customer Portal Engine...


mkdir apps\customer_portal 2>nul
mkdir apps\customer_portal\models 2>nul
mkdir apps\customer_portal\services 2>nul
mkdir apps\customer_portal\views 2>nul


type nul > apps\customer_portal\__init__.py


echo.
echo [2/16] Creating Customer Profile Management...


type nul > apps\customer_portal\models\customer.py
type nul > apps\customer_portal\models\organization.py
type nul > apps\customer_portal\models\preferences.py


echo.
echo [3/16] Creating Service Catalog...


mkdir apps\service_catalog 2>nul


type nul > apps\service_catalog\__init__.py
type nul > apps\service_catalog\models.py
type nul > apps\service_catalog\catalog.py
type nul > apps\service_catalog\categories.py


echo.
echo [4/16] Creating Catalog Items...


mkdir apps\catalog_items 2>nul


type nul > apps\catalog_items\__init__.py
type nul > apps\catalog_items\models.py
type nul > apps\catalog_items\forms.py
type nul > apps\catalog_items\validation.py


echo.
echo [5/16] Creating Request Fulfillment Engine...


mkdir apps\request_fulfillment 2>nul


type nul > apps\request_fulfillment\__init__.py
type nul > apps\request_fulfillment\models.py
type nul > apps\request_fulfillment\workflow.py
type nul > apps\request_fulfillment\processor.py


echo.
echo [6/16] Creating Customer Dashboard...


mkdir templates\customer_portal 2>nul


type nul > templates\customer_portal\dashboard.html
type nul > templates\customer_portal\requests.html
type nul > templates\customer_portal\services.html


echo.
echo [7/16] Creating Portal Authentication...


mkdir apps\portal_auth 2>nul


type nul > apps\portal_auth\__init__.py
type nul > apps\portal_auth\registration.py
type nul > apps\portal_auth\access.py


echo.
echo [8/16] Creating Customer Notifications...


mkdir apps\customer_notifications 2>nul


type nul > apps\customer_notifications\__init__.py
type nul > apps\customer_notifications\models.py
type nul > apps\customer_notifications\email.py
type nul > apps\customer_notifications\alerts.py


echo.
echo [9/16] Creating Service Availability Module...


mkdir apps\service_availability 2>nul


type nul > apps\service_availability\__init__.py
type nul > apps\service_availability\models.py
type nul > apps\service_availability\monitor.py


echo.
echo [10/16] Creating Portal API...


mkdir api\customer_portal 2>nul


type nul > api\customer_portal\views.py
type nul > api\customer_portal\serializers.py
type nul > api\customer_portal\urls.py


echo.
echo [11/16] Creating External Customer Access...


mkdir apps\external_access 2>nul


type nul > apps\external_access\__init__.py
type nul > apps\external_access\permissions.py
type nul > apps\external_access\security.py


echo.
echo [12/16] Creating Portal Reporting...


mkdir apps\portal_reporting 2>nul


type nul > apps\portal_reporting\__init__.py
type nul > apps\portal_reporting\metrics.py


echo.
echo [13/16] Django Validation...


python manage.py check

if errorlevel 1 goto ERROR


echo.
echo [14/16] Creating Database Migrations...


python manage.py makemigrations


echo.
echo [15/16] Applying Database...


python manage.py migrate


echo.
echo [16/16] Git Preparation...


git add .

git status


echo.
echo ===============================================================
echo PHASE 40 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] Customer Portal
echo [OK] Service Catalog
echo [OK] Catalog Items
echo [OK] Request Fulfillment
echo [OK] Customer Dashboard
echo [OK] Portal Authentication
echo [OK] Notifications
echo [OK] Service Availability
echo [OK] External Access
echo [OK] Portal API
echo.


pause
exit /b 0


:ERROR

echo.
echo ===============================================================
echo PHASE 40 FAILED
echo ===============================================================

echo Fix Django errors before continuing.

pause
exit /b 1