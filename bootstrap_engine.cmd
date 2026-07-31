@echo off
title Enterprise Service Desk Bootstrap
color 0A

echo ============================================================
echo   ENTERPRISE SERVICE DESK - ENGINE BOOTSTRAP
echo ============================================================
echo.

REM Go to project folder
cd /d %~dp0

echo Creating Engineering Framework...

mkdir engine 2>nul
mkdir engine\generators 2>nul
mkdir engine\templates 2>nul
mkdir reports 2>nul
mkdir logs 2>nul
mkdir docs 2>nul
mkdir backups 2>nul

echo.

echo Creating Python packages...

type nul > engine\__init__.py
type nul > engine\builder.py
type nul > engine\validator.py
type nul > engine\generator.py
type nul > engine\migration_manager.py
type nul > engine\dependency_checker.py
type nul > engine\syntax_checker.py
type nul > engine\template_engine.py
type nul > engine\report_generator.py
type nul > engine\config.py

type nul > engine\generators\__init__.py
type nul > engine\generators\models_generator.py
type nul > engine\generators\admin_generator.py
type nul > engine\generators\views_generator.py
type nul > engine\generators\urls_generator.py
type nul > engine\generators\forms_generator.py
type nul > engine\generators\api_generator.py
type nul > engine\generators\template_generator.py
type nul > engine\generators\tests_generator.py

echo.

echo Creating build scripts...

(
echo import subprocess
echo print("=" * 60^)
echo print("Enterprise Service Desk Builder"^)
echo print("=" * 60^)
echo subprocess.run(["python","manage.py","check"]^)
echo subprocess.run(["python","manage.py","makemigrations"]^)
echo subprocess.run(["python","manage.py","migrate"]^)
echo subprocess.run(["python","manage.py","runserver"]^)
) > build.py

(
echo import subprocess
echo print("=" * 60^)
echo print("Validation Report"^)
echo print("=" * 60^)
echo subprocess.run(["python","manage.py","check"]^)
echo subprocess.run(["python","-m","compileall","."]^)
) > validate.py

echo.

echo Creating report files...

type nul > reports\Build_Report.txt
type nul > reports\Validation_Report.txt
type nul > reports\Migration_Report.txt
type nul > reports\Security_Report.txt

echo.

echo ============================================================
echo Bootstrap Complete
echo ============================================================
echo.
echo Next Commands:
echo.
echo python validate.py
echo python build.py
echo.
pause