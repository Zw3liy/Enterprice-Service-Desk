@echo off
title Enterprise Service Desk - Phase 2 Status Generator
color 0A

echo ===========================================
echo Enterprise Service Desk
echo Add Ticket Status Migration
echo ===========================================
echo.

cd /d "%~dp0"

if not exist manage.py (
    echo ERROR: manage.py not found.
    pause
    exit /b
)

echo Creating migrations...
python manage.py makemigrations service_desk

if errorlevel 1 (
    echo.
    echo Migration generation failed.
    pause
    exit /b
)

echo.
echo Applying migrations...
python manage.py migrate

if errorlevel 1 (
    echo.
    echo Migration failed.
    pause
    exit /b
)

echo.
echo ===========================================
echo Status migration completed successfully.
echo ===========================================
pause