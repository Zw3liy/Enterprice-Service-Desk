@echo off
title Enterprise Service Desk - Master Bootstrap
color 0A

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo MASTER BOOTSTRAP AND AUTO REPAIR SYSTEM
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR:
echo Django project root not detected.
pause
exit /b 1
)


echo.
echo [1/15] Activating Virtual Environment...


if exist ..\..\venv\Scripts\activate.bat (
call ..\..\venv\Scripts\activate.bat
)


echo.
echo [2/15] Checking Python...


python --version


echo.
echo [3/15] Installing Requirements...


if exist requirements.txt (
pip install -r requirements.txt
) else (
echo No requirements.txt found.
)


echo.
echo [4/15] Django System Check...


python manage.py check

if errorlevel 1 goto ERROR


echo.
echo [5/15] Creating Missing Migrations...


python manage.py makemigrations


echo.
echo [6/15] Applying Database...


python manage.py migrate


echo.
echo [7/15] Collecting Static Files...


python manage.py collectstatic --noinput


echo.
echo [8/15] Checking Application Modules...


python -c "import django; print('Django OK')"


echo.
echo [9/15] Creating Required Directories...


mkdir logs 2>nul
mkdir media 2>nul
mkdir staticfiles 2>nul


echo.
echo [10/15] Loading Enterprise Demo Data...


if exist apps\service_desk\management\commands\setup_phase2_schema.py (

python manage.py setup_phase2_schema

) else (

echo No schema loader detected.

)


echo.
echo [11/15] Checking Database Integrity...


python manage.py check --database default


echo.
echo [12/15] Git Repository Preparation...


git add .

git status


echo.
echo [13/15] Creating Startup Shortcut...


(
echo @echo off
echo call venv\Scripts\activate
echo python manage.py runserver
)>START_SERVICE_DESK.cmd


echo.
echo [14/15] System Verification...


python manage.py showmigrations


echo.
echo [15/15] Starting Enterprise Service Desk...


echo.
echo ===============================================================
echo MASTER BOOTSTRAP COMPLETE
echo ===============================================================

echo.
echo START APPLICATION:
echo.
echo START_SERVICE_DESK.cmd
echo.
echo OR:
echo python manage.py runserver
echo.


pause

python manage.py runserver

exit /b



:ERROR

echo.
echo ===============================================================
echo BOOTSTRAP FAILED
echo ===============================================================
echo Review Django errors above.

pause

exit /b 1