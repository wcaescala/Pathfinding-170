(function () {
  "use strict";
  var ALGOS = [
    { id: "gbfs", name: "GBFS", time: 0.44, exp: 27.5, alpha: 1.078 },
    { id: "astar", name: "A*", time: 0.79, exp: 50.5, alpha: 1.0 },
    { id: "jps", name: "JPS", time: 3.5, exp: 6.5, alpha: 1.0 },
    { id: "bfs", name: "BFS", time: 7.09, exp: 873.5, alpha: 1.0 },
    { id: "dijkstra", name: "Dijkstra", time: 8.77, exp: 882, alpha: 1.0 },
    { id: "dfs", name: "DFS", time: 15.29, exp: 1760, alpha: 7.659 }
  ];
  // Approximate values read from Figure 1 (median ms: short, medium, long)
  var TIERS = {
    astar: [0.2, 0.9, 80], bfs: [1.2, 8, 110], dfs: [2.1, 19, 85],
    dijkstra: [1.8, 10, 125], gbfs: [0.17, 0.43, 7.5], jps: [1.4, 2.3, 26]
  };
  var TIER_COLORS = ["#9fb3c4", "#5f7f99", "#1f3a52"];
  var METRICS = {
    time: { key: "time", log: true, unit: " ms", cap: "Median execution time, log scale. GBFS and A* are fastest; DFS is slowest." },
    exp: { key: "exp", log: true, unit: "", cap: "Median nodes expanded, log scale. JPS expands the fewest nodes even though it is not the fastest." },
    alpha: { key: "alpha", log: false, unit: "", cap: "Mean path suboptimality α (1.000 = optimal). DFS averages 7.659; GBFS pays about 8%." }
  };

  function fmt(n) {
    return n >= 1000 ? n.toLocaleString("en-US") : String(n);
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function scale(v, min, max, log) {
    if (!log) return (v / max) * 100;
    var lo = Math.log10(min / 2), hi = Math.log10(max);
    return Math.max(2, ((Math.log10(v) - lo) / (hi - lo)) * 100);
  }

  // Results table
  var tbody = document.querySelector("#results tbody");
  ALGOS.forEach(function (a) {
    var tr = el("tr");
    var th = el("th");
    th.scope = "row";
    var dot = el("i", "dot");
    dot.style.setProperty("--c", "var(--" + a.id + ")");
    th.appendChild(dot);
    th.appendChild(document.createTextNode(a.name));
    tr.appendChild(th);
    [a.time.toFixed(2), fmt(a.exp), a.alpha.toFixed(3)].forEach(function (t) { tr.appendChild(el("td", "", t)); });
    tr.dataset.id = a.id;
    tbody.appendChild(tr);
  });

  // Metric bars
  var barsEl = document.getElementById("bars");
  var capEl = document.getElementById("bars-cap");
  var rows = {};
  ALGOS.forEach(function (a) {
    var row = el("div", "row");
    row.appendChild(el("div", "name", a.name));
    var track = el("div", "track");
    var bar = el("div", "bar");
    bar.style.setProperty("--c", "var(--" + a.id + ")");
    bar.style.width = "0%";
    track.appendChild(bar);
    row.appendChild(track);
    row.addEventListener("mouseenter", function () { highlight(a.id); });
    row.addEventListener("mouseleave", function () { highlight(null); });
    barsEl.appendChild(row);
    rows[a.id] = bar;
  });

  function highlight(id) {
    Array.prototype.forEach.call(tbody.children, function (tr) {
      tr.classList.toggle("hl", tr.dataset.id === id);
    });
  }

  function render(metric) {
    var m = METRICS[metric];
    var vals = ALGOS.map(function (a) { return a[m.key]; });
    var min = Math.min.apply(null, vals), max = Math.max.apply(null, vals);
    ALGOS.forEach(function (a) {
      var v = a[m.key];
      var bar = rows[a.id];
      bar.style.width = scale(v, min, max, m.log) + "%";
      bar.textContent = (m.key === "alpha" ? v.toFixed(3) : v) + m.unit;
    });
    capEl.textContent = m.cap;
  }

  var buttons = document.querySelectorAll(".toggle button");
  Array.prototype.forEach.call(buttons, function (b) {
    b.addEventListener("click", function () {
      Array.prototype.forEach.call(buttons, function (x) {
        var on = x === b;
        x.classList.toggle("on", on);
        x.setAttribute("aria-pressed", on);
      });
      render(b.dataset.m);
    });
  });
  requestAnimationFrame(function () { render("time"); });

  // Figure 1: tiers
  var tiersEl = document.getElementById("tiers");
  ALGOS.slice().sort(function (a, b) { return a.name.localeCompare(b.name); }).forEach(function (a) {
    var row = el("div", "row tier");
    row.appendChild(el("div", "name", a.name));
    var track = el("div", "track");
    TIERS[a.id].forEach(function (v, i) {
      var bar = el("div", "bar");
      bar.style.setProperty("--c", TIER_COLORS[i]);
      bar.style.width = scale(v, 0.17, 125, true) + "%";
      bar.textContent = "~" + v;
      track.appendChild(bar);
    });
    row.appendChild(track);
    tiersEl.appendChild(row);
  });
})();