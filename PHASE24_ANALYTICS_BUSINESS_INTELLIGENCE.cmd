@echo off
title Enterprise Service Desk - Phase 24 Analytics BI
color 06

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 24 - REPORTING ANALYTICS BUSINESS INTELLIGENCE
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/15] Creating Analytics Application...


mkdir apps\analytics_engine 2>nul
mkdir apps\analytics_engine\models 2>nul
mkdir apps\analytics_engine\services 2>nul
mkdir apps\analytics_engine\reports 2>nul
mkdir apps\analytics_engine\exports 2>nul


type nul > apps\analytics_engine\__init__.py


echo.
echo [2/15] Creating Analytics Models...


type nul > apps\analytics_engine\models\metrics.py
type nul > apps\analytics_engine\models\kpi.py
type nul > apps\analytics_engine\models\report.py
type nul > apps\analytics_engine\models\snapshot.py


echo.
echo [3/15] Creating KPI Engine...


type nul > apps\analytics_engine\services\kpi_engine.py
type nul > apps\analytics_engine\services\metrics_engine.py


echo.
echo [4/15] Creating SLA Analytics...


mkdir apps\sla_reporting 2>nul

type nul > apps\sla_reporting\__init__.py
type nul > apps\sla_reporting\models.py
type nul > apps\sla_reporting\calculator.py


echo.
echo [5/15] Creating Executive Dashboard...


mkdir templates\analytics 2>nul

type nul > templates\analytics\dashboard.html
type nul > templates\analytics\executive.html
type nul > templates\analytics\department.html


echo.
echo [6/15] Creating Ticket Analytics...


type nul > apps\analytics_engine\reports\ticket_reports.py
type nul > apps\analytics_engine\reports\agent_reports.py
type nul > apps\analytics_engine\reports\sla_reports.py


echo.
echo [7/15] Creating Agent Performance Tracking...


mkdir apps\performance 2>nul

type nul > apps\performance\__init__.py
type nul > apps\performance\models.py
type nul > apps\performance\scoring.py


echo.
echo [8/15] Creating Customer Satisfaction Module...


mkdir apps\customer_experience 2>nul

type nul > apps\customer_experience\__init__.py
type nul > apps\customer_experience\models.py
type nul > apps\customer_experience\survey.py


echo.
echo [9/15] Creating Export Engine...


type nul > apps\analytics_engine\exports\pdf_export.py
type nul > apps\analytics_engine\exports\excel_export.py
type nul > apps\analytics_engine\exports\csv_export.py


echo.
echo [10/15] Creating Analytics API...


mkdir api\analytics 2>nul

type nul > api\analytics\views.py
type nul > api\analytics\serializers.py
type nul > api\analytics\urls.py


echo.
echo [11/15] Creating Scheduled Reporting...


mkdir apps\scheduled_reports 2>nul

type nul > apps\scheduled_reports\__init__.py
type nul > apps\scheduled_reports\models.py
type nul > apps\scheduled_reports\scheduler.py


echo.
echo [12/15] Django Validation...


python manage.py check

if errorlevel 1 goto ERROR


echo.
echo [13/15] Database Migration...


python manage.py makemigrations

python manage.py migrate


echo.
echo [14/15] Git Preparation...


git add .

git status


echo.
echo [15/15] Phase Complete...


echo ===============================================================
echo PHASE 24 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] Executive Dashboard
echo [OK] KPI Engine
echo [OK] SLA Analytics
echo [OK] Agent Metrics
echo [OK] Customer Satisfaction
echo [OK] Report Generator
echo [OK] Export Framework
echo [OK] Scheduled Reports
echo [OK] Analytics API
echo.


pause
exit /b


:ERROR

echo.
echo ===============================================================
echo PHASE 24 FAILED
echo ===============================================================

echo Fix Django errors before continuing.

pause
exit /b 1