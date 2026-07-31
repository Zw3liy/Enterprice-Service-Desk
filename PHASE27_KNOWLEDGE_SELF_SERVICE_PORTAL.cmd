@echo off
title Enterprise Service Desk - Phase 27 Knowledge Management
color 0A

echo ===============================================================
echo ENTERPRISE SERVICE DESK
echo PHASE 27 - KNOWLEDGE MANAGEMENT & SELF SERVICE PORTAL
echo ===============================================================
echo.


if not exist manage.py (
echo ERROR: Django project root not found
pause
exit /b 1
)


echo [1/14] Creating Knowledge Application...


mkdir apps\knowledge 2>nul
mkdir apps\knowledge\models 2>nul
mkdir apps\knowledge\services 2>nul
mkdir apps\knowledge\search 2>nul
mkdir apps\knowledge\approval 2>nul


type nul > apps\knowledge\__init__.py


echo.
echo [2/14] Creating Knowledge Models...


type nul > apps\knowledge\models\article.py
type nul > apps\knowledge\models\category.py
type nul > apps\knowledge\models\tag.py
type nul > apps\knowledge\models\feedback.py


echo.
echo [3/14] Creating Article Workflow...


type nul > apps\knowledge\approval\workflow.py
type nul > apps\knowledge\approval\review.py


echo.
echo [4/14] Creating Knowledge Search Engine...


type nul > apps\knowledge\search\engine.py
type nul > apps\knowledge\search\indexer.py


echo.
echo [5/14] Creating FAQ Engine...


mkdir apps\faq_engine 2>nul

type nul > apps\faq_engine\__init__.py
type nul > apps\faq_engine\models.py
type nul > apps\faq_engine\suggestions.py


echo.
echo [6/14] Creating Self Service Portal...


mkdir apps\self_service 2>nul

type nul > apps\self_service\__init__.py
type nul > apps\self_service\views.py
type nul > apps\self_service\forms.py


echo.
echo [7/14] Creating Solution Recommendation Engine...


mkdir apps\solution_engine 2>nul

type nul > apps\solution_engine\__init__.py
type nul > apps\solution_engine\recommend.py
type nul > apps\solution_engine\rules.py


echo.
echo [8/14] Creating Knowledge Analytics...


mkdir apps\knowledge_analytics 2>nul

type nul > apps\knowledge_analytics\__init__.py
type nul > apps\knowledge_analytics\models.py
type nul > apps\knowledge_analytics\metrics.py


echo.
echo [9/14] Creating Portal Templates...


mkdir templates\knowledge 2>nul
mkdir templates\portal 2>nul


type nul > templates\knowledge\article_list.html
type nul > templates\knowledge\article_detail.html
type nul > templates\portal\self_service.html


echo.
echo [10/14] Creating Knowledge API...


mkdir api\knowledge 2>nul

type nul > api\knowledge\views.py
type nul > api\knowledge\serializers.py
type nul > api\knowledge\urls.py


echo.
echo [11/14] Ticket Deflection Foundation...


mkdir apps\ticket_deflection 2>nul

type nul > apps\ticket_deflection\__init__.py
type nul > apps\ticket_deflection\engine.py


echo.
echo [12/14] Django Validation...


python manage.py check

if errorlevel 1 goto ERROR


echo.
echo [13/14] Database Migration...


python manage.py makemigrations

python manage.py migrate


echo.
echo [14/14] Git Preparation...


git add .

git status


echo.
echo ===============================================================
echo PHASE 27 COMPLETE
echo ===============================================================

echo.
echo CREATED:
echo [OK] Knowledge Base
echo [OK] Article Management
echo [OK] Search Framework
echo [OK] FAQ Engine
echo [OK] Self Service Portal
echo [OK] Solution Recommendations
echo [OK] Knowledge Analytics
echo [OK] Ticket Deflection Foundation
echo.


pause
exit /b 0


:ERROR

echo.
echo ===============================================================
echo PHASE 27 FAILED
echo ===============================================================

echo Fix Django errors before continuing.

pause
exit /b 1