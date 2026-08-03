(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    var toggle = document.getElementById("sidebarToggle");
    var sidebar = document.getElementById("appSidebar");
    if (toggle && sidebar) {
      toggle.addEventListener("click", function () {
        sidebar.classList.toggle("is-open");
      });
    }

    // Auto-dismiss alerts after 6s
    document.querySelectorAll(".alert-dismissible").forEach(function (el) {
      setTimeout(function () {
        try {
          var alert = bootstrap.Alert.getOrCreateInstance(el);
          alert.close();
        } catch (e) {
          el.remove();
        }
      }, 6000);
    });

    // Confirm destructive actions
    document.querySelectorAll("[data-confirm]").forEach(function (el) {
      el.addEventListener("click", function (evt) {
        var msg = el.getAttribute("data-confirm") || "Are you sure?";
        if (!window.confirm(msg)) evt.preventDefault();
      });
    });
  });

  window.ESD = window.ESD || {};
  window.ESD.csrfToken = function () {
    var cookie = document.cookie.split(";").map(function (c) { return c.trim(); });
    for (var i = 0; i < cookie.length; i++) {
      if (cookie[i].indexOf("csrftoken=") === 0) {
        return decodeURIComponent(cookie[i].split("=")[1]);
      }
    }
    var input = document.querySelector("[name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  };
})();
