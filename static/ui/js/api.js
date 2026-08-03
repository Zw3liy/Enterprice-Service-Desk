/* ==========================================================
   ENTERPRISE UI FRAMEWORK

   api.js

   Enterprise API Client

   Features
   -------------------------------------------------
   • CSRF Support
   • GET
   • POST
   • PUT
   • PATCH
   • DELETE
   • File Upload
   • Query Parameters
   • Automatic JSON Parsing
   • Standard Error Handling
========================================================== */

"use strict";

class APIClient {

    constructor() {

        this.baseURL = "/";

        this.defaultHeaders = {

            "Content-Type": "application/json"

        };

    }

    /* ======================================================
       CSRF TOKEN
    ====================================================== */

    getCSRFToken() {

        const cookie = document.cookie
            .split("; ")
            .find(row => row.startsWith("csrftoken="));

        return cookie
            ? decodeURIComponent(cookie.split("=")[1])
            : "";

    }

    /* ======================================================
       HEADERS
    ====================================================== */

    buildHeaders(extraHeaders = {}) {

        return {

            ...this.defaultHeaders,

            "X-CSRFToken": this.getCSRFToken(),

            ...extraHeaders

        };

    }

    /* ======================================================
       REQUEST
    ====================================================== */

    async request(url, options = {}) {

        const settings = {

            credentials: "same-origin",

            headers: this.buildHeaders(options.headers),

            ...options

        };

        try {

            const response = await fetch(

                this.baseURL + url,

                settings

            );

            const contentType =

                response.headers.get("content-type") || "";

            let data = null;

            if (contentType.includes("application/json")) {

                data = await response.json();

            } else {

                data = await response.text();

            }

            if (!response.ok) {

                throw {

                    status: response.status,

                    data

                };

            }

            return data;

        }

        catch (error) {

            console.error("API Error", error);

            if (

                window.EnterpriseUI?.notifications

            ) {

                EnterpriseUI.notifications.error(

                    "Request failed."

                );

            }

            throw error;

        }

    }

    /* ======================================================
       GET
    ====================================================== */

    get(url) {

        return this.request(

            url,

            {

                method: "GET"

            }

        );

    }

    /* ======================================================
       POST
    ====================================================== */

    post(url, data = {}) {

        return this.request(

            url,

            {

                method: "POST",

                body: JSON.stringify(data)

            }

        );

    }

    /* ======================================================
       PUT
    ====================================================== */

    put(url, data = {}) {

        return this.request(

            url,

            {

                method: "PUT",

                body: JSON.stringify(data)

            }

        );

    }

    /* ======================================================
       PATCH
    ====================================================== */

    patch(url, data = {}) {

        return this.request(

            url,

            {

                method: "PATCH",

                body: JSON.stringify(data)

            }

        );

    }

    /* ======================================================
       DELETE
    ====================================================== */

    delete(url) {

        return this.request(

            url,

            {

                method: "DELETE"

            }

        );

    }

    /* ======================================================
       FILE UPLOAD
    ====================================================== */

    async upload(url, file, field = "file") {

        const form = new FormData();

        form.append(field, file);

        return this.request(

            url,

            {

                method: "POST",

                headers: {

                    "X-CSRFToken":

                        this.getCSRFToken()

                },

                body: form

            }

        );

    }

    /* ======================================================
       QUERY STRING
    ====================================================== */

    buildQuery(params = {}) {

        const query =

            new URLSearchParams(params);

        return query.toString();

    }

}

/* ==========================================================
   INITIALIZE
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    () => {

        const api =

            new APIClient();

        if (

            window.EnterpriseUI

        ) {

            EnterpriseUI.api = api;

        }

        console.log("API Client Ready");

    }

);