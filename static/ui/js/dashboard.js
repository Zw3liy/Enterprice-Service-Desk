/* ==========================================================
   ENTERPRISE UI FRAMEWORK

   dashboard.js

   Dashboard Manager
========================================================== */

"use strict";

class DashboardManager {

    constructor() {

        this.widgets = {};

        this.refreshInterval = null;

        this.refreshTime = 30000;

    }

    /* ======================================================
       INITIALIZATION
    ====================================================== */

    init() {

        console.log("Dashboard Manager Ready");

        this.registerEvents();

        this.discoverWidgets();

    }

    /* ======================================================
       EVENTS
    ====================================================== */

    registerEvents() {

        document
            .querySelectorAll("[data-dashboard-refresh]")
            .forEach(button => {

                button.addEventListener("click", () => {

                    this.refresh();

                });

            });

        document
            .querySelectorAll("[data-dashboard-filter]")
            .forEach(filter => {

                filter.addEventListener("change", () => {

                    this.refresh();

                });

            });

    }

    /* ======================================================
       DISCOVER WIDGETS
    ====================================================== */

    discoverWidgets() {

        document
            .querySelectorAll("[data-widget]")
            .forEach(widget => {

                const name =

                    widget.dataset.widget;

                this.widgets[name] = widget;

            });

    }

    /* ======================================================
       REGISTER
    ====================================================== */

    register(name, callback) {

        this.widgets[name] = callback;

    }

    /* ======================================================
       REFRESH
    ====================================================== */

    refresh() {

        console.log("Refreshing Dashboard");

        Object.values(this.widgets).forEach(widget => {

            if (typeof widget === "function") {

                widget();

            }

        });

    }

    /* ======================================================
       AUTO REFRESH
    ====================================================== */

    startAutoRefresh(seconds = 30) {

        this.stopAutoRefresh();

        this.refreshTime = seconds * 1000;

        this.refreshInterval =

            setInterval(() => {

                this.refresh();

            }, this.refreshTime);

    }

    stopAutoRefresh() {

        if (this.refreshInterval) {

            clearInterval(

                this.refreshInterval

            );

        }

    }

    /* ======================================================
       KPI UPDATE
    ====================================================== */

    updateKPI(id, value) {

        const card =

            document.getElementById(id);

        if (!card) {

            return;

        }

        card.textContent = value;

    }

    /* ======================================================
       UPDATE TEXT
    ====================================================== */

    update(id, value) {

        const element =

            document.getElementById(id);

        if (!element) {

            return;

        }

        element.innerHTML = value;

    }

    /* ======================================================
       LOADING
    ====================================================== */

    loading(show = true) {

        document
            .querySelectorAll("[data-dashboard-loading]")
            .forEach(loader => {

                loader.style.display =

                    show ? "flex" : "none";

            });

    }

    /* ======================================================
       LOAD JSON
    ====================================================== */

    async load(url) {

        if (

            !window.EnterpriseUI

        ) {

            return;

        }

        this.loading(true);

        try {

            const data =

                await EnterpriseUI.get(url);

            this.loading(false);

            return data;

        }

        catch (error) {

            this.loading(false);

            EnterpriseUI.notifications.error(

                "Unable to load dashboard."

            );

        }

    }

    /* ======================================================
       FILTERS
    ====================================================== */

    getFilters() {

        const filters = {};

        document
            .querySelectorAll("[data-dashboard-filter]")
            .forEach(control => {

                filters[control.name] =

                    control.value;

            });

        return filters;

    }

}

/* ==========================================================
   INITIALIZE
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    () => {

        const dashboard =

            new DashboardManager();

        dashboard.init();

        if (window.EnterpriseUI) {

            EnterpriseUI.dashboard = dashboard;

        }

    }

);