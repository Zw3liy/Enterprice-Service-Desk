(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var requestType = document.querySelector("[name=request_type]");
    if (!requestType) return;

    // When request type changes on create form, reload with selection preserved
    // so server can render matching dynamic fields if extended later.
    requestType.addEventListener("change", function () {
      var form = requestType.closest("form");
      if (!form) return;
      // Soft hint only — full dynamic reload can be wired to an API endpoint.
      requestType.classList.add("border-primary");
    });

    // Character counter for description
    var desc = document.querySelector("[name=description]");
    if (desc && !desc.dataset.counterBound) {
      desc.dataset.counterBound = "1";
      var counter = document.createElement("div");
      counter.className = "form-text text-end";
      desc.parentNode.appendChild(counter);
      var update = function () {
        counter.textContent = (desc.value || "").length + " characters";
      };
      desc.addEventListener("input", update);
      update();
    }
  });
})();
