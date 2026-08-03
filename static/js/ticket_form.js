/* =====================================================================
   Enterprise Service Desk - New Support Ticket
   ---------------------------------------------------------------------
   Progressive enhancement only. Every behaviour here is cosmetic or a
   convenience; the form submits and validates normally (server-side)
   with JavaScript disabled.
   ===================================================================== */

(function () {
    "use strict";

    var form = document.querySelector("[data-ticket-form]");
    if (!form) {
        return;
    }

    /* ----------------------------------------------------------------
       1. Auto-grow the description textarea (never shrinks below CSS
          min-height, and the user can still resize manually).
       ---------------------------------------------------------------- */

    var textareas = form.querySelectorAll("textarea");

    Array.prototype.forEach.call(textareas, function (textarea) {
        function grow() {
            if (textarea.dataset.userResized === "true") {
                return;
            }
            textarea.style.height = "auto";
            textarea.style.height = textarea.scrollHeight + "px";
        }

        // Respect a manual drag-resize by the user.
        if (typeof ResizeObserver === "function") {
            var lastHeight = textarea.offsetHeight;
            new ResizeObserver(function () {
                if (document.activeElement !== textarea &&
                    Math.abs(textarea.offsetHeight - lastHeight) > 2) {
                    textarea.dataset.userResized = "true";
                }
                lastHeight = textarea.offsetHeight;
            }).observe(textarea);
        }

        textarea.addEventListener("input", grow);
        grow();
    });


    /* ----------------------------------------------------------------
       2. File upload: drag & drop + selected-file list.
       ---------------------------------------------------------------- */

    var zones = form.querySelectorAll("[data-upload-zone]");

    Array.prototype.forEach.call(zones, function (zone) {
        var input = zone.querySelector('input[type="file"]');
        var list = zone.querySelector("[data-upload-list]");

        if (!input) {
            return;
        }

        function renderFiles() {
            if (!list) {
                return;
            }

            list.innerHTML = "";

            if (!input.files || input.files.length === 0) {
                list.hidden = true;
                return;
            }

            Array.prototype.forEach.call(input.files, function (file) {
                var item = document.createElement("li");

                var icon = document.createElement("i");
                icon.className = "fa-solid fa-file-lines";
                icon.setAttribute("aria-hidden", "true");

                var name = document.createElement("span");
                name.textContent = file.name;

                var size = document.createElement("span");
                size.className = "ms-auto text-muted";
                size.textContent = (file.size / 1024).toFixed(0) + " KB";

                item.appendChild(icon);
                item.appendChild(name);
                item.appendChild(size);
                list.appendChild(item);
            });

            list.hidden = false;
        }

        input.addEventListener("change", renderFiles);

        ["dragenter", "dragover"].forEach(function (evt) {
            zone.addEventListener(evt, function (e) {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.add("esd-upload--dragover");
            });
        });

        ["dragleave", "drop"].forEach(function (evt) {
            zone.addEventListener(evt, function (e) {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.remove("esd-upload--dragover");
            });
        });

        zone.addEventListener("drop", function (e) {
            var dt = e.dataTransfer;
            if (!dt || !dt.files || dt.files.length === 0) {
                return;
            }

            // Assigning a FileList is supported in all modern browsers.
            try {
                input.files = dt.files;
                renderFiles();
            } catch (err) {
                /* Older browser: the click-to-upload path still works. */
            }
        });

        renderFiles();
    });


    /* ----------------------------------------------------------------
       3. Submit state - prevents accidental double submission.
          The button is only disabled AFTER the browser has accepted the
          submission, so the POST always contains every field.
       ---------------------------------------------------------------- */

    var button = form.querySelector("[data-submit-button]");
    var label = form.querySelector("[data-submit-label]");

    form.addEventListener("submit", function () {
        if (!button) {
            return;
        }

        window.setTimeout(function () {
            button.setAttribute("aria-busy", "true");
            button.disabled = true;
            if (label) {
                label.textContent = "Submitting…";
            }
        }, 0);
    });


    /* ----------------------------------------------------------------
       4. Move keyboard focus to the first field with a server-side error.
       ---------------------------------------------------------------- */

    var firstInvalid = form.querySelector(
        ".esd-field-group--invalid input, " +
        ".esd-field-group--invalid select, " +
        ".esd-field-group--invalid textarea"
    );

    if (firstInvalid) {
        firstInvalid.focus({ preventScroll: true });
        firstInvalid.scrollIntoView({ block: "center", behavior: "smooth" });
    }

}());
