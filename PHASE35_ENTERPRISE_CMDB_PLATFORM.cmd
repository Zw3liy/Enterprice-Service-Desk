@echo off
title Enterprise Service Desk - Phase 35 CMDB Platform
color 06

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 35 - CONFIGURATION MANAGEMENT DATABASE
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/16] Creating CMDB Engine...


mkdir apps\cmdb 2>nul
mkdir apps\cmdb\models 2>nul
mkdir apps\cmdb\services 2>nul
mkdir apps\cmdb\relationships 2>nul
mkdir apps\cmdb\analytics 2>nul


type nul > apps\cmdb\__init__.py


echo.
echo [2/16] Creating Configuration Item Models...


type nul > apps\cmdb\models\configuration_item.py
type nul > apps\cmdb\models\ci_type.py
type nul > apps\cmdb\models\ci_status.py
type nul > apps\cmdb\models\ci_attribute.py


echo.
echo [3/16] Creating CI Relationship Engine...


type nul > apps\cmdb\relationships\relationship.py
type nul > apps\cmdb\relationships\dependency.py
type nul > apps\cmdb\relationships\mapping.py


echo.
echo [4/16] Creating Service Mapping Engine...


mkdir apps\service_mapping 2>nul


type nul > apps\service_mapping\__init__.py
type nul > apps\service_mapping\models.py
type nul > apps\service_mapping\mapper.py


echo.
echo [5/16] Creating Infrastructure Graph Engine...


mkdir apps\infrastructure_graph 2>nul


type nul > apps\infrastructure_graph\__init__.py
type nul > apps\infrastructure_graph\graph.py
type nul > apps\infrastructure_graph\nodes.py
type nul > apps\infrastructure_graph\edges.py


echo.
echo [6/16] Creating Ownership Management...


mkdir apps\ownership_management 2>nul


type nul > apps\ownership_management\__init__.py
type nul > apps\ownership_management\models.py
type nul > apps\ownership_management\assignment.py


echo.
echo [7/16] Creating Lifecycle Management...


mkdir apps\asset_lifecycle 2>nul


type nul > apps\asset_lifecycle\__init__.py
type nul > apps\asset_lifecycle\lifecycle.py
type nul > apps\asset_lifecycle\events.py


echo.
echo [8/16] Creating Impact Analysis Engine...


type nul > apps\cmdb\services\impact_analysis.py
type nul > apps\cmdb\services\dependency_analysis.py


echo.
echo [9/16] Creating CMDB Health Engine...


type nul > apps\cmdb\analytics\health_score.py
type nul > apps\cmdb\analytics\quality.py


echo.
echo [10/16] Creating Discovery Synchronization...


mkdir apps\cmdb_sync 2>nul


type nul > apps\cmdb_sync\__init__.py
type nul > apps\cmdb_sync\discovery_import.py
type nul > apps\cmdb_sync\reconciliation.py


echo.
echo [11/16] Creating CMDB Dashboard...


mkdir templates\cmdb 2>nul


type nul > templates\cmdb\dashboard.html
type nul > templates\cmdb\cis.html
type nul > templates\cmdb\relationships.html


echo.
echo [12/16] Creating CMDB API...


mkdir api\cmdb 2>nul


type nul > api\cmdb\views.py
type nul > api\cmdb\serializers.py
type nul > api\cmdb\urls.py


echo.
echo [13/16] Django Validation...


python manage.py check

if errorlevel 1 goto ERROR


echo.
echo [14/16] Creating Migrations...


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
echo PHASE 35 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] CMDB Core
echo [OK] Configuration Items
echo [OK] CI Relationships
echo [OK] Service Mapping
echo [OK] Dependency Graph
echo [OK] Ownership Tracking
echo [OK] Lifecycle Management
echo [OK] Impact Analysis
echo [OK] CMDB Health Scoring
echo [OK] Discovery Synchronization
echo.


pause
exit /b 0


:ERROR

echo.
echo ===============================================================
echo PHASE 35 FAILED
echo ===============================================================

echo Fix Django errors before continuing.

pause
exit /b 1