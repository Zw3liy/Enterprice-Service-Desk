@echo off
title Enterprise Service Desk - Phase 1 UI Foundation
color 0A

echo ==========================================
echo ENTERPRISE SERVICE DESK
echo PHASE 1 - UI FOUNDATION
echo ==========================================

cd /d "%~dp0"

echo Creating frontend directories...

mkdir templates\layouts 2>nul
mkdir templates\components 2>nul
mkdir templates\dashboard 2>nul

mkdir static\css 2>nul
mkdir static\js 2>nul
mkdir static\images 2>nul


echo Creating base template...


(
echo ^<!DOCTYPE html^>
echo ^<html lang="en"^>
echo ^<head^>
echo ^<meta charset="UTF-8"^>
echo ^<meta name="viewport" content="width=device-width, initial-scale=1.0"^>
echo ^<title^>{% block title %}Enterprise Service Desk{% endblock %}^</title^>
echo.
echo ^<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"^>
echo ^<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css" rel="stylesheet"^>
echo ^<link href="/static/css/enterprise.css" rel="stylesheet"^>
echo.
echo ^</head^>
echo.
echo ^<body^>
echo.
echo ^<div class="app-container"^>
echo.
echo {% include "components/sidebar.html" %}
echo.
echo ^<div class="main-area"^>
echo.
echo {% include "components/navbar.html" %}
echo.
echo ^<main class="content-area"^>
echo.
echo {% block content %}
echo {% endblock %}
echo.
echo ^</main^>
echo.
echo {% include "components/footer.html" %}
echo.
echo ^</div^>
echo.
echo ^</div^>
echo.
echo ^<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"^>^</script^>
echo ^<script src="/static/js/dashboard.js"^>^</script^>
echo.
echo ^</body^>
echo ^</html^>
) > templates\layouts\base.html


echo Creating sidebar...


(
echo ^<aside class="sidebar"^>
echo.
echo ^<div class="brand"^>
echo ^<i class="fa-solid fa-headset"^>^</i^>
echo ^<span^>Enterprise Desk^</span^>
echo ^</div^>
echo.
echo ^<ul class="menu"^>
echo.
echo ^<li^>^<a href="#"^>^<i class="fa fa-dashboard"^>^</i^> Dashboard^</a^>^</li^>
echo ^<li^>^<a href="#"^>^<i class="fa fa-ticket"^>^</i^> Tickets^</a^>^</li^>
echo ^<li^>^<a href="#"^>^<i class="fa fa-triangle-exclamation"^>^</i^> Incidents^</a^>^</li^>
echo ^<li^>^<a href="#"^>^<i class="fa fa-server"^>^</i^> CMDB^</a^>^</li^>
echo ^<li^>^<a href="#"^>^<i class="fa fa-book"^>^</i^> Knowledge Base^</a^>^</li^>
echo ^<li^>^<a href="#"^>^<i class="fa fa-chart-line"^>^</i^> Reports^</a^>^</li^>
echo ^<li^>^<a href="#"^>^<i class="fa fa-robot"^>^</i^> AI Assistant^</a^>^</li^>
echo ^<li^>^<a href="#"^>^<i class="fa fa-users"^>^</i^> Administration^</a^>^</li^>
echo.
echo ^</ul^>
echo.
echo ^</aside^>
) > templates\components\sidebar.html


echo PART 1 COMPLETE
echo Continue with PART 2
pause