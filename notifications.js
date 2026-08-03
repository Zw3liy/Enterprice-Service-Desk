/* ==========================================================
   ENTERPRISE UI FRAMEWORK

   notifications.js

   Enterprise Notification Manager

   Features
   -------------------------------------------------
   • Success
   • Error
   • Warning
   • Info
   • Auto Dismiss
   • Progress Bar
   • Manual Close
   • Notification Queue
   • EnterpriseUI Integration
========================================================== */

"use strict";

class NotificationManager {

    constructor() {

        this.container = null;

        this.defaultDuration = 5000;

        this.position = "top-right";

    }

    /* ======================================================
       INITIALIZATION
    ====================================================== */

    init() {

        this.createContainer();

        console.log("Notification Manager Ready");

    }

    /* ======================================================
       CONTAINER
    ====================================================== */

    createContainer() {

        let container = document.getElementById(
            "enterprise-notifications"
        );

        if (!container) {

            container = document.createElement("div");

            container.id =
                "enterprise-notifications";

            container.className =
                "notification-container";

            document.body.appendChild(container);

        }

        this.container = container;

    }

    /* ======================================================
       CREATE
    ====================================================== */

    notify(type, title, message, duration = null) {

        if (!this.container) {

            this.createContainer();

        }

        const timeout =

            duration || this.defaultDuration;

        const notification =

            document.createElement("div");

        notification.className =

            `notification notification-${type}`;

        notification.innerHTML = `

<div class="notification-header">

    <strong>${title}</strong>

    <button
        class="notification-close">

        &times;

    </button>

</div>

<div class="notification-body">

    ${message}

</div>

<div class="notification-progress"></div>

`;

        this.container.appendChild(notification);

        const closeButton =

            notification.querySelector(

                ".notification-close"

            );

        closeButton.addEventListener(

            "click",

            () => this.remove(notification)

        );

        const progress =

            notification.querySelector(

                ".notification-progress"

            );

        progress.style.transition =

            `width ${timeout}ms linear`;

        requestAnimationFrame(() => {

            progress.style.width = "0%";

        });

        setTimeout(() => {

            this.remove(notification);

        }, timeout);

    }

    /* ======================================================
       REMOVE
    ====================================================== */

    remove(notification) {

        if (!notification) {

            return;

        }

        notification.classList.add(

            "notification-hide"

        );

        setTimeout(() => {

            notification.remove();

        }, 300);

    }

    /* ======================================================
       SUCCESS
    ====================================================== */

    success(message, title = "Success") {

        this.notify(

            "success",

            title,

            message

        );

    }

    /* ======================================================
       ERROR
    ====================================================== */

    error(message, title = "Error") {

        this.notify(

            "error",

            title,

            message

        );

    }

    /* ======================================================
       WARNING
    ====================================================== */

    warning(message, title = "Warning") {

        this.notify(

            "warning",

            title,

            message

        );

    }

    /* ======================================================
       INFO
    ====================================================== */

    info(message, title = "Information") {

        this.notify(

            "info",

            title,

            message

        );

    }

}


/* ==========================================================
   INITIALIZE
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    () => {

        const notifications =

            new NotificationManager();

        notifications.init();

        if (window.EnterpriseUI) {

            EnterpriseUI.notifications =

                notifications;

        }

    }

);