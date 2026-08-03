/* =====================================================================
   Enterprise Service Desk - Create Ticket form
   ---------------------------------------------------------------------
   Progressive enhancement + client-side validation.

   Safety model:
   - Everything is initialised from a single guarded entry point, so no
     selector can ever return null at listener-attach time.
   - Client-side validation is a UX convenience only. The Django form
     remains the source of truth; if JS fails the form still POSTs and
     the server validates it.
   ===================================================================== */

(function () {
    "use strict";

    /* ----------------------------------------------------------------
       Boot safely: run now if the DOM is already parsed (this file is
       loaded with `defer`, so that is the normal case), otherwise wait
       for DOMContentLoaded. Guarantees elements exist before we bind.
       ---------------------------------------------------------------- */
    function ready(fn) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", fn, { once: true });
        } else {
            fn();
        }
    }

    ready(function init() {
        var form = document.querySelector("[data-ticket-form]");
        if (!form) {
            return; // Not on the ticket page - nothing to enhance.
        }

        var submitButton = form.querySelector("[data-submit-button]");
        var submitLabel = form.querySelector("[data-submit-label]");
        var cancelButton = form.querySelector("[data-cancel-button]");
        var errorBox = form.querySelector("[data-client-error]");
        var errorText = form.querySelector("[data-client-error-text]");

        var submitting = false;

        /* ============================================================
           1. Validation helpers
           ============================================================ */

        function groupFor(field) {
            return field.closest(".esd-field-group");
        }

        function labelTextFor(field) {
            var group = groupFor(field);
            var label = group && group.querySelector(".esd-label");
            if (!label) {
                return "This field";
            }
            // Strip the "*" / "(required)" decorations.
            return label.textContent.replace(/[*]|\(required\)|\(optional\)/g, "")
                        .trim();
        }

        function clearError(field) {
            var group = groupFor(field);
            if (!group) {
                return;
            }
            group.classList.remove("esd-field-group--invalid");
            field.removeAttribute("aria-invalid");

            var clientError = group.querySelector("[data-client-field-error]");
            if (clientError) {
                clientError.remove();
            }
        }

        function showError(field, message) {
            var group = groupFor(field);
            if (!group) {
                return;
            }

            clearError(field);
            group.classList.add("esd-field-group--invalid");
            field.setAttribute("aria-invalid", "true");

            var p = document.createElement("p");
            p.className = "esd-error";
            p.setAttribute("data-client-field-error", "");

            var icon = document.createElement("i");
            icon.className = "fa-solid fa-circle-exclamation";
            icon.setAttribute("aria-hidden", "true");

            var span = document.createElement("span");
            span.textContent = message;

            p.appendChild(icon);
            p.appendChild(span);
            group.appendChild(p);
        }

        /**
         * Validate one field using the native Constraint Validation API,
         * with friendlier messages. Returns true when valid.
         */
        function validateField(field) {
            if (field.disabled || field.type === "hidden") {
                return true;
            }

            // checkValidity() respects required / type="email" / maxlength etc.
            if (typeof field.checkValidity === "function" && field.checkValidity()) {
                clearError(field);
                return true;
            }

            var name = labelTextFor(field);
            var message;

            if (field.validity && field.validity.valueMissing) {
                message = name + " is required.";
            } else if (field.validity && field.validity.typeMismatch) {
                message = field.type === "email"
                    ? "Enter a valid email address, e.g. name@company.com."
                    : "Enter a valid " + name.toLowerCase() + ".";
            } else if (field.validity && field.validity.tooLong) {
                message = name + " is too long.";
            } else {
                message = field.validationMessage || (name + " is invalid.");
            }

            showError(field, message);
            return false;
        }

        function validatableFields() {
            return form.querySelectorAll(
                "input:not([type=hidden]):not([type=file]), select, textarea"
            );
        }

        function validateForm() {
            var fields = validatableFields();
            var firstInvalid = null;
            var invalidCount = 0;

            Array.prototype.forEach.call(fields, function (field) {
                if (!validateField(field)) {
                    invalidCount += 1;
                    if (!firstInvalid) {
                        firstInvalid = field;
                    }
                }
            });

            if (errorBox && errorText) {
                if (invalidCount > 0) {
                    errorText.textContent = invalidCount === 1
                        ? "1 field needs your attention before you can submit."
                        : invalidCount + " fields need your attention before you can submit.";
                    errorBox.hidden = false;
                } else {
                    errorBox.hidden = true;
                }
            }

            return { valid: invalidCount === 0, firstInvalid: firstInvalid };
        }

        /* ============================================================
           2. Live feedback - validate on blur, clear errors on input
           ============================================================ */

        Array.prototype.forEach.call(validatableFields(), function (field) {
            field.addEventListener("blur", function () {
                // Only nag about a field the user has actually engaged with.
                if (field.value !== "") {
                    validateField(field);
                }
            });

            var eventName = (field.tagName === "SELECT") ? "change" : "input";
            field.addEventListener(eventName, function () {
                var group = groupFor(field);
                if (group && group.classList.contains("esd-field-group--invalid")) {
                    validateField(field);
                }
            });
        });

        /* ============================================================
           3. Submit handling
           ============================================================ */

        form.addEventListener("submit", function (e) {
            // Guard against double submission (Enter key + click, etc.)
            if (submitting) {
                e.preventDefault();
                return;
            }

            var result = validateForm();

            if (!result.valid) {
                // Block the submit and put the user on the first problem.
                e.preventDefault();

                if (result.firstInvalid) {
                    result.firstInvalid.focus({ preventScroll: true });
                    result.firstInvalid.scrollIntoView({
                        block: "center",
                        behavior: "smooth"
                    });
                }
                return;
            }

            // Valid: allow the native POST to proceed. We deliberately do NOT
            // call preventDefault() here - Django handles the submission.
            submitting = true;

            if (submitButton) {
                // Disable AFTER the browser has serialised the form, so no
                // field is dropped from the POST body.
                window.setTimeout(function () {
                    submitButton.setAttribute("aria-busy", "true");
                    submitButton.disabled = true;
                    if (submitLabel) {
                        submitLabel.textContent = "Creating…";
                    }
                }, 0);
            }
        });

        /* ============================================================
           4. Cancel handling
           ============================================================ */

        if (cancelButton) {
            cancelButton.addEventListener("click", function (e) {
                e.preventDefault();

                var isDirty = Array.prototype.some.call(
                    validatableFields(),
                    function (field) {
                        if (field.type === "checkbox" || field.type === "radio") {
                            return field.checked !== field.defaultChecked;
                        }
                        if (field.tagName === "SELECT") {
                            return Array.prototype.some.call(
                                field.options,
                                function (o) { return o.selected !== o.defaultSelected; }
                            );
                        }
                        return field.value !== field.defaultValue;
                    }
                );

                if (isDirty) {
                    var ok = window.confirm(
                        "Discard this ticket? Your changes will be lost."
                    );
                    if (!ok) {
                        return;
                    }
                }

                // Clear any validation state left on screen.
                Array.prototype.forEach.call(validatableFields(), clearError);
                if (errorBox) {
                    errorBox.hidden = true;
                }

                // 1) Inside a modal? Close it. 2) Otherwise navigate back.
                var modal = form.closest(".modal");
                if (modal && window.bootstrap && window.bootstrap.Modal) {
                    form.reset();
                    window.bootstrap.Modal.getOrCreateInstance(modal).hide();
                    return;
                }

                form.reset();

                var fallback = cancelButton.getAttribute("data-cancel-url") || "/";
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.location.assign(fallback);
                }
            });
        }

        /* ============================================================
           5. Auto-grow textareas
           ============================================================ */

        Array.prototype.forEach.call(form.querySelectorAll("textarea"), function (textarea) {
            function grow() {
                if (textarea.dataset.userResized === "true") {
                    return;
                }
                textarea.style.height = "auto";
                textarea.style.height = textarea.scrollHeight + "px";
            }

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

        /* ============================================================
           6. File upload - drag & drop + selected file list
           ============================================================ */

        Array.prototype.forEach.call(
            form.querySelectorAll("[data-upload-zone]"),
            function (zone) {
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
                    try {
                        input.files = dt.files;
                        renderFiles();
                    } catch (err) {
                        /* Older browser: click-to-upload still works. */
                    }
                });

                renderFiles();
            }
        );

        /* ============================================================
           7. Focus the first field carrying a SERVER-side error
           ============================================================ */

        var firstServerInvalid = form.querySelector(
            ".esd-field-group--invalid input, " +
            ".esd-field-group--invalid select, " +
            ".esd-field-group--invalid textarea"
        );

        if (firstServerInvalid) {
            firstServerInvalid.focus({ preventScroll: true });
            firstServerInvalid.scrollIntoView({ block: "center", behavior: "smooth" });
        }
    });
}());
