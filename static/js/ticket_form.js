/**
 * Enterprise Service Desk - Ticket Form Enhancements
 * Handles accessible client-side validation, drag-and-drop file upload,
 * double-submit prevention, and smooth cancel navigation.
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('[data-ticket-form]');
    if (!form) return;

    const submitBtn = form.querySelector('[data-submit-button]');
    const submitLabel = form.querySelector('[data-submit-label]');
    const cancelBtn = form.querySelector('[data-cancel-button]');
    const clientErrorSummary = form.querySelector('[data-client-error]');
    const clientErrorText = form.querySelector('[data-client-error-text]');
    const uploadZone = form.querySelector('[data-upload-zone]');
    const fileInput = uploadZone ? uploadZone.querySelector('input[type="file"]') : null;
    const fileList = uploadZone ? uploadZone.querySelector('[data-upload-list]') : null;

    /* -------------------------------------------------------------------------
     * 1. Drag & Drop File Upload Handling
     * ------------------------------------------------------------------------- */
    if (uploadZone && fileInput) {
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadZone.classList.add('esd-upload--active');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadZone.classList.remove('esd-upload--active');
            }, false);
        });

        uploadZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                fileInput.files = files;
                updateFileList(files);
            }
        });

        fileInput.addEventListener('change', () => {
            updateFileList(fileInput.files);
        });
    }

    function updateFileList(files) {
        if (!fileList) return;
        fileList.innerHTML = '';
        if (files && files.length > 0) {
            fileList.hidden = false;
            Array.from(files).forEach(file => {
                const li = document.createElement('li');
                li.className = 'esd-upload__file-item';
                li.innerHTML = `<i class="fa-solid fa-file-lines me-1"></i> ${file.name} <small class="text-muted">(${formatBytes(file.size)})</small>`;
                fileList.appendChild(li);
            });
        } else {
            fileList.hidden = true;
        }
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /* -------------------------------------------------------------------------
     * 2. Cancel Button Handling
     * ------------------------------------------------------------------------- */
    if (cancelBtn) {
        cancelBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const targetUrl = cancelBtn.getAttribute('data-cancel-url');
            if (targetUrl) {
                window.location.href = targetUrl;
            } else {
                window.history.back();
            }
        });
    }

    /* -------------------------------------------------------------------------
     * 3. Form Validation & Submission
     * ------------------------------------------------------------------------- */
    form.addEventListener('submit', (e) => {
        let invalidFields = [];
        const requiredInputs = form.querySelectorAll('input[required], select[required], textarea[required]');

        requiredInputs.forEach(input => {
            const fieldGroup = input.closest('.esd-field-group');
            if (!input.value.trim()) {
                invalidFields.push(input);
                input.classList.add('is-invalid', 'esd-input--invalid');
                input.setAttribute('aria-invalid', 'true');
                if (fieldGroup) {
                    fieldGroup.classList.add('esd-field-group--invalid');
                }
            } else {
                input.classList.remove('is-invalid', 'esd-input--invalid');
                input.removeAttribute('aria-invalid');
                if (fieldGroup) {
                    fieldGroup.classList.remove('esd-field-group--invalid');
                }
            }
        });

        if (invalidFields.length > 0) {
            e.preventDefault();
            if (clientErrorSummary && clientErrorText) {
                clientErrorText.textContent = `Please complete all ${invalidFields.length} required field(s) before submitting.`;
                clientErrorSummary.hidden = false;
                clientErrorSummary.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            invalidFields[0].focus();
            return;
        }

        // Hide error message if valid
        if (clientErrorSummary) {
            clientErrorSummary.hidden = true;
        }

        // Double-submit guard: disable submit button immediately after submit event fires
        if (submitBtn) {
            setTimeout(() => {
                submitBtn.disabled = true;
                if (submitLabel) {
                    submitLabel.textContent = 'Submitting Ticket...';
                }
            }, 0);
        }
    });

    /* -------------------------------------------------------------------------
     * 4. Clear Inline Errors on Input
     * ------------------------------------------------------------------------- */
    form.addEventListener('input', (e) => {
        const target = e.target;
        if (target.matches('input, select, textarea')) {
            if (target.value.trim()) {
                target.classList.remove('is-invalid', 'esd-input--invalid');
                target.removeAttribute('aria-invalid');
                const fieldGroup = target.closest('.esd-field-group');
                if (fieldGroup) {
                    fieldGroup.classList.remove('esd-field-group--invalid');
                }
            }
        }
    });
});