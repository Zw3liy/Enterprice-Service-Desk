@echo off
title Enterprise Service Desk UI Framework Generator
color 0A

echo.
echo ================================================
echo    ENTERPRISE SERVICE DESK UI GENERATOR
echo ================================================
echo.

if not exist manage.py (
    echo ERROR: Run this script from the folder containing manage.py
    pause
    exit /b
)

echo Creating directories...

mkdir static 2>nul
mkdir static\css 2>nul
mkdir static\js 2>nul
mkdir static\images 2>nul
mkdir static\fonts 2>nul
mkdir static\icons 2>nul

mkdir templates 2>nul
mkdir templates\components 2>nul
mkdir templates\dashboard 2>nul
mkdir templates\tickets 2>nul
mkdir templates\knowledge 2>nul
mkdir templates\reports 2>nul
mkdir templates\settings 2>nul
mkdir templates\authentication 2>nul

echo.

echo Creating CSS files...

type nul > static\css\variables.css
type nul > static\css\reset.css
type nul > static\css\typography.css
type nul > static\css\layout.css
type nul > static\css\navigation.css
type nul > static\css\dashboard.css
type nul > static\css\forms.css
type nul > static\css\tables.css
type nul > static\css\buttons.css
type nul > static\css\cards.css
type nul > static\css\modals.css
type nul > static\css\timeline.css
type nul > static\css\ticket.css
type nul > static\css\reports.css
type nul > static\css\dark-theme.css
type nul > static\css\responsive.css
type nul > static\css\main.css

echo Creating JavaScript files...

type nul > static\js\app.js
type nul > static\js\dashboard.js
type nul > static\js\sidebar.js
type nul > static\js\forms.js
type nul > static\js\tables.js
type nul > static\js\notifications.js
type nul > static\js\charts.js

echo Creating template files...

type nul > templates\base.html
type nul > templates\components\navbar.html
type nul > templates\components\sidebar.html
type nul > templates\components\footer.html
type nul > templates\components\alerts.html
type nul > templates\components\breadcrumbs.html

type nul > templates\dashboard\dashboard.html
type nul > templates\tickets\list.html
type nul > templates\tickets\detail.html
type nul > templates\tickets\create.html

type nul > templates\knowledge\index.html
type nul > templates\reports\dashboard.html
type nul > templates\settings\index.html

echo.

echo ================================================
echo Framework generated successfully.
echo ================================================

echo.
echo Folder Structure:
echo.
tree static /f
echo.
tree templates /f

echo.
echo NEXT STEP:
echo We will generate the Enterprise CSS Framework
echo (approximately 5,000-8,000 lines)
echo with responsive layouts, dashboards,
echo cards, forms, tables, navigation,
echo animations, themes and widgets.

pause