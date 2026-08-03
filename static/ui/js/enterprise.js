/* ==========================================================
   ENTERPRISE UI FRAMEWORK

   enterprise.js

   Core Frontend Controller

   Features:
   - UI Initialization
   - Global Event Handling
   - CSRF Support
   - AJAX Helpers
   - Theme Switching
   - Component Loading
   - Utility Functions
========================================================== */


"use strict";


/* ==========================================================
   ENTERPRISE APPLICATION OBJECT
========================================================== */

const EnterpriseUI = {


    config: {

        apiBase: "/",

        themeKey: "enterprise-theme",

        debug: true

    },



    /* ======================================================
       INITIALIZATION
    ====================================================== */

    init(){

        this.log("Enterprise UI Initializing...");


        this.loadTheme();


        this.registerEvents();


        this.initializeComponents();


        this.log("Enterprise UI Ready.");

    },



    /* ======================================================
       LOGGING
    ====================================================== */

    log(message, data=null){

        if(this.config.debug){

            console.log(

                "[Enterprise UI]",

                message,

                data || ""

            );

        }

    },



    /* ======================================================
       GLOBAL EVENTS
    ====================================================== */

    registerEvents(){


        document.addEventListener(

            "DOMContentLoaded",

            () => {

                this.initializeComponents();

            }

        );



        document.addEventListener(

            "click",

            (event)=>{


                const themeButton =

                event.target.closest(
                    "[data-theme-toggle]"
                );


                if(themeButton){

                    this.toggleTheme();

                }



                const loader =

                event.target.closest(
                    "[data-loading]"
                );


                if(loader){

                    this.showLoading(loader);

                }


            }

        );

    },



    /* ======================================================
       COMPONENT INITIALIZER
    ====================================================== */

    initializeComponents(){


        this.log(

            "Loading UI Components"

        );


        document.querySelectorAll(

            "[data-component]"

        ).forEach(component=>{


            const name =

            component.dataset.component;



            this.loadComponent(

                name,

                component

            );


        });


    },



    loadComponent(name, element){


        this.log(

            "Component loaded:",

            name

        );


        element.classList.add(

            "component-ready"

        );


    },



    /* ======================================================
       CSRF SUPPORT
    ====================================================== */

    getCSRFToken(){


        const cookie =

        document.cookie

        .split(";")

        .find(

            row =>

            row.trim()

            .startsWith(

                "csrftoken="

            )

        );


        if(!cookie){

            return null;

        }


        return decodeURIComponent(

            cookie

            .split("=")[1]

        );


    },



    /* ======================================================
       AJAX REQUEST HELPER
    ====================================================== */

    async request(

        url,

        options={}

    ){


        const defaults = {


            method:"GET",


            headers:{


                "Content-Type":

                "application/json",


                "X-CSRFToken":

                this.getCSRFToken()

            }

        };



        const settings = {


            ...defaults,


            ...options,


            headers:{


                ...defaults.headers,


                ...(options.headers || {})

            }

        };



        try{


            const response =

            await fetch(

                url,

                settings

            );



            if(!response.ok){


                throw new Error(

                    `HTTP Error ${response.status}`

                );


            }



            return await response.json();



        }

        catch(error){


            this.log(

                "Request Failed",

                error

            );


            throw error;


        }


    },



    /* ======================================================
       GET REQUEST
    ====================================================== */

    get(url){


        return this.request(

            url,

            {

                method:"GET"

            }

        );


    },



    /* ======================================================
       POST REQUEST
    ====================================================== */

    post(url,data){


        return this.request(

            url,

            {


                method:"POST",


                body:

                JSON.stringify(data)


            }

        );


    },



    /* ======================================================
       THEME MANAGEMENT
    ====================================================== */

    loadTheme(){


        const theme =

        localStorage.getItem(

            this.config.themeKey

        );



        if(theme){


            document.documentElement

            .setAttribute(

                "data-theme",

                theme

            );


        }


    },



    toggleTheme(){


        const current =

        document.documentElement

        .getAttribute(

            "data-theme"

        );



        const next =


        current === "dark"

        ?

        "light"

        :

        "dark";



        document.documentElement

        .setAttribute(

            "data-theme",

            next

        );



        localStorage.setItem(

            this.config.themeKey,

            next

        );



        this.log(

            "Theme changed:",

            next

        );


    },



    /* ======================================================
       LOADING STATES
    ====================================================== */

    showLoading(element){


        element.classList.add(

            "loading"

        );


        setTimeout(()=>{


            element.classList.remove(

                "loading"

            );


        },1000);


    },



    /* ======================================================
       UTILITIES
    ====================================================== */

    qs(selector){


        return document.querySelector(

            selector

        );


    },



    qsa(selector){


        return document.querySelectorAll(

            selector

        );


    },


};




/* ==========================================================
   AUTO START
========================================================== */

document.addEventListener(

    "DOMContentLoaded",

    ()=>{


        EnterpriseUI.init();


    }

);



/* ==========================================================
   GLOBAL ACCESS
========================================================== */

window.EnterpriseUI = EnterpriseUI;