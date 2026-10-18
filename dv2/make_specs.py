"""
make_specs.py - writes every Vega-Lite specification to js/*.vg.json
(pretty-printed so the JSON is easy to read in the GitHub repo).

Change the colours / fonts once here, rerun `python make_specs.py`,
and every chart stays consistent.
"""
import csv
import json
from pathlib import Path

OUT = Path("js")
OUT.mkdir(exist_ok=True)
SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"

# ------------------------------------------------------------------ style
BG = "#f6f1e7"          # newsprint cream (same as the page)
INK = "#2b2620"
MUTED = "#6f665a"
GRID = "#e2dac6"
LAND = "#e4dcc8"        # base-map land colour
BODY_FONT = "Source Serif 4, Georgia, serif"
HEAD_FONT = "Playfair Display, Georgia, serif"

# one colour per state, used on every chart (colour-blind-safe, Okabe-Ito based)
STATE_ORDER = ["New South Wales", "Victoria", "Queensland", "South Australia",
               "Western Australia", "Tasmania", "NT and ACT"]
STATE_COLOURS = ["#0072B2", "#D55E00", "#6b4fa0", "#CC79A7", "#E69F00", "#56B4E9", "#8a8478"]
# full list for charts that keep NT and ACT separate (maps)
STATE_ORDER_8 = STATE_ORDER[:6] + ["Northern Territory", "Australian Capital Territory"]
STATE_COLOURS_8 = STATE_COLOURS[:6] + ["#8a8478", "#5b574e"]
SLICE = "Victorian papers in Trove only for 1914\u20131918"
SLICE_COLOUR = "#c4baa4"

# COLOUR RULES (one meaning per colour across the whole page)
#   state colours above      = which state (only used for states)
#   TEAL                     = the value to notice: launches, highlighted bars, key numbers, regional towns
#   teal ramp (TEAL_RAMP)    = how many titles (maps and heatmap)
#   greys / tans             = everything else: closures, context, other categories
TEAL = "#21736d"
TEAL_RAMP = ["#e3f1ee", "#7fbdb4", "#21736d", "#0e3f3b"]
LAUNCH = TEAL
CLOSE = "#5b574e"       # dark grey = closed

CONFIG = {
    "background": "transparent",
    "view": {"stroke": None},
    "font": BODY_FONT,
    "title": {"font": HEAD_FONT, "fontSize": 16, "color": INK, "anchor": "start", "fontWeight": 700,
              "subtitleFont": BODY_FONT, "subtitleFontWeight": 400, "subtitleColor": MUTED, "subtitleFontSize": 12.5, "subtitlePadding": 6, "offset": 10},
    "axis": {"labelFont": BODY_FONT, "titleFont": BODY_FONT, "labelColor": MUTED,
             "titleColor": MUTED, "labelFontSize": 12, "titleFontSize": 12,
             "gridColor": GRID, "domainColor": "#b9ae96", "tickColor": "#b9ae96"},
    "legend": {"labelFont": BODY_FONT, "titleFont": BODY_FONT, "labelColor": INK,
               "titleColor": MUTED, "labelFontSize": 12, "titleFontSize": 12, "symbolType": "square", "symbolOpacity": 1},
    "text": {"font": BODY_FONT},
}

STATE_SCALE = {"domain": STATE_ORDER, "range": STATE_COLOURS}
STATE_SCALE_8 = {"domain": STATE_ORDER_8, "range": STATE_COLOURS_8}

TOPO = {"url": "data/australia_states.topojson",
        "format": {"type": "topojson", "feature": "states"}}

ACTIVE = "datum.start <= yr1 && datum.end >= yr0 && (show_slices || datum.wwi_slice == 0)"   # a title was running during the chosen years
YEAR_PARAMS = [{"name": "yr0", "value": 1850}, {"name": "yr1", "value": 1900}, {"name": "show_slices", "value": True}]


def column(path, field):
    with open(path, newline="") as f:
        return [r[field] for r in csv.DictReader(f)]


def write(name, spec):
    spec = {"$schema": SCHEMA, **spec, "config": CONFIG}
    (OUT / name).write_text(json.dumps(spec, indent=2))
    print("wrote", name)


def base_layer(fill=LAND):
    """Grey states underneath a data layer; hovering shows a 'no data' note."""
    return {
        "data": TOPO,
        "transform": [{"calculate": "'No data: ' + datum.properties.STE_NAME21", "as": "note"}],
        "mark": {"type": "geoshape", "fill": fill, "stroke": "white", "strokeWidth": 1},
        "encoding": {"tooltip": {"field": "note"}},
    }


def outline_layer():
    return {"data": TOPO, "mark": {"type": "geoshape", "fill": None, "stroke": "#8f866f", "strokeWidth": 0.6}}


# ===================================================== 1. STREAMGRAPH
events = [
    {"year": 1851, "label": "Gold rushes begin", "row": 6},
    {"year": 1901, "label": "Federation", "row": 6},
    {"year": 1914, "label": "War begins", "row": 6},
    {"year": 1939, "label": "War begins", "row": 6},
]
write("01_streamgraph.vg.json", {
    "title": {"text": "Articles preserved in Trove, by state, per year", "subtitle": "Thickness of each band = number of articles"},
    "width": "container", "height": 380,
    "data": {"url": "data/articles_by_year_state.csv"},
    "layer": [
        {
            "mark": {"type": "area", "interpolate": "monotone", "opacity": 0.92},
            "encoding": {
                "x": {"field": "year", "type": "quantitative", "title": None,
                      "axis": {"format": "d", "tickCount": 10, "grid": False},
                      "scale": {"domain": [1810, 1954], "nice": False}},
                "y": {"aggregate": "sum", "field": "total", "type": "quantitative",
                      "stack": "center", "axis": None},
                "color": {"field": "group", "type": "nominal", "title": "State",
                          "scale": STATE_SCALE, "legend": {"orient": "top", "columns": 4, "title": None, "labelLimit": 260, "labelExpr": "datum.label == 'NT and ACT' ? 'Northern Territory and Canberra' : datum.label"}},
                "tooltip": [{"field": "group", "title": "State"}, {"field": "year", "title": "Year", "format": "d"},
                            {"field": "total", "title": "Articles", "format": ","}],
            },
        },
        {
            "data": {"values": events},
            "mark": {"type": "rule", "strokeDash": [4, 3], "color": INK, "strokeWidth": 1},
            "encoding": {"x": {"field": "year", "type": "quantitative"}},
        },
        {   # event labels along the top edge; Federation sits left of its line so it does not run into WWI
            "data": {"values": [e for e in events if e["year"] != 1901]},
            "mark": {"type": "text", "align": "left", "dx": 4, "y": 8, "baseline": "top", "fontSize": 12,
                     "fontStyle": "italic", "color": INK},
            "encoding": {"x": {"field": "year", "type": "quantitative"}, "text": {"field": "label"}},
        },
        {
            "data": {"values": [e for e in events if e["year"] == 1901]},
            "mark": {"type": "text", "align": "right", "dx": -4, "y": 8, "baseline": "top", "fontSize": 12,
                     "fontStyle": "italic", "color": INK},
            "encoding": {"x": {"field": "year", "type": "quantitative"}, "text": {"field": "label"}},
        },
    ],
})

# ======================================================= 2. BUTTERFLY
# long-format data: launched titles are negative (drawn left), closed titles positive (drawn right).
# The grey segment is the Victorian papers that Trove holds only for 1914-1918.
lc_colour = {"domain": ["Titles launched", "Titles closed", SLICE], "range": [LAUNCH, CLOSE, SLICE_COLOUR]}
DEC = [f"{d}s" for d in range(1830, 1950, 10)]
write("02_butterfly.vg.json", {
    "title": {"text": "Newspaper titles launched and closed, by decade",
              "subtitle": ["The 1890s had the most launches (247).",
                           "From the 1920s, more titles closed than opened."]},
    "width": "container", "height": 340,
    "encoding": {"y": {"field": "label", "type": "ordinal", "title": None, "sort": DEC,
                       "axis": {"labelFontSize": 13, "domain": False, "ticks": False}}},
    "layer": [
        {
            "data": {"url": "data/butterfly_long.csv"},
            "mark": {"type": "bar", "height": {"band": 0.72}},
            "encoding": {
                "x": {"field": "value", "type": "quantitative", "title": "\u2190 Titles launched        Titles closed \u2192",
                      "axis": {"values": [-300, -200, -100, 0, 100, 200, 300], "labelExpr": "abs(datum.value)"}},
                "color": {"field": "series", "type": "nominal", "scale": lc_colour,
                          "legend": {"orient": "top", "title": None, "columns": 2, "labelLimit": 380}},
                "order": {"field": "stack_order", "type": "quantitative", "sort": "ascending"},
                "tooltip": [{"field": "label", "title": "Decade"}, {"field": "series", "title": "Group"},
                            {"field": "value", "title": "Titles (negative = launched)"}, {"field": "net", "title": "Net change in decade"}],
            },
        },
        {   # totals at the bar ends and the net change on the right
            "data": {"url": "data/titles_launched_closed_by_decade.csv"},
            "transform": [{"calculate": "-datum.Launched", "as": "neg"}],
            "mark": {"type": "text", "align": "right", "dx": -4, "fontSize": 11, "color": INK},
            "encoding": {"x": {"field": "neg", "type": "quantitative"}, "text": {"field": "Launched"}},
        },
        {
            "data": {"url": "data/titles_launched_closed_by_decade.csv"},
            "mark": {"type": "text", "align": "left", "dx": 4, "fontSize": 11, "color": INK},
            "encoding": {"x": {"field": "Closed", "type": "quantitative"}, "text": {"field": "Closed"}},
        },
        {
            "data": {"url": "data/titles_launched_closed_by_decade.csv"},
            "transform": [{"calculate": "'Net ' + (datum.net > 0 ? '+' : '\u2212') + abs(datum.net)", "as": "netlabel"},
                          {"calculate": "340", "as": "netx"}],
            "mark": {"type": "text", "align": "left", "fontSize": 12, "fontStyle": "italic"},
            "encoding": {"x": {"field": "netx", "type": "quantitative"}, "text": {"field": "netlabel"},
                         "color": {"condition": {"test": "datum.net < 0", "value": CLOSE}, "value": LAUNCH}},
        },
    ],
})

# ============================================================ 3. GANTT
GY = {"field": "label", "type": "nominal", "title": None,
      "sort": column("data/longest_running_titles.csv", "label"),
      "axis": {"labelLimit": 250, "ticks": False, "domain": False, "labelFontSize": 12}}
write("03_gantt.vg.json", {
    "title": {"text": "The 15 longest-running newspapers in Trove", "subtitle": "Bars show each title's run in Trove; the number is its length in years"},
    "width": "container", "height": 400,
    "data": {"url": "data/longest_running_titles.csv"},
    "layer": [
        {"mark": {"type": "bar", "height": {"band": 0.6}, "cornerRadius": 2},
         "encoding": {
             "y": GY,
             "x": {"field": "start", "type": "quantitative", "title": None,
                   "scale": {"domain": [1835, 2020], "nice": False}, "axis": {"format": "d", "tickCount": 8}},
             "x2": {"field": "end"},
             "color": {"field": "state", "type": "nominal", "scale": STATE_SCALE_8,
                       "legend": {"orient": "top", "title": None}},
             "tooltip": [{"field": "label", "title": "Newspaper"}, {"field": "place", "title": "Place"},
                         {"field": "state", "title": "State"},
                         {"field": "start", "title": "First year", "format": "d"},
                         {"field": "end", "title": "Last year", "format": "d"},
                         {"field": "years", "title": "Years in Trove"},
                         {"field": "articles", "title": "Articles in Trove", "format": ","}]}},
        {"mark": {"type": "text", "align": "left", "dx": 5, "fontSize": 11, "color": INK},
         "encoding": {"y": GY, "x": {"field": "end", "type": "quantitative"},
                      "text": {"field": "years", "type": "quantitative"}}},
        {"data": {"values": [{"x": 1954}]},
         "mark": {"type": "rule", "strokeDash": [4, 3], "color": INK},
         "encoding": {"x": {"field": "x", "type": "quantitative"}}},
        {"data": {"values": [{"x": 1954, "note": "1954: most of Trove stops here"}]},
         "mark": {"type": "text", "align": "left", "dx": 6, "dy": -2, "baseline": "bottom", "fontStyle": "italic", "fontSize": 11.5, "y": "height",
                  "color": INK},
         "encoding": {"x": {"field": "x", "type": "quantitative"}, "text": {"field": "note"}}},
    ],
})

# ========================================== 4. OVERVIEW (linked brush)
write("04_overview.vg.json", {
    "title": {"text": "Drag across the chart to choose the years shown on the maps below",
              "fontSize": 13, "font": BODY_FONT, "fontStyle": "italic", "fontWeight": 400},
    "width": "container", "height": 130,
    "data": {"url": "data/active_titles_by_year_state.csv"},
    "params": [{"name": "brush", "value": {"year": [1850, 1900]},
                "select": {"type": "interval", "encodings": ["x"]}}],
    "mark": {"type": "area", "interpolate": "monotone"},
    "encoding": {
        "x": {"field": "year", "type": "quantitative", "title": None,
              "axis": {"format": "d", "tickCount": 15, "grid": False}, "scale": {"domain": [1803, 1954], "nice": False}},
        "y": {"aggregate": "sum", "field": "titles", "type": "quantitative", "title": "Titles in print",
              "axis": {"tickCount": 3}},
        "color": {"field": "group", "type": "nominal", "title": None,
                  "scale": {"domain": STATE_ORDER + [SLICE], "range": STATE_COLOURS + [SLICE_COLOUR]},
                  "legend": {"orient": "top", "columns": 4, "labelLimit": 360, "labelExpr": "datum.label == 'NT and ACT' ? 'Northern Territory and Canberra' : datum.label"}},
        "order": {"field": "group", "sort": "descending"},
        "tooltip": [{"field": "group", "title": "State"}, {"field": "year", "format": "d", "title": "Year"},
                    {"field": "titles", "title": "Titles in print"}],
    },
})

# ============================== 5. DOT MAP, SMALL MULTIPLES BY ERA
# three side-by-side panels (one per era), each a base map + one dot per title
ERAS = [("1. Before 1860", "Before 1860"), ("2. 1860-1899", "1860\u20131899"), ("3. 1900 onwards", "1900 onwards")]


def era_panel(era, label, show_legend):
    return {
        "title": {"text": label, "font": HEAD_FONT, "fontSize": 15, "anchor": "middle"},
        "width": 320, "height": 300,
        "projection": {"type": "mercator", "center": [133.5, -27.5], "scale": 430, "translate": [160, 150]},
        "layer": [
            {"data": TOPO, "mark": {"type": "geoshape", "fill": LAND, "stroke": "white", "strokeWidth": 0.8}},
            {
                "data": {"url": "data/titles.csv"},
                "transform": [{"filter": f"datum.lat != null && datum.era == '{era}'"}],
                "mark": {"type": "circle", "opacity": 0.6, "size": 22},
                "encoding": {
                    "longitude": {"field": "lon", "type": "quantitative"},
                    "latitude": {"field": "lat", "type": "quantitative"},
                    "color": {"field": "place_type", "type": "nominal", "title": None,
                              "scale": {"domain": ["Capital city", "Regional town"], "range": ["#1d1a16", TEAL]},
                              "legend": None},
                    "tooltip": [{"field": "short", "title": "Title"}, {"field": "place", "title": "Place"},
                                {"field": "start", "title": "Started", "format": "d"}],
                },
            },
        ],
    }


write("05_dot_map_eras.vg.json", {
    "title": {"text": "Where newspapers first appeared", "subtitle": "One dot per title, placed by the year the title started"},
    "hconcat": [era_panel(e, l, i == 1) for i, (e, l) in enumerate(ERAS)],
    "resolve": {"scale": {"color": "shared"}},
})

# ===================== 6. PROPORTIONAL SYMBOL MAP (zoom + linked years)
FOCUS = [
    ([134, -28.5, 760], "All of Australia"),
    ([146.5, -35.5, 2600], "South-east: Victoria, NSW, Tasmania"),
    ([145.3, -37.3, 6200], "Melbourne and Victoria"),
    ([151.0, -33.2, 7000], "Sydney and the Hunter"),
    ([138.6, -34.4, 5200], "Adelaide and the Murray"),
    ([119.5, -31.0, 3400], "Perth and the goldfields"),
    ([151.5, -24.5, 1500], "Queensland coast"),
]
write("06_symbol_map.vg.json", {
    "title": {"text": "Titles in print, town by town"},
    "width": 620, "height": 520,
    "params": YEAR_PARAMS + [{
        "name": "focus", "value": FOCUS[0][0],
        "bind": {"input": "select", "options": [f[0] for f in FOCUS], "labels": [f[1] for f in FOCUS],
                 "name": "Zoom to: "},
    }],
    "projection": {"type": "mercator", "center": {"expr": "[focus[0], focus[1]]"}, "scale": {"expr": "focus[2]"}},
    "layer": [
        base_layer(),
        {
            "data": {"url": "data/titles.csv"},
            "transform": [
                {"filter": "datum.lat != null && " + ACTIVE},
                {"aggregate": [{"op": "count", "as": "n"}, {"op": "sum", "field": "articles", "as": "arts"}],
                 "groupby": ["place", "state", "lat", "lon"]},
            ],
            "mark": {"type": "circle", "opacity": 0.72, "stroke": "white", "strokeWidth": 0.6},
            "encoding": {
                "longitude": {"field": "lon", "type": "quantitative"},
                "latitude": {"field": "lat", "type": "quantitative"},
                "size": {"field": "n", "type": "quantitative", "title": "Titles in print",
                         "scale": {"type": "sqrt", "domain": [0, 120], "range": [0, 1900]},
                         "legend": {"values": [1, 10, 50, 100], "orient": "bottom-left", "symbolType": "circle", "symbolFillColor": "#b9ae96", "symbolStrokeColor": "#8f866f", "symbolOpacity": 0.9}},
                "color": {"field": "state", "type": "nominal", "scale": STATE_SCALE_8, "legend": None},
                "order": {"field": "n", "sort": "descending"},
                "tooltip": [{"field": "place", "title": "Place"}, {"field": "state", "title": "State"},
                            {"field": "n", "title": "Titles in print"},
                            {"field": "arts", "title": "Articles in Trove", "format": ","}],
            },
        },
        {
            "data": {"url": "data/titles.csv"},
            "transform": [
                {"filter": "datum.lat != null && " + ACTIVE},
                {"aggregate": [{"op": "count", "as": "n"}], "groupby": ["place", "lat", "lon"]},
                {"filter": "datum.n >= 14"},
            ],
            "mark": {"type": "text", "dy": -26, "fontSize": 11.5, "fontStyle": "italic", "fill": INK},
            "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                         "latitude": {"field": "lat", "type": "quantitative"},
                         "text": {"field": "place"}},
        },
    ],
})

# ============================================ 7. CHOROPLETH (linked)
LOOK = [
    {"filter": "datum.state != 'International' && datum.state != 'National' && " + ACTIVE},
    {"aggregate": [{"op": "count", "as": "n"}], "groupby": ["state"]},
    {"lookup": "state", "from": {"data": {"url": "data/state_area.csv"}, "key": "state", "fields": ["area_km2"]}},
    {"calculate": "datum.n / datum.area_km2 * 100000", "as": "per100k"},
    {"calculate": "measure == 'count' ? datum.n : datum.per100k", "as": "shade"},
    {"lookup": "state", "from": {"data": TOPO, "key": "properties.STE_NAME21"}, "as": "geo"},
]
write("07_choropleth.vg.json", {
    "title": {"text": "Titles in print, by state"},
    "width": "container", "height": 330,
    "params": YEAR_PARAMS + [{
        "name": "measure", "value": "per100k",
        "bind": {"input": "select", "options": ["per100k", "count"],
                 "labels": ["Titles per 100,000 km² (fair comparison)", "Number of titles"], "name": "Show: "},
    }],
    "projection": {"type": "mercator"},
    "layer": [
        base_layer(),
        {
            "data": {"url": "data/titles.csv"},
            "transform": LOOK,
            "mark": {"type": "geoshape", "stroke": "white", "strokeWidth": 1},
            "encoding": {
                "shape": {"field": "geo", "type": "geojson"},
                "color": {"field": "shade", "type": "quantitative", "title": "Darker = more",
                          "scale": {"type": "sqrt", "range": ["#e3f1ee", "#8cc4bb", "#4aa093"], "domainMin": 0},
                          "legend": {"orient": "bottom-left", "format": "~s", "gradientLength": 120}},
                "tooltip": [{"field": "state", "title": "State"},
                            {"field": "n", "title": "Titles in print"},
                            {"field": "per100k", "title": "Per 100,000 km²", "format": ".1f"}],
            },
        },
        {
            "data": {"values": [
                {"s": ["New South", "Wales"], "lon": 146.5, "lat": -32.3}, {"s": "Victoria", "lon": 144.8, "lat": -36.9},
                {"s": "Queensland", "lon": 144.5, "lat": -22.5}, {"s": ["South", "Australia"], "lon": 135.0, "lat": -30.0},
                {"s": ["Western", "Australia"], "lon": 122.0, "lat": -25.5}, {"s": "Tasmania", "lon": 146.6, "lat": -42.1},
                {"s": ["Northern", "Territory"], "lon": 133.5, "lat": -19.5}]},
            "mark": {"type": "text", "fontSize": 10.5, "fontWeight": 700, "color": INK, "opacity": 0.8},
            "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                         "latitude": {"field": "lat", "type": "quantitative"},
                         "text": {"field": "s"}},
        },
    ],
})

# ================================================= 8. BIN MAP (linked)
write("08_bin_map.vg.json", {
    "title": {"text": "Where titles clustered (2° × 2° squares)"},
    "width": "container", "height": 330,
    "params": YEAR_PARAMS,
    "projection": {"type": "mercator"},
    "layer": [
        base_layer(),
        {
            "data": {"url": "data/titles.csv"},
            "transform": [
                {"filter": "datum.cell_id != null && " + ACTIVE},
                {"aggregate": [{"op": "count", "as": "n"}], "groupby": ["cell_id"]},
                {"lookup": "cell_id", "from": {"data": {"url": "data/cells.geojson", "format": {"type": "json", "property": "features"}},
                                               "key": "properties.cell_id"}, "as": "geo"},
            ],
            "mark": {"type": "geoshape", "stroke": BG, "strokeWidth": 0.6, "opacity": 0.92},
            "encoding": {
                "shape": {"field": "geo", "type": "geojson"},
                "color": {"field": "n", "type": "quantitative", "title": "Titles in square",
                          "scale": {"type": "threshold", "domain": [3, 6, 11, 26, 51],
                                    "range": ["#e3f1ee", "#b3dad3", "#7fbdb4", "#3f968c", "#21736d", "#0e3f3b"]},
                          "legend": {"orient": "bottom-left", "values": [1, 3, 6, 11, 26, 51],
                                     "labelExpr": "datum.value == 1 ? '1–2' : datum.value == 3 ? '3–5' : datum.value == 6 ? '6–10' : datum.value == 11 ? '11–25' : datum.value == 26 ? '26–50' : '51+'"}},
                "tooltip": [{"field": "n", "title": "Titles in this square"}],
            },
        },
        outline_layer(),
    ],
})

# ============================================================ 9. BUMP
write("09_bump.vg.json", {
    "title": {"text": "How the states ranked by number of newspapers in print",
              "subtitle": "Hover over a line to follow one state"},
    "width": "container", "height": 330,
    "data": {"url": "data/bump_active_titles.csv"},
    "encoding": {
        "x": {"field": "year", "type": "ordinal", "title": None, "axis": {"labelAngle": 0, "grid": False},
              "scale": {"padding": 0.5}},
        "y": {"field": "rank", "type": "quantitative", "title": "Rank (1 = most titles)",
              "scale": {"domain": [0.6, 6.4], "reverse": True},
              "axis": {"values": [1, 2, 3, 4, 5, 6], "format": "d", "grid": False}},
        "color": {"field": "state", "type": "nominal", "scale": STATE_SCALE_8, "legend": None},
    },
    "layer": [
        {"params": [{"name": "hl", "select": {"type": "point", "fields": ["state"], "on": "pointerover", "clear": "pointerout"}}],
         "mark": {"type": "line", "strokeWidth": 4, "interpolate": "monotone"},
         "encoding": {"opacity": {"condition": {"param": "hl", "value": 1}, "value": 0.22}}},
        {"mark": {"type": "circle", "size": 150, "opacity": 1, "stroke": BG, "strokeWidth": 1.5},
         "encoding": {"opacity": {"condition": {"param": "hl", "value": 1}, "value": 0.22},
                      "tooltip": [{"field": "state", "title": "State"}, {"field": "year", "title": "Year"},
                                  {"field": "rank", "title": "Rank"}, {"field": "titles", "title": "Titles in print"}]}},
        {"transform": [{"filter": "datum.year == 1950"}], 
         "mark": {"type": "text", "align": "left", "dx": 14, "fontSize": 12, "fontWeight": 600},
         "encoding": {"text": {"field": "state"}, "color": {"field": "state", "type": "nominal", "scale": STATE_SCALE_8, "legend": None}}},
        {"data": {"values": [{"year": "1900", "rank": 3, "t": "Climbs to third place"}]},
         "mark": {"type": "text", "align": "left", "dx": -8, "dy": -17, "fontSize": 11.5, "fontStyle": "italic", "color": INK},
         "encoding": {"x": {"field": "year", "type": "ordinal"}, "y": {"field": "rank", "type": "quantitative"},
                      "text": {"field": "t"}, "color": {"value": INK}}},
    ],
    
})

# ======================================================== 10. LOLLIPOP
# town labels read "Sydney, NSW" in the data; show the full state name instead of the abbreviation
TOWN_LABEL = ("split(datum.label, ', ')[0] + ', ' + ({'NSW': 'New South Wales', 'VIC': 'Victoria', 'QLD': 'Queensland', "
              "'SA': 'South Australia', 'WA': 'Western Australia', 'TAS': 'Tasmania', 'NT': 'Northern Territory', "
              "'ACT': 'Australian Capital Territory'})[split(datum.label, ', ')[1]]")
write("10_lollipop.vg.json", {
    "title": {"text": "The towns that printed the most newspapers"},
    "width": "container", "height": 360,
    "data": {"url": "data/top_towns.csv"},
    "encoding": {
        "y": {"field": "town", "type": "nominal", "sort": column("data/top_towns.csv", "town"), "title": None,
              "axis": {"ticks": False, "domain": False, "labelFontSize": 12.5, "labelLimit": 230, "labelExpr": TOWN_LABEL}},
        "x": {"field": "titles", "type": "quantitative", "title": "Number of titles", "axis": {"grid": True, "tickMinStep": 25}},
        "color": {"field": "state", "type": "nominal", "scale": STATE_SCALE_8, "legend": None},
    },
    "layer": [
        {"mark": {"type": "rule", "strokeWidth": 3},
         "encoding": {"x2": {"datum": 0}}},
        {"mark": {"type": "circle", "size": 190, "opacity": 1},
         "encoding": {"tooltip": [{"field": "town", "title": "Town"}, {"field": "titles", "title": "Titles"},
                                  {"field": "articles", "title": "Articles in Trove", "format": ","}]}},
        {"mark": {"type": "text", "align": "left", "dx": 12, "fontSize": 12, "color": INK},
         "encoding": {"text": {"field": "titles"}}},
    ],
})

# ================================================ 11. INDEXED LINE
write("11_indexed_line.vg.json", {
    "title": {"text": "Articles preserved per year, 1929 = 100", "subtitle": "Each line shows a state's yearly total compared with its own 1929 total"},
    "width": "container", "height": 340,
    "data": {"url": "data/articles_index_1929.csv"},
    "transform": [{"calculate": "datum.state == 'Australia' ? 1 : 0", "as": "is_au"}],
    "encoding": {
        "x": {"field": "year", "type": "quantitative", "title": None,
              "axis": {"format": "d", "values": [1929, 1934, 1939, 1944, 1949, 1954], "grid": False}, "scale": {"domain": [1929, 1954], "nice": False}},
        "y": {"field": "index", "type": "quantitative", "title": "Index (1929 = 100)",
              "scale": {"domain": [30, 115]}},
        "color": {"field": "state", "type": "nominal", "title": None,
                  "scale": {"domain": ["Australia"] + STATE_ORDER[:6], "range": [INK] + STATE_COLOURS[:6]},
                  "legend": {"orient": "top", "columns": 4}},
    },
    "layer": [
        {"data": {"values": [{"y": 100}]}, "mark": {"type": "rule", "strokeDash": [5, 4], "color": MUTED},
         "encoding": {"y": {"field": "y", "type": "quantitative"}}},
        {"mark": {"type": "line", "interpolate": "monotone"},
         "encoding": {"strokeWidth": {"condition": {"test": "datum.is_au == 1", "value": 4.5}, "value": 1.8},
                      "opacity": {"condition": {"test": "datum.is_au == 1", "value": 1}, "value": 0.7}}},
        {"mark": {"type": "point", "size": 18, "filled": True, "opacity": 0},
         "encoding": {"tooltip": [{"field": "state", "title": "State"}, {"field": "year", "title": "Year", "format": "d"},
                                  {"field": "index", "title": "Index (1929 = 100)"},
                                  {"field": "total", "title": "Articles", "format": ","}]}},
        {"data": {"values": [
            {"year": 1931, "index": 88.5, "t": "1931: Depression, 88.5"},
            {"year": 1943, "index": 54.4, "t": "1943: wartime low, 54.4"}]},
         "mark": {"type": "text", "align": "left", "dx": 8, "dy": 16, "fontStyle": "italic", "fontSize": 12, "color": INK},
         "encoding": {"x": {"field": "year", "type": "quantitative"}, "y": {"field": "index", "type": "quantitative"},
                      "text": {"field": "t"},"color": {"value": INK}}},
        {"data": {"values": [{"year": 1943, "index": 54.4}, {"year": 1931, "index": 88.5}]},
         "mark": {"type": "point", "size": 90, "filled": False, "color": INK, "strokeWidth": 1.5},
         "encoding": {"x": {"field": "year", "type": "quantitative"}, "y": {"field": "index", "type": "quantitative"},
                      "color": {"value": INK}}},
    ],
})

# ============================================================ 12. HEATMAP
write("12_heatmap.vg.json", {
    "title": {"text": "Newspaper titles added to Trove's list each year, by state",
              "subtitle": ["2013 was the peak: 322 titles added,", "183 of them from New South Wales"]},
    "width": "container", "height": 300,
    "data": {"url": "data/titles_added_to_trove.csv"},
    "encoding": {
        "x": {"field": "year", "type": "ordinal", "title": None, "axis": {"labelAngle": 0, "orient": "top", "domain": False, "ticks": False, "labelOverlap": True}},
        "y": {"field": "state", "type": "nominal", "title": None,
              "sort": {"field": "titles", "op": "sum", "order": "descending"},
              "axis": {"domain": False, "ticks": False, "labelLimit": 260}},
    },
    "layer": [
        {"mark": {"type": "rect", "stroke": BG, "strokeWidth": 2},
         "encoding": {
             "color": {"field": "titles", "type": "quantitative", "title": "Titles added",
                       "scale": {"range": TEAL_RAMP, "domainMin": 0}, "legend": {"orient": "bottom", "gradientLength": 180}},
             "tooltip": [{"field": "state", "title": "State"}, {"field": "year", "title": "Year", "format": "d"},
                         {"field": "titles", "title": "Titles added"}]}},
        {"mark": {"type": "text", "fontSize": 11},
         "encoding": {"text": {"field": "titles", "type": "quantitative"},
                      "color": {"condition": {"test": "datum.titles > 45", "value": "white"}, "value": INK}}},
    ],
})

# ============================================================== 13. WAFFLE
WAFFLE_ORDER = list(dict.fromkeys(column("data/waffle_cells.csv", "category")))
write("13_waffle.vg.json", {
    "title": {"text": ["What filled the pages:", "100 squares = all 251 million articles"]},
    "width": 300, "height": 300,
    "data": {"url": "data/waffle_cells.csv"},
    "mark": {"type": "rect", "stroke": BG, "strokeWidth": 2.5, "cornerRadius": 2},
    "encoding": {
        "x": {"field": "col", "type": "ordinal", "axis": None},
        "y": {"field": "row", "type": "ordinal", "axis": None, "sort": "ascending"},
        "color": {"field": "category", "type": "nominal", "title": None,
                  "scale": {"domain": WAFFLE_ORDER, "range": ["#a39574", "#d6ccb0", "#5b574e", TEAL]},
                  "legend": {"orient": "bottom", "direction": "vertical", "symbolSize": 160, "labelLimit": 340, "labelFontSize": 12}},
                    "tooltip": [{"field": "category", "title": "Type"}, {"field": "share_pct", "title": "Exact share (%)"}],
    },
})

# =============================================================== 14. CLIFF
CX = {"field": "year", "type": "quantitative", "title": None,
      "axis": {"format": "d", "tickCount": 10, "grid": False},
      "scale": {"domain": [1850, 2023], "nice": False, "zero": False}}
CY = {"field": "total", "type": "quantitative", "title": "Articles (log scale)",
      "scale": {"type": "log", "domain": [1000, 10000000]}, "axis": {"format": "~s", "tickCount": 4}}
write("14_cliff.vg.json", {
    "title": {"text": "Articles per year in Trove (log scale)", "subtitle": "Each step up the axis is ten times more articles"},
    "width": "container", "height": 330,
    "data": {"url": "data/articles_all_years.csv"},
    "layer": [
        {"data": {"values": [{"year": 1954.5, "year2": 2023}]},
         "mark": {"type": "rect", "color": "#cfc4a8", "opacity": 0.4},
         "encoding": {"x": CX, "x2": {"field": "year2"}}},
        {"mark": {"type": "line", "strokeWidth": 3, "color": "#5b574e", "interpolate": "monotone"},
         "encoding": {"x": CX, "y": CY,
                      "tooltip": [{"field": "year", "title": "Year", "format": "d"},
                                  {"field": "total", "title": "Articles", "format": ","}]}},
        {"data": {"values": [{"year": 1954, "total": 3661437}, {"year": 1955, "total": 436398}]},
         "mark": {"type": "point", "size": 80, "filled": True, "color": TEAL},
         "encoding": {"x": CX, "y": CY}},
        {"data": {"values": [{"year": 1954, "total": 3661437, "t": "1954: 3.7 million"}]},
         "mark": {"type": "text", "align": "right", "dx": -10, "dy": -24, "fontSize": 12, "fontStyle": "italic", "color": INK},
         "encoding": {"x": CX, "y": CY, "text": {"field": "t"}}},
        {"data": {"values": [{"year": 1955, "total": 436398, "t": "1955: 436,000 (down 88%)"}]},
         "mark": {"type": "text", "align": "left", "dx": 10, "fontSize": 12, "fontStyle": "italic", "color": INK},
         "encoding": {"x": CX, "y": CY, "text": {"field": "t"}}},
        {"data": {"values": [{"year": 1989, "total": 1500, "t": "After 1954: only a few papers"}]},
         "mark": {"type": "text", "align": "center", "fontSize": 12, "color": MUTED},
         "encoding": {"x": CX, "y": CY, "text": {"field": "t"}}},
    ],
})

# ====================================================== 15. CONNECTED DOT PLOT
DUMB_ORDER = ["Western Australia", "Queensland", "South Australia", "New South Wales", "Tasmania", "Victoria", "NT and ACT"]
write("15_dumbbell.vg.json", {
    "title": {"text": ["Titles in print by state:", "1900 against 1930"]},
    "width": "container", "height": 260,
    "data": {"url": "data/active_titles_by_year_state.csv",
             "format": {"type": "csv", "parse": {"year": "number", "titles": "number"}}},
    "transform": [{"filter": "(datum.year == 1900 || datum.year == 1930) && indexof(datum.group, 'Victorian papers') < 0"}],
    "encoding": {"y": {"field": "group", "type": "nominal", "title": None, "sort": DUMB_ORDER,
                       "axis": {"domain": False, "ticks": False, "labelLimit": 150}}},
    "layer": [
        {"mark": {"type": "rule", "color": "#8f866f", "strokeWidth": 3},
         "encoding": {"x": {"field": "titles", "type": "quantitative", "aggregate": "min", "title": "Titles in print"},
                      "x2": {"field": "titles", "aggregate": "max"}}},
        {"mark": {"type": "point", "filled": True, "size": 190, "opacity": 1},
         "encoding": {"x": {"field": "titles", "type": "quantitative"},
                      "color": {"field": "year", "type": "ordinal", "title": "Year",
                                "scale": {"domain": [1900, 1930], "range": ["#8f866f", TEAL]},
                                "legend": {"orient": "top", "format": "d"}},
                      "tooltip": [{"field": "group", "title": "State"}, {"field": "year", "title": "Year", "format": "d"},
                                  {"field": "titles", "title": "Titles in print"}]}},
    ],
})

# ============================================================ 16. NON-ENGLISH LANGUAGES
# the most common language gets the highlight colour, the rest stay muted
LANG_COLOUR = {"condition": {"test": "datum.language_full == 'German'", "value": TEAL}, "value": "#a39574"}
write("16_languages.vg.json", {
    "title": {"text": ["Papers printed partly or wholly in other languages", "(titles that began by 1954)"]},
    "width": "container", "height": 320,
    "data": {"url": "data/non_english_languages.csv"},
    "encoding": {
        "y": {"field": "language_full", "type": "nominal", "title": None,
              "sort": column("data/non_english_languages.csv", "language_full"),
              "axis": {"ticks": False, "domain": False, "labelFontSize": 12.5}},
        "x": {"field": "titles", "type": "quantitative", "title": "Number of titles",
              "axis": {"grid": True, "tickMinStep": 1}, "scale": {"domainMin": 0}},
    },
    "layer": [
        {"mark": {"type": "rule", "strokeWidth": 3},
         "encoding": {"x2": {"datum": 0}, "color": LANG_COLOUR}},
        {"mark": {"type": "circle", "size": 170, "opacity": 1},
         "encoding": {"color": LANG_COLOUR, "tooltip": [{"field": "language_full", "title": "Language"},
                                  {"field": "titles", "title": "Titles"},
                                  {"field": "first_year", "title": "First title appeared", "format": "d"}]}},
        {"transform": [{"calculate": "datum.titles + ' (from ' + datum.first_year + ')'", "as": "lab"}],
         "mark": {"type": "text", "align": "left", "dx": 12, "fontSize": 11.5, "color": "#6f665a"},
         "encoding": {"text": {"field": "lab"}}},
    ],
})