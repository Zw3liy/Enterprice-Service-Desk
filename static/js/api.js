(function () {
  "use strict";

  function csrf() {
    return (window.ESD && window.ESD.csrfToken && window.ESD.csrfToken()) || "";
  }

  async function request(url, options) {
    options = options || {};
    var headers = Object.assign(
      {
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      options.headers || {}
    );
    if (options.json) {
      headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.json);
      delete options.json;
    }
    if (options.method && options.method.toUpperCase() !== "GET") {
      headers["X-CSRFToken"] = csrf();
    }
    options.headers = headers;
    options.credentials = options.credentials || "same-origin";
    var resp = await fetch(url, options);
    var data = null;
    var text = await resp.text();
    try {
      data = text ? JSON.parse(text) : null;
    } catch (e) {
      data = { raw: text };
    }
    if (!resp.ok) {
      var err = new Error("API error " + resp.status);
      err.status = resp.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  window.ESD = window.ESD || {};
  window.ESD.api = {
    get: function (url) {
      return request(url, { method: "GET" });
    },
    post: function (url, json) {
      return request(url, { method: "POST", json: json || {} });
    },
    patch: function (url, json) {
      return request(url, { method: "PATCH", json: json || {} });
    },
    del: function (url) {
      return request(url, { method: "DELETE" });
    },
  };
})();
