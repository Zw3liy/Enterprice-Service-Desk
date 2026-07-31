"""
====================================================
Phase 6 - Service Desk Application Layer Bootstrap
Enterprise Service Desk Platform
====================================================
"""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


APP_DIR = BASE_DIR / "apps" / "service_desk"


def create_file(path, content):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not path.exists():

        path.write_text(
            content,
            encoding="utf-8"
        )

        print(f"[+] Created {path}")

    else:

        print(f"[SKIP] Exists {path}")


def main():

    print("")
    print("=" * 60)
    print(" Phase 6 - Service Desk Application Layer")
    print("=" * 60)
    print("")


    # ---------------------------------------
    # Templates
    # ---------------------------------------

    dashboard_html = """

<!DOCTYPE html>
<html>

<head>

<title>
Enterprise Service Desk
</title>


<style>

body {

font-family: Arial;
background:#f4f6f8;
padding:40px;

}


.container {

background:white;
padding:30px;
border-radius:10px;

box-shadow:
0 3px 10px rgba(0,0,0,.15);

}


</style>


</head>


<body>


<div class="container">


<h1>
Enterprise Service Desk
</h1>


<p>
IT Support Management Platform
</p>


<hr>


<h2>
Operations
</h2>


<ul>

<li>
Create Ticket
</li>


<li>
Ticket Queue
</li>


<li>
SLA Monitoring
</li>


<li>
Knowledge Base
</li>


</ul>


</div>


</body>

</html>

"""


    create_file(
        APP_DIR /
        "templates" /
        "service_desk" /
        "dashboard.html",
        dashboard_html
    )


    # ---------------------------------------
    # Views
    # ---------------------------------------

    views = """

from django.shortcuts import render



def dashboard(request):

    return render(
        request,
        "service_desk/dashboard.html"
    )

"""

    create_file(
        APP_DIR / "views.py",
        views
    )


    # ---------------------------------------
    # URLs
    # ---------------------------------------

    urls = """

from django.urls import path

from . import views



urlpatterns = [


    path(
        "",
        views.dashboard,
        name="dashboard"
    ),


]

"""

    create_file(
        APP_DIR / "urls.py",
        urls
    )


    # ---------------------------------------
    # Static folders
    # ---------------------------------------

    folders = [

        APP_DIR / "static" / "service_desk" / "css",

        APP_DIR / "static" / "service_desk" / "js",

        APP_DIR / "static" / "service_desk" / "images",

    ]


    for folder in folders:

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        print(
            f"[+] Folder ready {folder}"
        )


    # ---------------------------------------
    # Project URL
    # ---------------------------------------

    project_urls = BASE_DIR / "ticketing" / "urls.py"


    if project_urls.exists():

        content = project_urls.read_text(
            encoding="utf-8"
        )


        if "apps.service_desk.urls" not in content:


            content = """

from django.contrib import admin

from django.urls import path, include



urlpatterns = [

path(
"admin/",
admin.site.urls
),


path(
"",
include("apps.service_desk.urls")
),


]

"""


            project_urls.write_text(
                content,
                encoding="utf-8"
            )


            print(
                "[+] Updated project URLs"
            )


        else:

            print(
                "[SKIP] URLs already connected"
            )


    print("")
    print("=" * 60)
    print(" Phase 6 Foundation Completed")
    print("=" * 60)
    print("")


if __name__ == "__main__":

    main()