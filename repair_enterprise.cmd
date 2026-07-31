@echo off
title Enterprise Service Desk Repair
color 0A

echo ============================================
echo Enterprise Service Desk Repair Utility
echo ============================================
echo.

cd /d "%~dp0"

if not exist manage.py (
    echo ERROR: manage.py not found.
    pause
    exit /b 1
)

if exist "..\..\venv\Scripts\activate.bat" (
    call "..\..\venv\Scripts\activate.bat"
)

echo.
echo [1/8] Checking Django...
python manage.py check
if errorlevel 1 goto failed

echo.
echo [2/8] Creating migrations...
python manage.py makemigrations
if errorlevel 1 goto failed

echo.
echo [3/8] Applying migrations...
python manage.py migrate
if errorlevel 1 goto failed

echo.
echo [4/8] Collecting static files...
python manage.py collectstatic --noinput

echo.
echo [5/8] Seeding Phase 2...
python manage.py setup_phase2_schema

echo.
echo [6/8] Checking project...
python manage.py check
if errorlevel 1 goto failed

echo.
echo [7/8] Running tests...
python manage.py test

echo.
echo [8/8] Starting server...
python manage.py runserver 8001

goto end

:failed
echo.
echo ********************************************
echo PROJECT CONTAINS PYTHON ERRORS
echo ********************************************
echo.
echo Fix the Python errors shown above.
pause

:end
pause