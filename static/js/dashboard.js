(function () {
  "use strict";

  function drawTrend(canvas, points) {
    if (!canvas || !points || !points.length) return;
    var ctx = canvas.getContext("2d");
    var width = canvas.width = canvas.clientWidth * (window.devicePixelRatio || 1);
    var height = canvas.height = canvas.clientHeight * (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, width, height);

    var max = 1;
    points.forEach(function (p) { if (p.count > max) max = p.count; });

    var pad = 16 * (window.devicePixelRatio || 1);
    var chartW = width - pad * 2;
    var chartH = height - pad * 2;

    ctx.strokeStyle = "#93c5fd";
    ctx.fillStyle = "rgba(37, 99, 235, 0.15)";
    ctx.lineWidth = 2 * (window.devicePixelRatio || 1);
    ctx.beginPath();

    points.forEach(function (p, i) {
      var x = pad + (chartW * (i / Math.max(points.length - 1, 1)));
      var y = pad + chartH - (chartH * (p.count / max));
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // fill under curve
    var lastX = pad + chartW;
    var firstX = pad;
    ctx.lineTo(lastX, pad + chartH);
    ctx.lineTo(firstX, pad + chartH);
    ctx.closePath();
    ctx.fill();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var canvas = document.getElementById("trendChart");
    var data = window.ESD_TREND;
    if (!data) {
      var node = document.getElementById("trendData");
      if (node) {
        try { data = JSON.parse(node.textContent || "[]"); } catch (e) { data = []; }
      }
    }
    if (typeof data === "string") {
      try { data = JSON.parse(data); } catch (e) { data = []; }
    }
    if (canvas && Array.isArray(data)) drawTrend(canvas, data);
  });
})();
