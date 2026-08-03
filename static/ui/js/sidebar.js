/* ==========================================================
   ENTERPRISE UI FRAMEWORK

   sidebar.js

   Enterprise Sidebar Manager

   Features
   ------------------------------------
   - SidebarManager Class
   - Desktop Collapse
   - Mobile Toggle
   - Overlay
   - Active Navigation
   - Keyboard Support
   - State Persistence
   - Responsive Handling
========================================================== */

"use strict";

class SidebarManager {

    constructor() {

        this.sidebar =
            document.querySelector(".sidebar");

        this.toggleButtons =
            document.querySelectorAll("[data-sidebar-toggle]");

        this.overlay =
            document.querySelector(".sidebar-overlay");

        this.storageKey =
            "enterprise-sidebar-collapsed";

        this.mobileWidth = 992;

    }


    /* ======================================================
       INITIALIZATION
    ====================================================== */

    init() {

        if (!this.sidebar) {

            console.warn("Sidebar not found.");

            return;

        }

        this.restoreState();

        this.registerEvents();

        this.setActiveNavigation();

        this.handleResize();

        console.log("Sidebar initialized.");

    }


    /* ======================================================
       EVENTS
    ====================================================== */

    registerEvents() {

        this.toggleButtons.forEach(button => {

            button.addEventListener("click", () => {

                if (window.innerWidth <= this.mobileWidth) {

                    this.toggleMobile();

                }

                else {

                    this.toggleDesktop();

                }

            });

        });


        if (this.overlay) {

            this.overlay.addEventListener(

                "click",

                () => this.closeMobile()

            );

        }


        document.addEventListener(

            "keydown",

            (event) => {

                if (

                    event.key === "Escape"

                ) {

                    this.closeMobile();

                }

            }

        );


        window.addEventListener(

            "resize",

            () => this.handleResize()

        );

    }


    /* ======================================================
       DESKTOP
    ====================================================== */

    toggleDesktop() {

        this.sidebar.classList.toggle(

            "collapsed"

        );

        this.saveState();

    }


    /* ======================================================
       MOBILE
    ====================================================== */

    toggleMobile() {

        this.sidebar.classList.toggle(

            "show"

        );

        if (this.overlay) {

            this.overlay.classList.toggle(

                "show"

            );

        }

    }


    closeMobile() {

        this.sidebar.classList.remove(

            "show"

        );

        if (this.overlay) {

            this.overlay.classList.remove(

                "show"

            );

        }

    }


    /* ======================================================
       RESPONSIVE
    ====================================================== */

    handleResize() {

        if (

            window.innerWidth >

            this.mobileWidth

        ) {

            this.closeMobile();

        }

    }


    /* ======================================================
       STATE
    ====================================================== */

    saveState() {

        localStorage.setItem(

            this.storageKey,

            this.sidebar.classList.contains(

                "collapsed"

            )

        );

    }


    restoreState() {

        const collapsed =

            localStorage.getItem(

                this.storageKey

            );

        if (

            collapsed === "true"

        ) {

            this.sidebar.classList.add(

                "collapsed"

            );

        }

    }


    /* ======================================================
       ACTIVE NAVIGATION
    ====================================================== */

    setActiveNavigation() {

        const current =

            window.location.pathname;

        const links =

            this.sidebar.querySelectorAll("a");

        links.forEach(link => {

            const href =

                link.getAttribute("href");

            if (

                href === current

            ) {

                link.classList.add(

                    "active"

                );

            }

        });

    }


}


/* ==========================================================
   INITIALIZE
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    () => {

        const sidebar =

            new SidebarManager();

        sidebar.init();

        if (

            window.EnterpriseUI

        ) {

            EnterpriseUI.sidebar =

                sidebar;

        }

    }

);