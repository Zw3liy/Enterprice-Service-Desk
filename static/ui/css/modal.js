/* ==========================================================
   ENTERPRISE UI FRAMEWORK

   modal.js

   Enterprise Modal Manager
========================================================== */

"use strict";

class ModalManager {

    constructor() {

        this.activeModal = null;

        this.defaultTitle = "Enterprise Service Desk";

    }


    /* ======================================================
       INITIALIZATION
    ====================================================== */

    init() {

        this.registerGlobalEvents();

        console.log("Modal Manager Ready");

    }


    /* ======================================================
       EVENTS
    ====================================================== */

    registerGlobalEvents() {

        document.addEventListener("click", (event) => {

            const closeButton =
                event.target.closest("[data-modal-close]");

            if (closeButton) {

                this.close();

            }

        });


        document.addEventListener("keydown", (event) => {

            if (event.key === "Escape") {

                this.close();

            }

        });

    }


    /* ======================================================
       CREATE
    ====================================================== */

    create(options = {}) {

        this.close();

        const overlay = document.createElement("div");

        overlay.className = "modal-overlay";

        overlay.innerHTML = `

<div class="modal">

    <div class="modal-header">

        <h3>

            ${options.title || this.defaultTitle}

        </h3>

        <button
            class="btn btn-light"
            data-modal-close>

            ✕

        </button>

    </div>

    <div class="modal-body">

        ${options.body || ""}

    </div>

    <div class="modal-footer">

        ${options.footer || ""}

    </div>

</div>

`;

        document.body.appendChild(overlay);

        overlay.addEventListener("click", (event) => {

            if (event.target === overlay) {

                this.close();

            }

        });

        this.activeModal = overlay;

        return overlay;

    }


    /* ======================================================
       OPEN
    ====================================================== */

    open(options = {}) {

        this.create(options);

    }


    /* ======================================================
       CLOSE
    ====================================================== */

    close() {

        if (this.activeModal) {

            this.activeModal.remove();

            this.activeModal = null;

        }

    }


    /* ======================================================
       ALERT
    ====================================================== */

    alert(message, title = "Information") {

        this.open({

            title,

            body: `

<p>${message}</p>

`,

            footer: `

<button
class="btn btn-primary"
data-modal-close>

OK

</button>

`

        });

    }


    /* ======================================================
       CONFIRM
    ====================================================== */

    confirm(message, callback) {

        this.open({

            title: "Confirmation",

            body: `

<p>${message}</p>

`,

            footer: `

<button
class="btn btn-secondary"
data-modal-close>

Cancel

</button>

<button
class="btn btn-primary"
id="modalConfirmButton">

Confirm

</button>

`

        });

        const button =

            document.getElementById(

                "modalConfirmButton"

            );

        if (button) {

            button.addEventListener("click", () => {

                this.close();

                if (typeof callback === "function") {

                    callback();

                }

            });

        }

    }


    /* ======================================================
       LOADING
    ====================================================== */

    loading(message = "Loading...") {

        this.open({

            title: "Please Wait",

            body: `

<div class="loading">

    <div class="spinner"></div>

</div>

<p style="text-align:center;">

${message}

</p>

`

        });

    }


    /* ======================================================
       FORM
    ====================================================== */

    form(options = {}) {

        this.open({

            title: options.title || "Form",

            body: options.body || "",

            footer:

                options.footer ||

                `

<button
class="btn btn-secondary"
data-modal-close>

Cancel

</button>

<button
class="btn btn-primary">

Save

</button>

`

        });

    }

}


/* ==========================================================
   INITIALIZE
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    () => {

        const modal =

            new ModalManager();

        modal.init();

        if (window.EnterpriseUI) {

            EnterpriseUI.modal = modal;

        }

    }

);