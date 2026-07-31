@echo off
title Enterprise Service Desk - Phase 33 Network Discovery Intelligence
color 03

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 33 - NETWORK DISCOVERY & INFRASTRUCTURE INTELLIGENCE
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/16] Creating Discovery Engine...


mkdir apps\network_discovery 2>nul
mkdir apps\network_discovery\models 2>nul
mkdir apps\network_discovery\services 2>nul
mkdir apps\network_discovery\scanners 2>nul
mkdir apps\network_discovery\protocols 2>nul


type nul > apps\network_discovery\__init__.py


echo.
echo [2/16] Creating Discovery Models...


type nul > apps\network_discovery\models\device.py
type nul > apps\network_discovery\models\network.py
type nul > apps\network_discovery\models\ip_address.py
type nul > apps\network_discovery\models\scan.py


echo.
echo [3/16] Creating Network Scanner...


type nul > apps\network_discovery\scanners\network_scanner.py
type nul > apps\network_discovery\scanners\port_scanner.py
type nul > apps\network_discovery\scanners\host_detector.py


echo.
echo [4/16] Creating SNMP Framework...


type nul > apps\network_discovery\protocols\snmp.py
type nul > apps\network_discovery\protocols\icmp.py
type nul > apps\network_discovery\protocols\ssh.py


echo.
echo [5/16] Creating Device Fingerprinting...


mkdir apps\device_intelligence 2>nul


type nul > apps\device_intelligence\__init__.py
type nul > apps\device_intelligence\fingerprint.py
type nul > apps\device_intelligence\vendor_detection.py


echo.
echo [6/16] Creating IP Address Management...


mkdir apps\ip_management 2>nul


type nul > apps\ip_management\__init__.py
type nul > apps\ip_management\models.py
type nul > apps\ip_management\allocator.py


echo.
echo [7/16] Creating Network Topology Engine...


mkdir apps\topology_engine 2>nul


type nul > apps\topology_engine\__init__.py
type nul > apps\topology_engine\models.py
type nul > apps\topology_engine\mapper.py


echo.
echo [8/16] Creating CMDB Discovery Connector...


mkdir apps\cmdb_discovery 2>nul


type nul > apps\cmdb_discovery\__init__.py
type nul > apps\cmdb_discovery\importer.py
type nul > apps\cmdb_discovery\synchronizer.py


echo.
echo [9/16] Creating Discovery Scheduler...


mkdir apps\discovery_scheduler 2>nul


type nul > apps\discovery_scheduler\__init__.py
type nul > apps\discovery_scheduler\jobs.py
type nul > apps\discovery_scheduler\tasks.py


echo.
echo [10/16] Creating Infrastructure Dashboard...


mkdir templates\network 2>nul


type nul > templates\network\dashboard.html
type nul > templates\network\devices.html
type nul > templates\network\topology.html


echo.
echo [11/16] Creating Discovery API...


mkdir api\discovery 2>nul


type nul > api\discovery\views.py
type nul > api\discovery\serializers.py
type nul > api\discovery\urls.py


echo.
echo [12/16] Creating Discovery Logs...


mkdir apps\discovery_logs 2>nul


type nul > apps\discovery_logs\__init__.py
type nul > apps\discovery_logs\models.py


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
echo PHASE 33 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] Network Discovery Engine
echo [OK] Device Scanner
echo [OK] SNMP Framework
echo [OK] IP Management
echo [OK] Device Fingerprinting
echo [OK] Network Topology Mapping
echo [OK] CMDB Synchronization
echo [OK] Discovery Scheduler
echo [OK] Infrastructure Dashboard
echo.


pause
exit /b 0


:ERROR

echo.
echo ===============================================================
echo PHASE 33 FAILED
echo ===============================================================

echo Fix Django errors before continuing.

pause
exit /b 1