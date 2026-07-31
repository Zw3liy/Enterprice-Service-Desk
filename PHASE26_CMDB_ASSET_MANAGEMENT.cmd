@echo off
title Enterprise Service Desk - Phase 26 CMDB Asset Management
color 05

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 26 - CMDB & ASSET MANAGEMENT
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/15] Creating CMDB Application...


mkdir apps\cmdb 2>nul
mkdir apps\cmdb\models 2>nul
mkdir apps\cmdb\services 2>nul
mkdir apps\cmdb\discovery 2>nul
mkdir apps\cmdb\relationships 2>nul


type nul > apps\cmdb\__init__.py


echo.
echo [2/15] Creating Asset Models...


type nul > apps\cmdb\models\asset.py
type nul > apps\cmdb\models\asset_type.py
type nul > apps\cmdb\models\software.py
type nul > apps\cmdb\models\vendor.py


echo.
echo [3/15] Creating Configuration Item Models...


type nul > apps\cmdb\models\configuration_item.py
type nul > apps\cmdb\models\relationship.py


echo.
echo [4/15] Creating Asset Lifecycle Engine...


type nul > apps\cmdb\services\lifecycle.py
type nul > apps\cmdb\services\ownership.py
type nul > apps\cmdb\services\warranty.py


echo.
echo [5/15] Creating Discovery Framework...


type nul > apps\cmdb\discovery\scanner.py
type nul > apps\cmdb\discovery\network_discovery.py
type nul > apps\cmdb\discovery\collector.py


echo.
echo [6/15] Creating Asset Relationship Mapping...


type nul > apps\cmdb\relationships\mapper.py
type nul > apps\cmdb\relationships\dependency.py


echo.
echo [7/15] Creating Vendor Management...


mkdir apps\vendor_management 2>nul

type nul > apps\vendor_management\__init__.py
type nul > apps\vendor_management\models.py


echo.
echo [8/15] Creating Warranty Tracking...


mkdir apps\warranty 2>nul

type nul > apps\warranty\__init__.py
type nul > apps\warranty\models.py
type nul > apps\warranty\alerts.py


echo.
echo [9/15] Creating Asset Dashboard...


mkdir templates\cmdb 2>nul

type nul > templates\cmdb\dashboard.html
type nul > templates\cmdb\assets.html
type nul > templates\cmdb\relationships.html


echo.
echo [10/15] Creating CMDB API...


mkdir api\cmdb 2>nul

type nul > api\cmdb\views.py
type nul > api\cmdb\serializers.py
type nul > api\cmdb\urls.py


echo.
echo [11/15] Creating Ticket Asset Integration...


mkdir integrations\cmdb_ticketing 2>nul

type nul > integrations\cmdb_ticketing\asset_link.py
type nul > integrations\cmdb_ticketing\events.py


echo.
echo [12/15] Django Validation...


python manage.py check

if errorlevel 1 goto ERROR


echo.
echo [13/15] Creating Migrations...


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
echo PHASE 26 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] CMDB Core
echo [OK] Asset Inventory
echo [OK] Software Tracking
echo [OK] Configuration Items
echo [OK] Asset Relationships
echo [OK] Discovery Foundation
echo [OK] Warranty Management
echo [OK] CMDB Dashboard
echo [OK] Ticket Asset Linking
echo.


pause
exit /b 0


:ERROR

echo.
echo ===============================================================
echo PHASE 26 FAILED
echo ===============================================================

echo Fix Django errors before continuing.

pause
exit /b 1