import { searchPassages, passageKey, snippet } from "./evidence-tools.mjs";
const $ = (s, root = document) => root.querySelector(s);
const main = $("#main");
const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const fmt = (value) =>
  Number(value).toLocaleString("en-US", { maximumFractionDigits: 3 });
const iconPaths = {
  overview:
    '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  library:
    '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 4 16 4 16 0V5M4 12v7c0 4 16 4 16 0v-7"/>',
  studio: '<path d="M9 3h6m-5 0v7L4 20q0 1 2 1h12q2 0 2-1l-6-10V3M7 15h10"/>',
  frontier:
    '<path d="M3 3v18h18M6 16l4-5 4 2 6-8"/><circle cx="10" cy="11" r="1"/><circle cx="20" cy="5" r="1"/>',
  evidence:
    '<circle cx="5" cy="12" r="2.5"/><circle cx="18" cy="5" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="m7 11 9-5m-9 7 9 5"/>',
  extract: '<path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6m-6 4h6"/>',
  literature: '<path d="M3 5q5-2 9 1 4-3 9-1v14q-5-2-9 1-4-3-9-1zM12 6v14"/>',
  project: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-11v2"/>',
  layers: '<path d="m3 8 9-5 9 5-9 5zM3 12l9 5 9-5M3 16l9 5 9-5"/>',
  temp: '<path d="M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0Z"/><path d="M12 9v9m5-12h3m-3 4h2"/>',
  target:
    '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/>',
};
const icon = (key) =>
  '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
  iconPaths[key] +
  "</svg>";
const pages = {
  overview: "Overview",
  compare: "Compare heats",
  library: "Heat library",
  studio: "Alloy studio",
  frontier: "Pareto search",
  evidence: "Mechanisms",
  extract: "Document extractor",
  literature: "Evidence library",
  project: "Project details",
};
const nav = $("#nav");
const groups = [
  ["Explore", ["overview", "library", "compare"]],
  ["Analyse", ["studio", "frontier", "evidence"]],
  ["Research", ["literature", "extract", "project"]],
];
nav.innerHTML = groups
  .map(
    ([label, keys]) =>
      '<div class="navgroup"><p class="overline">' +
      label +
      "</p>" +
      keys
        .map(
          (k) =>
            '<a class="navitem" href="#' +
            k +
            '">' +
            icon(k === "compare" ? "layers" : k) +
            pages[k] +
            "</a>",
        )
        .join("") +
      "</div>",
  )
  .join("");
$(".skip").onclick = (e) => {
  e.preventDefault();
  main.focus();
  main.scrollIntoView();
};
function menu(open) {
  nav.hidden = !open;
  for (const trigger of document.querySelectorAll("#tools,#menu"))
    trigger.setAttribute("aria-expanded", String(open));
}
for (const trigger of document.querySelectorAll("#tools,#menu"))
  trigger.onclick = () => menu(nav.hidden);
document.addEventListener("click", (e) => {
  if (!e.target.closest("header") || e.target.closest("#nav a")) menu(false);
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !nav.hidden) {
    menu(false);
    (window.matchMedia("(max-width:760px)").matches
      ? $("#menu")
      : $("#tools")
    ).focus();
  }
});
const state = {
  page: "overview",
  heat: "HSLA-100_Std",
  temperature: "all",
  query: "",
  family: "all",
  modelInput: null,
  modelResult: null,
  candidates: null,
  extraction: null,
  extractionName: "",
  job: 0,
};
let data,
  heats,
  engine,
  ongoing = new Map(),
  nextId = 0;
const palette = {
  HSLA: "#087056",
  HY: "#7462ad",
  BlastAlloy: "#b76828",
  AF1410: "#ab486f",
  Research: "#41838d",
};
function family(r) {
  const n = r.alloy_name;
  if (n.startsWith("HSLA")) return "HSLA";
  if (n.startsWith("HY")) return "HY";
  if (n.startsWith("BlastAlloy")) return "BlastAlloy";
  if (n.startsWith("AF1410")) return "AF1410";
  return "Research";
}
function grade(r) {
  return r.alloy_name
    .replace(/_(Std|SubZero|LowT|Opt|\d+C)$/, "")
    .replace(/_(A[1-3]|B[1-3]|[1-4])$/, "")
    .replace("Cu_SecHard", "Cu secondary-hardening")
    .replace("LowC_Bainitic", "Low-carbon bainitic");
}
const activeHeat = () => heats.find((r) => r.alloy_name === state.heat);
const selected = (v, w) => (v === w ? " selected" : "");
const opt = (v, label, chosen) =>
  '<option value="' +
  escapeHTML(v) +
  '"' +
  selected(v, chosen) +
  ">" +
  escapeHTML(label) +
  "</option>";
const dot = (r) =>
  '<i class="dot" style="--dot:' + palette[family(r)] + '"></i>';
const row = (name, value) =>
  '<div class="row"><span>' +
  escapeHTML(name) +
  '</span><span class="value">' +
  escapeHTML(value) +
  "</span></div>";
const metric = (name, value) =>
  "<div><strong>" +
  escapeHTML(value) +
  "</strong><small>" +
  escapeHTML(name) +
  "</small></div>";
const pageHead = (title, lead) =>
  '<div class="pagehead"><h1>' +
  title +
  '</h1><p class="lead">' +
  lead +
  "</p></div>";
const panel = (title, html) =>
  '<section class="panel"><h2>' + title + "</h2>" + html + "</section>";
const elements = [
  "C",
  "Mn",
  "Si",
  "Ni",
  "Cr",
  "Mo",
  "Cu",
  "V",
  "Nb",
  "Co",
  "B",
];
const modelKeys = [
  "yield_strength_mpa",
  "tensile_strength_mpa",
  "charpy_toughness_j",
];
const names = ["Yield strength", "Tensile strength", "Charpy energy"];
const units = ["MPa", "MPa", "J"];
const profileRows = (r) =>
  modelKeys
    .map((key, i) => row(names[i], fmt(r[key]) + " " + units[i]))
    .join("") + row("Test temperature", fmt(r.test_temp_C) + " °C");
function download(filename, text, type = "application/json") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function heatTable(rows) {
  return (
    '<div class="tablewrap"><table><thead><tr><th>Heat record</th><th>Test (°C)</th><th>Yield (MPa)</th><th>Tensile (MPa)</th><th>Charpy (J)</th></tr></thead><tbody>' +
    rows
      .map(
        (r) =>
          '<tr><td><button class="tablelink" data-heat="' +
          r.alloy_name +
          '">' +
          dot(r) +
          r.alloy_name +
          "</button></td>" +
          ["test_temp_C", ...modelKeys]
            .map((k) => '<td class="num">' + fmt(r[k]) + "</td>")
            .join("") +
          "</tr>",
      )
      .join("") +
    "</tbody></table></div>"
  );
}
function bars(r) {
  const items = elements.filter((k) => r[k] > 0).sort((a, b) => r[b] - r[a]);
  const max = Math.max(...items.map((k) => r[k]));
  return items
    .map(
      (k) =>
        '<div class="barrow"><b>' +
        k +
        '</b><div><i style="width:' +
        (100 * r[k]) / max +
        '%"></i></div><span class="num">' +
        fmt(r[k]) +
        " wt%</span></div>",
    )
    .join("");
}
function inspect(r) {
  $("dialog")?.remove();
  const d = document.createElement("dialog");
  d.setAttribute("aria-labelledby", "record-title");
  d.innerHTML =
    '<div class="panelhead"><span class="smallcap">Heat record</span><button class="ghost" data-close>Close</button></div><h2 id="record-title">' +
    r.alloy_name +
    '</h2><p class="hint">Project dataset · ' +
    escapeHTML(grade(r)) +
    '</p><div class="infoRows">' +
    profileRows(r) +
    row(
      "Temper",
      fmt(r.temper_temp_C) + " °C · " + fmt(r.temper_time_h) + " h",
    ) +
    '</div><p class="smallcap">Composition · wt%</p>' +
    bars(r) +
    '<p class="note">Fe balance ' +
    fmt(100 - elements.reduce((sum, k) => sum + (r[k] || 0), 0)) +
    ' wt%</p><div class="actions group"><button class="button primary" id="modelheat">Model this heat</button><button class="ghost" id="dlheat">Export JSON</button></div>';
  document.body.append(d);
  d.showModal();
  $("[data-close]", d).onclick = () => d.close();
  d.onclick = (e) => {
    if (e.target === d) d.close();
  };
  d.onclose = () => d.remove();
  $("#dlheat", d).onclick = () =>
    download(r.alloy_name + ".json", JSON.stringify(r, null, 2));
  $("#modelheat", d).onclick = () => {
    loadModelHeat(r);
    d.close();
    navigate("studio");
  };
}
function chart(rows) {
  const w = 600,
    h = 252,
    l = 55,
    rt = 20,
    t = 16,
    b = 47,
    x = (v) => l + ((v - 450) / 800) * (w - l - rt),
    y = (v) => h - b - ((v - 40) / 180) * (h - b - t);
  const xt = [500, 700, 900, 1100, 1200],
    yt = [50, 100, 150, 200];
  const lines =
    xt
      .map(
        (v) =>
          '<line x1="' +
          x(v) +
          '" x2="' +
          x(v) +
          '" y1="' +
          t +
          '" y2="' +
          (h - b) +
          '"/><text text-anchor="middle" x="' +
          x(v) +
          '" y="' +
          (h - b + 19) +
          '">' +
          v +
          "</text>",
      )
      .join("") +
    yt
      .map(
        (v) =>
          '<line x1="' +
          l +
          '" x2="' +
          (w - rt) +
          '" y1="' +
          y(v) +
          '" y2="' +
          y(v) +
          '"/><text x="' +
          (l - 10) +
          '" y="' +
          (y(v) + 4) +
          '" text-anchor="end">' +
          v +
          "</text>",
      )
      .join("");
  const points = rows
    .map((r) => {
      const cx = x(r.yield_strength_mpa),
        cy = y(r.charpy_toughness_j);
      return (
        (r.alloy_name === state.heat
          ? '<circle fill="none" stroke="#123e2a" stroke-width="1.3" cx="' +
            cx +
            '" cy="' +
            cy +
            '" r="9"/>'
          : "") +
        '<circle role="button" tabindex="0" class="pt" aria-label="' +
        r.alloy_name +
        ", " +
        r.yield_strength_mpa +
        " MPa, " +
        r.charpy_toughness_j +
        ' J" data-point="' +
        r.alloy_name +
        '" fill="' +
        palette[family(r)] +
        '" cx="' +
        cx +
        '" cy="' +
        cy +
        '" r="5"><title>' +
        r.alloy_name +
        " · " +
        r.yield_strength_mpa +
        " MPa / " +
        r.charpy_toughness_j +
        " J at " +
        r.test_temp_C +
        " °C</title></circle>"
      );
    })
    .join("");
  return (
    '<svg class="plot" viewBox="0 0 ' +
    w +
    " " +
    h +
    '" aria-label="Scatter plot of yield strength and Charpy energy"><g stroke="#c3d3cb" stroke-dasharray="3 4">' +
    lines.replaceAll("<text ", '<text stroke="none" ') +
    '</g><text x="' +
    (w + l) / 2 +
    '" y="' +
    (h - 5) +
    '" text-anchor="middle">Yield strength (MPa)</text><text x="0" y="0" transform="translate(13 114) rotate(-90)" text-anchor="middle">Charpy energy (J)</text>' +
    points +
    "</svg>"
  );
}
function overview() {
  const temps = [...new Set(heats.map((r) => r.test_temp_C))].sort(
    (a, b) => a - b,
  );
  const rows = heats.filter(
    (r) =>
      state.temperature === "all" ||
      String(r.test_temp_C) === state.temperature,
  );
  if (!rows.includes(activeHeat())) state.heat = rows[0].alloy_name;
  const r = activeHeat();
  main.innerHTML = `<section class="showcase"><picture><source media="(max-width:650px)" srcset="assets/studio-hero-small.webp"><img src="assets/studio-hero.webp" alt="" fetchpriority="high" width="1440" height="960"></picture><div class="covercopy"><p class="overline"><span class="stripe"></span>IIT Kanpur <i></i> UGP 497</p><h1>Naval steel<br><em>research atlas.</em></h1><p class="coverdesc">Compare steel properties, inspect the evidence, and model an alloy in your browser.</p><div class="coveractions"><a class="button primary" href="#library">Explore heat library</a><a class="button glass" href="#compare">Compare heats</a></div></div></section>
 <div class="databar">${[
   ["library", heats.length, "Heat records"],
   ["layers", data.records.length, "Benchmark steels"],
   ["temp", temps[0] + " to " + temps.at(-1) + " °C", "Test range"],
 ]
   .map(
     ([k, v, l]) =>
       "<div>" +
       icon(k) +
       "<strong>" +
       v +
       "</strong><span>" +
       l +
       "</span></div>",
   )
   .join("")}</div>
 <section class="atlasbody"><div class="sectionintro"><div><p class="overline">Property explorer</p><h2>Strength &amp; <em>toughness.</em></h2></div><a class="textbtn" href="#library">Browse all heats</a></div>
 <div class="twocol"><section class="panel mapcard"><div class="panelhead"><div><h3>Property map</h3><p>Select a heat to see its test conditions.</p></div><select aria-label="Filter test temperature" id="charttemp">${opt("all", "All temperatures", state.temperature) + temps.map((t) => opt(String(t), t + " °C", state.temperature)).join("")}</select></div><div class="chartwrap">${chart(rows)}</div><div class="legend">${Object.entries(
   palette,
 )
   .filter(([g]) => rows.some((h) => family(h) === g))
   .map(
     ([g, c]) =>
       '<span><i class="dot" style="--dot:' + c + '"></i>' + g + "</span>",
   )
   .join("")}</div></section>
 <section class="panel inspector"><p class="overline">Heat inspector</p><h3 class="profileTitle">${escapeHTML(grade(r))}</h3><select id="inspectheat" aria-label="Select heat record">${rows.map((h) => opt(h.alloy_name, h.alloy_name, state.heat)).join("")}</select><div class="infoRows">${profileRows(r)}</div><button class="ghost" data-heat="${r.alloy_name}">Open heat record</button></section></div>
 <div class="sectionintro smallintro"><h2>Research tools</h2></div><div class="toolgrid">${[
   [
     "studio",
     "Alloy studio",
     "Estimate properties from chemistry and test conditions.",
   ],
   [
     "literature",
     "Evidence library",
     "Find a passage and open the original report page.",
   ],
   [
     "extract",
     "Document extractor",
     "Read a lab file privately and export its record.",
   ],
 ]
   .map(
     ([k, t, d]) =>
       '<a class="tooltile" href="#' +
       k +
       '"><span class="tileico">' +
       icon(k) +
       "</span><h3>" +
       t +
       "</h3><p>" +
       d +
       "</p></a>",
   )
   .join("")}</div></section>`;
  $("#charttemp").onchange = (e) => {
    state.temperature = e.target.value;
    overview();
    $("#charttemp").focus();
  };
  $("#inspectheat").onchange = (e) => {
    state.heat = e.target.value;
    overview();
    $("#inspectheat").focus();
  };
}
function comparePage() {
  const params = new URLSearchParams(location.hash.split("?")[1]);
  const resolve = (v, fallback) =>
    heats.find((r) => r.alloy_name === v) ||
    heats.find((r) => r.alloy_name === fallback);
  const A = resolve(params.get("a"), "HSLA-100_Std"),
    B = resolve(params.get("b"), "HY-100_Std");
  const metrics = [
    ...modelKeys.map((k, i) => [k, names[i], units[i]]),
    ["test_temp_C", "Test temperature", "°C"],
    ["temper_temp_C", "Temper temperature", "°C"],
    ["temper_time_h", "Temper hold", "h"],
  ];
  const values = metrics.map(([k, name, unit]) => [
    name,
    unit,
    A[k],
    B[k],
    +(B[k] - A[k]).toFixed(3),
  ]);
  main.innerHTML =
    pageHead(
      "Compare heats",
      "Compare two dataset records with their test conditions in view.",
    ) +
    panel(
      "Select heat records",
      '<div class="inputgrid group">' +
        [
          ["a", "Heat A", A],
          ["b", "Heat B", B],
        ]
          .map(
            ([id, l, r]) =>
              '<label class="field">' +
              l +
              '<select id="compare' +
              id +
              '">' +
              heats
                .map((h) => opt(h.alloy_name, h.alloy_name, r.alloy_name))
                .join("") +
              "</select></label>",
          )
          .join("") +
        '</div><p class="contextnote">' +
        (A === B
          ? "Both selectors show the same heat."
          : A.test_temp_C === B.test_temp_C
            ? "Both heats were tested at " + fmt(A.test_temp_C) + " °C."
            : "Test temperatures differ. Consider this when interpreting the property differences.") +
        '</p><div class="tablewrap"><table class="comparetable"><thead><tr><th>Property</th><th>A</th><th>B</th><th>B − A</th></tr></thead><tbody>' +
        values
          .map(
            ([name, unit, a, b, d]) =>
              '<tr><th scope="row">' +
              name +
              " <small>(" +
              unit +
              ")</small></th><td>" +
              fmt(a) +
              "</td><td>" +
              fmt(b) +
              "</td><td>" +
              (d > 0 ? "+" : "") +
              fmt(d) +
              "</td></tr>",
          )
          .join("") +
        '</tbody></table></div><div class="actions group"><button id="deltacsv" class="ghost">Export comparison</button><button id="copycompare" class="ghost">Copy comparison link</button></div><p id="copystatus" class="hint" role="status"></p>',
    );
  const hash = () =>
    "compare?" +
    new URLSearchParams({ a: $("#comparea").value, b: $("#compareb").value });
  for (const sel of [$("#comparea"), $("#compareb")])
    sel.onchange = () => {
      location.hash = hash();
    };
  $("#deltacsv").onclick = () =>
    download(
      "heat-comparison.csv",
      [["Property", "Unit", A.alloy_name, B.alloy_name, "B minus A"], ...values]
        .map((v) => v.join(","))
        .join("\n"),
      "text/csv",
    );
  $("#copycompare").onclick = async () => {
    const url = new URL(location.href);
    url.hash = hash();
    try {
      await navigator.clipboard.writeText(url.href);
      $("#copystatus").textContent = "Comparison link copied.";
    } catch {
      $("#copystatus").textContent = url.href;
    }
  };
}
function library() {
  main.innerHTML =
    pageHead(
      pages.library,
      "Browse the project dataset by grade, heat condition, and test temperature.",
    ) +
    panel(
      "Heat records",
      '<div class="controls"><label class="field">Find a heat<input class="search" id="findheat" placeholder="Heat name or grade"></label><label class="field">Steel family<select id="family">' +
        opt("all", "All families", state.family) +
        Object.keys(palette)
          .map((v) => opt(v, v, state.family))
          .join("") +
        '</select></label><button id="csv" class="ghost">Export filtered CSV</button></div><div id="heatlist"></div>',
    );
  main.insertAdjacentHTML(
    "beforeend",
    '<div class="actions group"><a class="button secondary" href="#compare">Compare two heats</a></div>',
  );
  const q = $("#findheat");
  q.value = state.query;
  let filtered;
  const update = () => {
    filtered = heats.filter(
      (r) =>
        (state.family === "all" || family(r) === state.family) &&
        (r.alloy_name + " " + grade(r))
          .toLowerCase()
          .includes(state.query.trim().toLowerCase()),
    );
    $("#heatlist").innerHTML =
      '<p class="hint">' +
      filtered.length +
      " of " +
      heats.length +
      " heat records</p>" +
      (filtered.length
        ? heatTable(filtered)
        : '<p class="empty">No matching heats. Try another name or family.</p>');
    $("#csv").disabled = !filtered.length;
  };
  q.oninput = () => {
    state.query = q.value;
    update();
  };
  $("#family").onchange = (e) => {
    state.family = e.target.value;
    update();
  };
  $("#csv").onclick = () => {
    const keys = Object.keys(heats[0]);
    download(
      "navalsteel-heats.csv",
      [
        keys.join(","),
        ...filtered.map((r) => keys.map((k) => r[k]).join(",")),
      ].join("\n"),
      "text/csv",
    );
  };
  update();
}
function loadModelHeat(r) {
  state.modelPreset = r.alloy_name;
  state.modelInput = Object.fromEntries(
    [...elements, "temper_temp_C", "temper_time_h", "test_temp_C"].map((k) => [
      k,
      r[k] ?? 0,
    ]),
  );
  state.modelResult = null;
}
function run(action, payload) {
  if (!engine) {
    engine = new Worker("engine-worker.js");
    engine.onmessage = (e) => {
      const job = ongoing.get(e.data.id);
      if (!job) return;
      ongoing.delete(e.data.id);
      if (e.data.error) job.reject(Error(e.data.error));
      else job.resolve(e.data.result);
    };
    engine.onerror = () => {
      for (const job of ongoing.values())
        job.reject(Error("The analysis engine could not start. Try again."));
      ongoing.clear();
      engine.terminate();
      engine = null;
    };
  }
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    ongoing.set(id, { resolve, reject });
    engine.postMessage({ id, action, payload });
  });
}
const field = (name, label, value, min, max, step = "any") =>
  '<label class="field">' +
  escapeHTML(label) +
  '<input type="number" name="' +
  name +
  '" value="' +
  value +
  '" min="' +
  min +
  '" max="' +
  max +
  '" step="' +
  step +
  '" required></label>';
function studio() {
  if (!state.modelInput) loadModelHeat(activeHeat());
  const m = state.modelInput;
  main.innerHTML =
    pageHead(
      pages.studio,
      "Start from a heat, edit its chemistry, and predict mechanical properties.",
    ) +
    '<div class="stack">' +
    panel(
      "Alloy formulation",
      '<div class="controls"><label class="field">Starting heat<select id="preset">' +
        heats
          .map((r) => opt(r.alloy_name, r.alloy_name, state.modelPreset))
          .join("") +
        '</select></label></div><form id="model"><p class="smallcap group">Composition · wt%</p><div class="gridfields">' +
        elements.map((k) => field(k, k, m[k], 0, 100)).join("") +
        '</div><p id="balance" class="hint"></p><p class="smallcap group">Test conditions</p><div class="gridfields">' +
        field("temper_temp_C", "Temper (°C)", m.temper_temp_C, 400, 675) +
        field("temper_time_h", "Hold (h)", m.temper_time_h, 0.1, 24) +
        field("test_temp_C", "Test (°C)", m.test_temp_C, -84, 25) +
        '</div><div class="actions group"><button class="button primary">Predict properties</button><span role="status" class="hint" id="modelstatus"></span></div></form>',
    ) +
    '<div id="predictions"></div></div>';
  const form = $("#model"),
    balance = $("#balance");
  function update() {
    const sum = elements.reduce(
      (s, k) => s + Number(form.elements[k].value),
      0,
    );
    balance.textContent =
      sum <= 100
        ? "Fe balance " + fmt(100 - sum) + " wt%"
        : "Total solutes exceed 100 wt%.";
    form.elements.C.setCustomValidity(
      sum > 100 ? "Reduce the total to 100 wt% or less." : "",
    );
  }
  update();
  $("#preset").onchange = (e) => {
    loadModelHeat(heats.find((r) => r.alloy_name === e.target.value));
    studio();
  };
  form.oninput = () => {
    update();
    state.modelInput = Object.fromEntries(
      [...new FormData(form)].map(([k, v]) => [k, Number(v)]),
    );
    state.modelResult = null;
    $("#predictions").innerHTML = "";
  };
  function show(result) {
    const p = result.physics;
    $("#predictions").innerHTML = panel(
      "Predicted properties",
      '<div class="metrics">' +
        modelKeys
          .map((k, i) =>
            metric(
              names[i],
              fmt(result.properties[k].mean) +
                " ± " +
                fmt(result.properties[k].uncertainty) +
                " " +
                units[i],
            ),
          )
          .join("") +
        '</div><div class="infoRows">' +
        row(
          "Cracking parameter Pcm",
          p.pcm.toFixed(3) +
            " · " +
            (p.pcm <= 0.3 ? "within" : "above") +
            " 0.30 limit",
        ) +
        row(
          "Martensite start",
          p.martensite_start_C +
            " °C · " +
            (p.martensite_start_C >= 300 ? "within range" : "below 300 °C"),
        ) +
        '</div><p class="note">± reports model spread across trees and regressors. The model was trained on 40 project heats and may extrapolate for new compositions.</p><button id="dlprediction" class="ghost group">Export prediction</button>',
    );
    $("#dlprediction").onclick = () =>
      download(
        "alloy-prediction.json",
        JSON.stringify({ inputs: state.modelInput, ...result }, null, 2),
      );
  }
  if (state.modelResult) show(state.modelResult);
  form.onsubmit = async (e) => {
    e.preventDefault();
    const status = $("#modelstatus"),
      button = $("button", form),
      params = { ...state.modelInput };
    button.disabled = true;
    status.textContent = "Computing in your browser…";
    try {
      const result = await run("predict", params);
      if (
        status.isConnected &&
        JSON.stringify(params) === JSON.stringify(state.modelInput)
      ) {
        state.modelResult = result;
        show(result);
        status.textContent = "Prediction complete.";
      }
    } catch (err) {
      status.textContent = err.message;
    } finally {
      button.disabled = false;
    }
  };
}
function frontier() {
  const params = state.targets || { ys: 650, cvn: 80, temp: 25 };
  main.innerHTML =
    pageHead(
      pages.frontier,
      "Find modelled alloys that meet your strength and impact-energy targets.",
    ) +
    panel(
      "Search targets",
      '<form id="targets"><div class="gridfields group">' +
        field("ys", "Minimum yield (MPa)", params.ys, 0, 1800) +
        field("cvn", "Minimum Charpy (J)", params.cvn, 0, 350) +
        field("temp", "Test temperature (°C)", params.temp, -84, 25) +
        '</div><div class="infoRows">' +
        row("Project limits", "Pcm ≤ 0.30 · Ms ≥ 300 °C") +
        '</div><div class="actions group"><button class="button primary">Run Pareto search</button><span id="frontstatus" role="status" class="hint"></span></div></form>',
    ) +
    '<div class="results" id="frontresults"></div>';
  function show(cs) {
    $("#frontresults").innerHTML = panel(
      "Candidate alloys",
      '<p class="hint">' +
        (cs.length
          ? cs.length +
            " distinct non-dominated candidates met the targets in this run."
          : "No candidate in this run met every target. Try a lower strength or energy minimum.") +
        "</p>" +
        cs
          .map(
            (c) =>
              "<details><summary>" +
              escapeHTML(c.id) +
              " · " +
              fmt(c.yield_strength_mpa) +
              " MPa · " +
              fmt(c.charpy_toughness_j) +
              ' J</summary><div class="infoRows">' +
              row("Pcm", c.pcm) +
              row("Martensite start", c.ms_C + " °C") +
              row(
                "Predicted tensile strength",
                c.tensile_strength_mpa + " MPa",
              ) +
              row(
                "Estimated raw materials",
                fmt(c.cost_per_ton_usd) + " USD/t",
              ) +
              row(
                "Temper",
                fmt(c.processing.temper_temp_C) +
                  " °C · " +
                  fmt(c.processing.temper_time_h) +
                  " h",
              ) +
              "</div>" +
              bars(c.composition) +
              "</details>",
          )
          .join("") +
        (cs.length
          ? '<button class="ghost group" id="dlfront">Export candidates</button>'
          : "") +
        '<p class="note">NSGA-II search over yield strength, Charpy energy, Pcm, and estimated raw-material cost. Predictions require experimental validation.</p>',
    );
    if (cs.length)
      $("#dlfront").onclick = () =>
        download(
          "pareto-candidates.json",
          JSON.stringify({ targets: state.targets, candidates: cs }, null, 2),
        );
  }
  if (state.candidates) show(state.candidates);
  const form = $("#targets");
  form.oninput = () => {
    state.candidates = null;
    $("#frontresults").innerHTML = "";
    state.targets = Object.fromEntries(
      [...new FormData(form)].map(([k, v]) => [k, Number(v)]),
    );
  };
  form.onsubmit = async (e) => {
    e.preventDefault();
    const params = Object.fromEntries(
      [...new FormData(form)].map(([k, v]) => [k, Number(v)]),
    );
    state.targets = params;
    const button = $("button", form),
      status = $("#frontstatus");
    button.disabled = true;
    status.textContent = "Searching in your browser…";
    try {
      const cs = await run("optimize", params);
      if (status.isConnected && state.targets === params) {
        state.candidates = cs;
        show(cs);
        status.textContent = "Search complete.";
      }
    } catch (err) {
      status.textContent = err.message;
    } finally {
      button.disabled = false;
    }
  };
}
function evidence() {
  const edges = data.edges,
    alloys = [...new Set(edges.map((e) => e["Alloy Origin"]))];
  main.innerHTML =
    pageHead(
      pages.evidence,
      "Trace the links between elements, microstructure, and properties in the project records.",
    ) +
    panel(
      "Mechanism pathways",
      '<div class="controls"><label class="field">Steel<select id="edgealloy">' +
        opt("all", "All steels", "all") +
        alloys.map((v) => opt(v, v)).join("") +
        '</select></label><label class="field">Evidence grade<select id="egrade">' +
        ["all", ...new Set(edges.map((e) => e["Evidence Grade"]))]
          .map((v) => opt(v, v === "all" ? "All grades" : v))
          .join("") +
        '</select></label></div><div id="edges"></div>',
    );
  const draw = () => {
    const filt = edges.filter(
      (e) =>
        ($("#edgealloy").value === "all" ||
          $("#edgealloy").value === e["Alloy Origin"]) &&
        ($("#egrade").value === "all" ||
          $("#egrade").value === e["Evidence Grade"]),
    );
    $("#edges").innerHTML =
      '<p class="hint">' +
      filt.length +
      " recorded relationships</p>" +
      filt
        .map(
          (e) =>
            "<details><summary>" +
            escapeHTML(e["Source (From)"]) +
            " → " +
            escapeHTML(e["Target (To)"]) +
            '</summary><div class="edge tight"><span class="pill">' +
            escapeHTML(e["Evidence Grade"]) +
            "</span><strong>" +
            escapeHTML(e["Relationship"]) +
            "</strong></div><p>" +
            escapeHTML(
              e["Scientific Evidence Claim"] ||
                "No supporting passage recorded.",
            ) +
            '</p><p class="note">' +
            escapeHTML(e["Alloy Origin"]) +
            " · " +
            escapeHTML(e["Literature"]) +
            "</p></details>",
        )
        .join("");
  };
  $("#edgealloy").onchange = draw;
  $("#egrade").onchange = draw;
  draw();
}
let reportsPromise;
function reports() {
  if (!reportsPromise)
    reportsPromise = fetch("report-index.json")
      .then((r) => {
        if (!r.ok) throw Error("Report index unavailable.");
        return r.json();
      })
      .catch((e) => {
        reportsPromise = null;
        throw e;
      });
  return reportsPromise;
}
const shelfKey = "navalsteel.saved-passages.v1";
function savedKeys() {
  try {
    const items = JSON.parse(localStorage.getItem(shelfKey) || "[]");
    return Array.isArray(items)
      ? items.filter((v) => typeof v === "string")
      : [];
  } catch {
    return [];
  }
}
function literature() {
  main.innerHTML =
    pageHead(
      "Evidence library",
      "Search the two project reports by passage or inspect the claims in a curated steel record.",
    ) +
    '<div class="stack">' +
    panel(
      "Search report pages",
      '<form id="reportform" class="controls"><label class="field">Search passages<input id="reportquery" type="search" required placeholder="e.g. uncertainty"></label><label class="field">Document<select id="reportscope">' +
        opt("all", "Both project reports") +
        opt("design-report", "Detailed project report") +
        opt("ugp497-report", "UGP 497 final report") +
        '</select></label><button class="button primary">Search reports</button></form><p id="searchstatus" class="hint" role="status"></p><div id="reporthits"></div>',
    ) +
    panel("Saved passages", '<div id="shelf"></div>') +
    panel(
      "Curated steel records",
      '<label class="field group">Filter by steel, author, or title<input id="papers" type="search" placeholder="Find a record"></label><div id="records"></div>',
    ) +
    "</div>";
  const output = $("#reporthits"),
    shelf = $("#shelf"),
    status = $("#searchstatus");
  let results = [],
    docs = [],
    stored = savedKeys();
  function ref(hit) {
    return (
      '<a class="tablelink" href="assets/' +
      hit.doc +
      ".pdf#page=" +
      hit.page +
      '" target="_blank" rel="noopener">' +
      escapeHTML(hit.title) +
      " · p. " +
      hit.page +
      "</a>"
    );
  }
  function allSaved() {
    const items = [];
    for (const doc of docs)
      for (const p of doc.pages)
        for (const [index, paragraph] of p.paragraphs.entries()) {
          const h = {
            doc: doc.id,
            title: doc.title,
            page: p.page,
            index,
            paragraph,
          };
          if (stored.includes(passageKey(h))) items.push(h);
        }
    return items;
  }
  function renderShelf() {
    const items = allSaved();
    shelf.innerHTML = items.length
      ? items
          .map(
            (h) =>
              '<article class="evidencehit">' +
              ref(h) +
              "<p>" +
              escapeHTML(snippet(h.paragraph, "")) +
              '</p><button class="ghost" data-unsave="' +
              passageKey(h) +
              '">Remove</button></article>',
          )
          .join("") +
        '<button id="exportnotes" class="button secondary group">Export citations</button>'
      : '<p class="hint">Save a passage from the search results to keep its page reference on this device.</p>';
    shelf
      .querySelectorAll("[data-unsave]")
      .forEach((b) => (b.onclick = () => toggle(b.dataset.unsave)));
    const exp = $("#exportnotes");
    if (exp)
      exp.onclick = () =>
        download(
          "navalsteel-citations.md",
          items
            .map(
              (h) =>
                "## " +
                h.title +
                " — page " +
                h.page +
                "\n\n" +
                h.paragraph +
                "\n\n" +
                new URL(
                  "assets/" + h.doc + ".pdf#page=" + h.page,
                  location.href,
                ),
            )
            .join("\n\n"),
          "text/markdown",
        );
  }
  function renderHits() {
    output.innerHTML = results
      .map(
        (h) =>
          '<article class="evidencehit">' +
          ref(h) +
          "<p>" +
          escapeHTML(snippet(h.paragraph, $("#reportquery").value)) +
          '</p><button class="ghost" data-save="' +
          passageKey(h) +
          '">' +
          (stored.includes(passageKey(h))
            ? "Remove saved passage"
            : "Save passage") +
          "</button></article>",
      )
      .join("");
    output
      .querySelectorAll("[data-save]")
      .forEach((b) => (b.onclick = () => toggle(b.dataset.save)));
  }
  function toggle(key) {
    const next = stored.includes(key)
      ? stored.filter((k) => k !== key)
      : [...stored, key];
    try {
      localStorage.setItem(shelfKey, JSON.stringify(next));
      stored = next;
      renderHits();
      renderShelf();
    } catch {
      status.textContent =
        "This browser could not save the passage. Open its PDF page to keep the reference.";
    }
  }
  async function init() {
    try {
      docs = await reports();
      if (shelf.isConnected) renderShelf();
    } catch {
      if (shelf.isConnected)
        shelf.textContent =
          "The report index could not load. Try the search again.";
    }
  }
  init();
  $("#reportform").onsubmit = async (e) => {
    e.preventDefault();
    const q = $("#reportquery").value.trim(),
      scope = $("#reportscope").value;
    status.textContent = "Searching…";
    try {
      docs = await reports();
      if (!output.isConnected) return;
      results = searchPassages(docs, q, scope);
      status.textContent = results.length
        ? "Showing " +
          results.length +
          " matching passage" +
          (results.length === 1 ? "" : "s") +
          "."
        : "No matching passage. Try a property, process, or method name.";
      renderHits();
      renderShelf();
    } catch {
      status.textContent = "The report index could not load. Try again.";
    }
  };
  const field = $("#papers");
  function records() {
    const q = field.value.trim().toLowerCase();
    const match = data.records.filter((r) =>
      (r.steel.name + " " + Object.values(r.paper).join(" "))
        .toLowerCase()
        .includes(q),
    );
    $("#records").innerHTML =
      match
        .map(
          (r) =>
            "<details><summary>" +
            escapeHTML(r.steel.name) +
            " · " +
            escapeHTML(r.paper.year) +
            "</summary><h3>" +
            escapeHTML(r.paper.title) +
            '</h3><p class="note">' +
            escapeHTML(r.paper.author || "") +
            "</p>" +
            r.properties
              .map(
                (p) =>
                  '<div class="evidencehit"><span class="pill">' +
                  escapeHTML(p.status || "UNKNOWN") +
                  "</span><p><strong>" +
                  escapeHTML(p.property.replaceAll("_", " ")) +
                  "</strong> · " +
                  escapeHTML(
                    p.value == null ? "Unreported" : p.value + " " + p.unit,
                  ) +
                  (p.temperature_C != null
                    ? " at " + escapeHTML(p.temperature_C) + " °C"
                    : "") +
                  "</p><p>" +
                  escapeHTML(
                    p.evidence?.claim || "No evidence statement recorded.",
                  ) +
                  '</p><p class="note">' +
                  (p.evidence?.source_page
                    ? "Recorded source page " +
                      escapeHTML(p.evidence.source_page)
                    : "Source page unrecorded") +
                  (p.is_proxy_for
                    ? " · Proxy for " +
                      escapeHTML(p.is_proxy_for.replaceAll("_", " "))
                    : "") +
                  "</p></div>",
              )
              .join("") +
            '<button class="ghost group" data-record="' +
            escapeHTML(r.record_id) +
            '">Download source record</button></details>',
        )
        .join("") || '<p class="hint">No matching records.</p>';
    document.querySelectorAll("[data-record]").forEach(
      (b) =>
        (b.onclick = () =>
          download(
            b.dataset.record + ".json",
            JSON.stringify(
              match.find((r) => r.record_id === b.dataset.record),
              null,
              2,
            ),
          )),
    );
  }
  field.oninput = records;
  records();
}
const sample =
  "Carbon (C): 0.04 wt%\nNickel (Ni): 3.50 wt%\nCopper (Cu): 1.55 wt%\nManganese (Mn): 0.85 wt%\nSilicon (Si): 0.25 wt%\nChromium (Cr): 0.60 wt%\nMolybdenum (Mo): 0.55 wt%\nNiobium (Nb): 0.035 wt%\nYield strength: 690 MPa\nTensile strength: 780 MPa\nCharpy impact energy: 140 J";
async function pdfText(file) {
  const pdfjs = await import("./pdf/pdf.min.mjs");
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    "./pdf/pdf.worker.min.mjs",
    location.href,
  ).href;
  const pdf = await pdfjs.getDocument({
    data: await file.arrayBuffer(),
    isEvalSupported: false,
    useSystemFonts: true,
  }).promise;
  try {
    if (pdf.numPages > 80) throw Error("Choose a PDF with up to 80 pages.");
    const pages = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      pages.push(
        content.items.map((v) => v.str + (v.hasEOL ? "\n" : " ")).join(""),
      );
      page.cleanup();
    }
    const text = pages.join("\n");
    if (!text.trim())
      throw Error("This PDF has no text layer. Paste OCR text to continue.");
    return text;
  } finally {
    await pdf.destroy();
  }
}
function extract() {
  main.innerHTML =
    pageHead(
      pages.extract,
      "Read alloy chemistry and mechanical properties from a lab document. Files stay in your browser.",
    ) +
    panel(
      "Source document",
      '<form id="extractform"><label class="field group">Select a file<input id="docfile" class="file" type="file" accept=".pdf,.txt,.md,.csv,.tsv,.json"></label><p class="hint">PDF, text, Markdown, CSV, TSV or JSON · 10 MB maximum</p><label class="field group">Or paste material data<textarea id="doctext" placeholder="Paste a composition or test report…"></textarea></label><div class="actions"><button class="button primary">Extract record</button><button type="button" class="ghost" id="sample">Use sample</button></div><p id="extractstatus" role="status" class="status"></p></form>',
    ) +
    '<div class="results" id="extracted"></div>';
  function show(r) {
    const comp = Object.entries(r.composition).filter(([k]) => k !== "Fe"),
      known = modelKeys.some((k) => r.properties[k] != null);
    $("#extracted").innerHTML = panel(
      escapeHTML(state.extractionName),
      (!comp.length && !known
        ? '<p class="hint">No supported composition or mechanical properties were found.</p>'
        : '<div class="metrics">' +
          modelKeys
            .map((k, i) =>
              metric(
                names[i],
                r.properties[k] != null
                  ? fmt(r.properties[k]) + " " + units[i]
                  : "Unreported",
              ),
            )
            .join("") +
          "</div>") +
        (comp.length
          ? '<p class="smallcap">Extracted composition</p><div class="infoRows">' +
            comp.map(([k, v]) => row(k, fmt(v) + " wt%")).join("") +
            "</div>"
          : "") +
        '<p class="note">Review against the source. For heat tables, the extractor reads the first data row.</p><button class="ghost group" id="dlext">Export record</button>',
    );
    $("#dlext").onclick = () =>
      download(
        "extracted-material.json",
        JSON.stringify({ source: state.extractionName, ...r }, null, 2),
      );
  }
  if (state.extraction) show(state.extraction);
  const file = $("#docfile"),
    ta = $("#doctext"),
    status = $("#extractstatus"),
    form = $("#extractform");
  function clear() {
    state.extraction = null;
    $("#extracted").innerHTML = "";
    status.textContent = "";
    state.extractVersion = (state.extractVersion || 0) + 1;
  }
  file.onchange = () => {
    if (file.files.length) ta.value = "";
    clear();
  };
  ta.oninput = () => {
    file.value = "";
    clear();
  };
  $("#sample").onclick = () => {
    file.value = "";
    ta.value = sample;
    clear();
    ta.focus();
  };
  form.onsubmit = async (e) => {
    e.preventDefault();
    const f = file.files[0],
      button = $("button", form),
      v = state.extractVersion;
    button.disabled = true;
    try {
      if (!f && !ta.value.trim())
        throw Error("Choose a file, paste text, or use the sample.");
      if (f?.size > 10 * 1024 * 1024 || ta.value.length > 10 * 1024 * 1024)
        throw Error("Choose a source smaller than 10 MB.");
      status.textContent = "Reading document…";
      let title = f?.name || "Pasted text",
        filename = f?.name || "pasted.txt";
      if (!/\.(pdf|txt|md|csv|tsv|json)$/i.test(filename))
        throw Error("Choose a supported file format.");
      let text;
      if (f && /\.pdf$/i.test(filename)) {
        text = await pdfText(f);
        filename = "pdf-text.txt";
      } else {
        text = f ? await f.text() : ta.value;
      }
      if (/\.json$/i.test(filename)) JSON.parse(text);
      const result = await run("extract", { text, filename });
      if (status.isConnected && state.extractVersion === v) {
        state.extraction = result;
        state.extractionName = title;
        show(result);
        status.textContent = "Extraction complete.";
      }
    } catch (err) {
      status.textContent = err.message;
    } finally {
      button.disabled = false;
    }
  };
}
function project() {
  main.innerHTML =
    pageHead(
      "Project & validation",
      "UGP 497 · Materials Science & Engineering, IIT Kanpur.",
    ) +
    '<div class="stack">' +
    panel(
      "Project team",
      '<div class="infoRows">' +
        row("Author", "Dipanshu Raj") +
        row("Faculty mentor", "Prof. Amarendra Kumar Singh") +
        "</div>",
    ) +
    panel(
      "Model validation",
      '<p class="hint">Mean absolute error across 40 withheld heat records. Holding out each named grade or research series in turn tests transfer to an unseen group.</p><div id="validation" role="status">Loading evaluation…</div>',
    ) +
    panel(
      "Report coverage",
      '<p class="hint">The public workspace supports heat comparison, model prediction, constrained Pareto search, extraction, mechanism records and page-linked report search. The Python edition adds dissertation retrieval and report generation.</p><p class="hint">The proposed 100–200-paper corpus, PostgreSQL/pgvector deployment, full contradiction detection, CALPHAD and kinetic calculations, Bayesian active learning, and laboratory feedback remain research milestones.</p>',
    ) +
    panel(
      "Project documents",
      '<div class="actions group"><a class="ghost" href="assets/design-report.pdf" target="_blank" rel="noopener">Detailed project report</a><a class="ghost" href="assets/ugp497-report.pdf" target="_blank" rel="noopener">UGP final report</a><a class="ghost" href="#literature">Search report pages</a></div>',
    ) +
    "</div>";
  const el = $("#validation");
  fetch("family-validation.json")
    .then((r) => {
      if (!r.ok) throw Error();
      return r.json();
    })
    .then((v) => {
      el.innerHTML =
        '<div class="tablewrap group"><table><thead><tr><th>Property</th><th>Random folds</th><th>Held-out group</th></tr></thead><tbody>' +
        modelKeys
          .map(
            (k, i) =>
              '<tr><th scope="row">' +
              names[i] +
              "</th><td>" +
              v.pooled_mae.row_wise[k].toFixed(1) +
              " " +
              units[i] +
              "</td><td>" +
              v.pooled_mae.family_holdout[k].toFixed(1) +
              " " +
              units[i] +
              "</td></tr>",
          )
          .join("") +
        '</tbody></table></div><p class="note">Eight named groups. Related steel grades may still appear in training. These errors describe this dataset; model spread is not a calibrated prediction interval.</p><a class="tablelink" href="family-validation.json" download>Download evaluation data</a>';
    })
    .catch(() => {
      el.textContent = "Evaluation data could not be loaded.";
    });
}
function navigate(page) {
  if (location.hash === "#" + page) route();
  else location.hash = page;
}
function route() {
  const key = location.hash.slice(1).split("?")[0];
  state.page = Object.hasOwn(pages, key) ? key : "overview";
  const render = {
    overview,
    compare: comparePage,
    library,
    studio,
    frontier,
    evidence,
    extract,
    literature,
    project,
  }[state.page];
  for (const a of document.querySelectorAll("#nav a, .dock a, .topstudio")) {
    const active = a.hash === "#" + state.page;
    a.classList.toggle("active", active);
    if (active) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  document.body.classList.toggle("landing", state.page === "overview");
  document.title = pages[state.page] + " · NavalSteel AI";
  menu(false);
  render();
  window.scrollTo(0, 0);
}
main.onclick = (e) => {
  const p = e.target.closest("[data-point]");
  if (p) {
    state.heat = p.dataset.point;
    overview();
    return;
  }
  const b = e.target.closest("[data-heat]");
  if (b) inspect(heats.find((r) => r.alloy_name === b.dataset.heat));
};
main.onkeydown = (e) => {
  const p = e.target.closest("[data-point]");
  if (p && ["Enter", " "].includes(e.key)) {
    e.preventDefault();
    state.heat = p.dataset.point;
    overview();
    main.querySelector('[data-point="' + state.heat + '"]').focus();
  }
};
try {
  const resp = await fetch("atlas.json");
  if (!resp.ok) throw Error();
  data = await resp.json();
  heats = data.heats;
  route();
  window.addEventListener("hashchange", route);
} catch {
  main.innerHTML =
    '<p class="empty">Heat records could not be loaded. <button class="ghost" id="reload">Retry</button></p>';
  $("#reload").onclick = () => location.reload();
}
if (window.parent !== window) {
  const notify = (type, extra = {}) =>
    window.parent.postMessage(
      { isStreamlitMessage: true, type, ...extra },
      "*",
    );
  notify("streamlit:componentReady", { apiVersion: 1 });
  const resize = () =>
    notify("streamlit:setFrameHeight", {
      height: Math.max(
        800,
        document.querySelector("header").offsetHeight +
          main.offsetHeight +
          document.querySelector("footer").offsetHeight,
      ),
    });
  new ResizeObserver(resize).observe(main);
  resize();
}
