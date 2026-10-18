// main.js - embeds every Vega-Lite chart and links the year selector to the maps.

const EMBED_OPTIONS = { mode: "vega-lite", actions: { export: true, source: true, compiled: false, editor: true }, renderer: "canvas" };

// chart div id -> spec file
const CHARTS = {
  vis_stream: "js/01_streamgraph.vg.json",
  vis_butterfly: "js/02_butterfly.vg.json",
  vis_gantt: "js/03_gantt.vg.json",
  vis_dots: "js/05_dot_map_eras.vg.json",
  vis_lollipop: "js/10_lollipop.vg.json",
  vis_bump: "js/09_bump.vg.json",
  vis_index: "js/11_indexed_line.vg.json",
  vis_waffle: "js/13_waffle.vg.json",
  vis_cliff: "js/14_cliff.vg.json",
  vis_heatmap: "js/12_heatmap.vg.json",
  vis_languages: "js/16_languages.vg.json",
};

// charts that listen to the year selector (they all have yr0 / yr1 parameters)
const LINKED = {
  vis_symbol: "js/06_symbol_map.vg.json",
  vis_choropleth: "js/07_choropleth.vg.json",
  vis_bin: "js/08_bin_map.vg.json",
};

const OVERVIEW = { id: "vis_overview", file: "js/04_overview.vg.json" };

const linkedViews = [];
let overviewView = null;

function showError(id, err) {
  console.error(id, err);
  const el = document.getElementById(id);
  if (el) el.innerHTML = '<p class="caveat">Sorry, this chart could not be loaded.</p>';
}

// ---- plain charts -------------------------------------------------------
Object.entries(CHARTS).forEach(([id, file]) => {
  vegaEmbed("#" + id, file, EMBED_OPTIONS).catch((e) => showError(id, e));
});

// ---- year selector -> maps ---------------------------------------------
function setYears(a, b) {
  a = Math.round(a);
  b = Math.round(b);
  document.getElementById("range-label").textContent = a + "–" + b;
  linkedViews.forEach((v) => v.signal("yr0", a).signal("yr1", b).runAsync());
}

// Find the signal that holds the brushed year range, e.g. brush_year
function brushSignalName(view) {
  const names = Object.keys(view.getState({ signals: () => true }).signals);
  return names.find((n) => /^brush_year$/.test(n));
}

Promise.all(
  Object.entries(LINKED).map(([id, file]) =>
    vegaEmbed("#" + id, file, EMBED_OPTIONS).then((r) => {
      linkedViews.push(r.view);

      // choropleth only: update the caption when the measure changes
      if (id === "vis_choropleth") {
        const caption = document.getElementById("measure-caption");
        r.view.addSignalListener("measure", (_, v) => {
          caption.innerHTML =
            v === "count"
              ? "Shading shows the <strong>number of titles</strong> in each state. States with no titles in print are grey."
              : "Shading shows <strong>titles per 100,000 km&sup2;</strong>, which allows for the very different sizes of the states. Grey means no titles in print.";
        });
      }
      return r.view;
    }).catch((e) => showError(id, e))
  )
).then(() => {
  vegaEmbed("#" + OVERVIEW.id, OVERVIEW.file, EMBED_OPTIONS)
    .then((r) => {
      overviewView = r.view;
      const sig = brushSignalName(r.view);
      if (!sig) { console.warn("brush signal not found"); return; }

      const read = (value) => {
        // value is [a, b] when a range is brushed and null when the brush is cleared
        if (value && value.length === 2) setYears(value[0], value[1]);
        else setYears(1803, 1954);
      };
      r.view.addSignalListener(sig, (_, v) => read(v));
      read(r.view.signal(sig));   // start in sync with the initial brush
    })
    .catch((e) => showError(OVERVIEW.id, e));
});

// ---- include / exclude the Victorian 1914-1918 slices -------------------
document.getElementById("toggle-slices").addEventListener("change", (e) => {
  linkedViews.forEach((v) => v.signal("show_slices", e.target.checked).runAsync());
});

// ---- preset buttons -----------------------------------------------------
document.querySelectorAll(".preset").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (!overviewView) return;
    const a = +btn.dataset.from, b = +btn.dataset.to;
    const xScale = overviewView.scale("x");
    // moving the brush rectangle updates brush_year, which updates the maps
    overviewView.signal("brush_x", [xScale(a), xScale(b)]).runAsync();
  });
});
