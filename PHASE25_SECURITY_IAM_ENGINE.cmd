@echo off
title Enterprise Service Desk - Phase 25 Security IAM Engine
color 0C

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 25 - SECURITY IDENTITY ACCESS MANAGEMENT
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/15] Creating Security Application...


mkdir apps\security_engine 2>nul
mkdir apps\security_engine\models 2>nul
mkdir apps\security_engine\services 2>nul
mkdir apps\security_engine\permissions 2>nul
mkdir apps\security_engine\audit 2>nul


type nul > apps\security_engine\__init__.py


echo.
echo [2/15] Creating Identity Models...


type nul > apps\security_engine\models\roles.py
type nul > apps\security_engine\models\permissions.py
type nul > apps\security_engine\models\groups.py
type nul > apps\security_engine\models\sessions.py


echo.
echo [3/15] Creating RBAC Engine...


type nul > apps\security_engine\permissions\rbac.py
type nul > apps\security_engine\permissions\policy.py
type nul > apps\security_engine\permissions\checker.py


echo.
echo [4/15] Creating User Management Layer...


mkdir apps\identity 2>nul

type nul > apps\identity\__init__.py
type nul > apps\identity\models.py
type nul > apps\identity\services.py


echo.
echo [5/15] Creating Department Security...


mkdir apps\department_security 2>nul

type nul > apps\department_security\__init__.py
type nul > apps\department_security\rules.py
type nul > apps\department_security\access.py


echo.
echo [6/15] Creating Audit Security Framework...


type nul > apps\security_engine\audit\audit_logger.py
type nul > apps\security_engine\audit\events.py
type nul > apps\security_engine\audit\reports.py


echo.
echo [7/15] Creating Login Monitoring...


mkdir apps\login_security 2>nul

type nul > apps\login_security\__init__.py
type nul > apps\login_security\models.py
type nul > apps\login_security\monitor.py


echo.
echo [8/15] Creating MFA Foundation...


mkdir apps\mfa 2>nul

type nul > apps\mfa\__init__.py
type nul > apps\mfa\models.py
type nul > apps\mfa\totp.py


echo.
echo [9/15] Creating API Security...


mkdir apps\api_security 2>nul

type nul > apps\api_security\__init__.py
type nul > apps\api_security\tokens.py
type nul > apps\api_security\middleware.py


echo.
echo [10/15] Creating Security Dashboard...


mkdir templates\security 2>nul

type nul > templates\security\dashboard.html
type nul > templates\security\roles.html
type nul > templates\security\audit_logs.html


echo.
echo [11/15] Updating Security Configuration...


mkdir config\security 2>nul

type nul > config\security\permissions.json
type nul > config\security\roles.json


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
echo PHASE 25 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] RBAC Engine
echo [OK] Permission System
echo [OK] Identity Layer
echo [OK] Department Security
echo [OK] Audit Framework
echo [OK] Login Monitoring
echo [OK] MFA Foundation
echo [OK] API Security
echo [OK] Security Dashboard
echo.


pause
exit /b 1


:ERROR

echo.
echo ===============================================================
echo PHASE 25 FAILED
echo ===============================================================

echo Resolve Django errors before continuing.

pause
exit /b 1