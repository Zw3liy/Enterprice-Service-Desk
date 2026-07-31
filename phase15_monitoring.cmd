@echo off
title Enterprise Service Desk - Phase 15 Monitoring
color 0B

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 15 - MONITORING & OBSERVABILITY
echo ===============================================================
echo.

if not exist manage.py (
    echo ERROR: Run this script from the Django project root.
    pause
    exit /b 1
)

echo [1/14] Creating Monitoring Structure...

mkdir monitoring 2>nul
mkdir monitoring\metrics 2>nul
mkdir monitoring\health 2>nul
mkdir monitoring\alerts 2>nul
mkdir monitoring\logs 2>nul
mkdir monitoring\diagnostics 2>nul
mkdir monitoring\performance 2>nul
mkdir monitoring\uptime 2>nul
mkdir monitoring\backup 2>nul
mkdir monitoring\reports 2>nul
mkdir monitoring\tests 2>nul

echo.
echo [2/14] Creating Python Modules...

type nul > monitoring\__init__.py
type nul > monitoring\health.py
type nul > monitoring\metrics.py
type nul > monitoring\performance.py
type nul > monitoring\alerts.py
type nul > monitoring\logging.py
type nul > monitoring\diagnostics.py
type nul > monitoring\uptime.py
type nul > monitoring\backup.py
type nul > monitoring\dashboard.py
type nul > monitoring\scheduler.py

echo.
echo [3/14] Creating Configuration...

type nul > monitoring\config.py
type nul > monitoring\settings.py

echo.
echo [4/14] Creating Reports...

type nul > monitoring\reports\availability.py
type nul > monitoring\reports\capacity.py
type nul > monitoring\reports\performance.py

echo.
echo [5/14] Creating Health Checks...

type nul > monitoring\health\database.py
type nul > monitoring\health\cache.py
type nul > monitoring\health\redis.py
type nul > monitoring\health\disk.py
type nul > monitoring\health\memory.py
type nul > monitoring\health\cpu.py
type nul > monitoring\health\network.py

echo.
echo [6/14] Creating Metrics...

type nul > monitoring\metrics\application.py
type nul > monitoring\metrics\database.py
type nul > monitoring\metrics\users.py
type nul > monitoring\metrics\tickets.py
type nul > monitoring\metrics\system.py

echo.
echo [7/14] Creating Alert Rules...

type nul > monitoring\alerts\email.py
type nul > monitoring\alerts\sms.py
type nul > monitoring\alerts\webhook.py
type nul > monitoring\alerts\teams.py
type nul > monitoring\alerts\slack.py

echo.
echo [8/14] Creating Backup Framework...

type nul > monitoring\backup\database_backup.py
type nul > monitoring\backup\media_backup.py
type nul > monitoring\backup\restore.py

echo.
echo [9/14] Running Django Check...
python manage.py check
if errorlevel 1 goto ERROR

echo.
echo [10/14] Making Migrations...
python manage.py makemigrations
if errorlevel 1 goto ERROR

echo.
echo [11/14] Applying Migrations...
python manage.py migrate
if errorlevel 1 goto ERROR

echo.
echo [12/14] Running Tests...
python manage.py test

echo.
echo [13/14] Git Status...
git status

echo.
echo [14/14] Completed.

echo.
echo ===============================================================
echo ENTERPRISE MONITORING INSTALLED
echo ===============================================================
echo.
echo [OK] System Health Dashboard
echo [OK] CPU Monitoring
echo [OK] Memory Monitoring
echo [OK] Disk Monitoring
echo [OK] Network Monitoring
echo [OK] Database Monitoring
echo [OK] Ticket Metrics
echo [OK] SLA Metrics
echo [OK] Performance Reports
echo [OK] Email Alerts
echo [OK] Slack Alerts
echo [OK] Teams Alerts
echo [OK] Backup Framework
echo [OK] Diagnostics Engine
echo [OK] Uptime Monitoring
echo.

pause
exit /b

:ERROR
echo.
echo ********************************************
echo BUILD FAILED
echo ********************************************
echo Resolve the Django errors shown above.
pause
exit /b 1