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

# ------------------------------------------------------------------ style
BG = "#fbf7ee"          # light beige (same as the page; chart backgrounds are transparent)
INK = "#2b2620"
MUTED = "#6f665a"
GRID = "#e8e0cd"
LAND = "#e4dcc8"        # base-map land colour
NO_DATA = "#d3d3d3"     # light grey: a state with no titles in print (no information, not zero)
# Fonts: Verdana (already installed on Windows and macOS) for text, Merriweather (Google Fonts) for titles.
# To try Lora instead, change "Merriweather" to "Lora" here and in index.html / styles.css.
BODY_FONT = "Verdana, Geneva, sans-serif"
HEAD_FONT = "Merriweather, Georgia, serif"

# one colour per state, used on every chart (colour-blind-safe, Okabe-Ito based)
TERRITORIES = "Northern Territory and Australian Capital Territory"   # the two territories share one group on some charts
STATE_ORDER = ["New South Wales", "Victoria", "Queensland", "South Australia",
               "Western Australia", "Tasmania", TERRITORIES]
# Victoria is a light brown (it used to be vermillion, which sat too close to Western Australia's orange)
STATE_COLOURS = ["#0072B2", "#A9794F", "#6b4fa0", "#CC79A7", "#E69F00", "#56B4E9", "#8a8478"]
# full list for charts that keep the two territories separate (maps)
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
LOLLI = "#4a5560"       # slate grey: every town on the lollipop chart (not used anywhere else)
LOLLI_HI = "#7cc400"    # bright lime: Sydney on the lollipop chart (not used anywhere else)

CONFIG = {
    "background": "transparent",
    "view": {"stroke": None},
    "font": BODY_FONT,
    "title": {"font": HEAD_FONT, "fontSize": 15, "color": INK, "anchor": "start", "fontWeight": 700,
              "subtitleFont": BODY_FONT, "subtitleFontWeight": 400, "subtitleColor": MUTED, "subtitleFontSize": 11.5, "subtitlePadding": 6, "offset": 10},
    "axis": {"labelFont": BODY_FONT, "titleFont": BODY_FONT, "labelColor": MUTED,
             "titleColor": MUTED, "labelFontSize": 11, "titleFontSize": 11.5, "titleFontWeight": 400,
             "gridColor": GRID, "domainColor": "#b9ae96", "tickColor": "#b9ae96"},
    "legend": {"labelFont": BODY_FONT, "titleFont": BODY_FONT, "labelColor": INK,
               "titleColor": MUTED, "labelFontSize": 11, "titleFontSize": 11.5, "titleFontWeight": 400,
               "symbolType": "square", "symbolOpacity": 1},
    "text": {"font": BODY_FONT},
}

STATE_SCALE = {"domain": STATE_ORDER, "range": STATE_COLOURS}
STATE_SCALE_8 = {"domain": STATE_ORDER_8, "range": STATE_COLOURS_8}

TOPO = {"url": "data/australia_states.topojson",
        "format": {"type": "topojson", "feature": "states"}}

# MAP PROJECTION (all four maps): Albers equal-area conic, set up as Geoscience Australia's "Australian Albers"
# (standard parallels 18 S and 36 S, central meridian 132 E). Equal-area means a state, or a 200 km square on
# the bin map, takes up the same space on the page wherever it is, so shading and dot density can be compared
# fairly. Mercator, the web-map default, stretches areas towards the poles (Tasmania would look larger than it is).
# make_cells.py uses the same numbers for the bin-map squares: change them in both places together.
# With a rotation, a "center" is given relative to the central meridian: [longitude - 132, latitude].
CENTRAL_MERIDIAN = 132
PROJ = {"type": "conicEqualArea", "parallels": [-18, -36], "rotate": [-CENTRAL_MERIDIAN, 0]}

# titles with no recorded place have an empty lat/lon: keep them off the town, dot and square maps
HAS_PLACE = "datum.lat != null && datum.lat !== ''"
HAS_SQUARE = "datum.cell_id != null && datum.cell_id !== ''"

# a title was running during the chosen years (the 1914-1918 Victorian slices are always included)
ACTIVE = "datum.start <= yr1 && datum.end >= yr0"
YEAR_PARAMS = [{"name": "yr0", "value": 1850}, {"name": "yr1", "value": 1900}]


def column(path, field):
    # utf-8 is explicit: without it Windows reads the file as cp1252, so the "…" in the Armidale label
    # becomes "â€¦", no longer matches the CSV that Vega-Lite loads, and the chart's sort order silently breaks
    with open(path, newline="", encoding="utf-8") as f:
        return [r[field] for r in csv.DictReader(f)]


def write(name, spec):
    spec = {**spec, "config": CONFIG}
    (OUT / name).write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print("wrote", name)


def base_layer(fill=LAND, prefix=""):
    """Base map under a data layer. Hovering shows the state name (with a prefix such as 'No data: ')."""
    return {
        "data": TOPO,
        "transform": [{"calculate": "'" + prefix + "' + datum.properties.STE_NAME21", "as": "note"}],
        "mark": {"type": "geoshape", "fill": fill, "stroke": "white", "strokeWidth": 1},
        "encoding": {"tooltip": {"field": "note", "title": "State"}},
    }


def outline_layer():
    return {"data": TOPO, "mark": {"type": "geoshape", "fill": None, "stroke": "#8f866f", "strokeWidth": 0.6}}


# ================================================= 1. STACKED AREA
# (this was a streamgraph with a centred baseline, whose vertical axis cannot be read; a stacked area that starts
# at zero keeps the same story and has a real y-axis)
def event(year, lines, align="left"):
    """a dashed line at `year` with a short italic label along the top edge"""
    return [
        {"data": {"values": [{"year": year}]},
         "mark": {"type": "rule", "strokeDash": [4, 3], "color": INK, "strokeWidth": 1},
         "encoding": {"x": {"field": "year", "type": "quantitative"}}},
        {"data": {"values": [{"year": year}]},
         "mark": {"type": "text", "align": align, "dx": 6 if align == "left" else -6, "y": 6, "baseline": "top",
                  "fontSize": 11, "fontStyle": "italic", "color": INK, "lineHeight": 13},
         "encoding": {"x": {"field": "year", "type": "quantitative"}, "text": {"value": lines}}},
    ]


def area_note(year, millions, lines, align="left"):
    """an explanatory note in the open space above the early, low part of the chart"""
    return {"data": {"values": [{"year": year, "y": millions * 1000000}]},
            "mark": {"type": "text", "align": align, "baseline": "bottom", "fontSize": 11, "fontStyle": "italic",
                     "color": INK, "lineHeight": 13},
            "encoding": {"x": {"field": "year", "type": "quantitative"}, "y": {"field": "y", "type": "quantitative"},
                         "text": {"value": lines}}}


write("01_stacked_area.vg.json", {
    "title": {"text": ["From a trickle in the 1830s to", "millions of articles a year by 1900"],
              "subtitle": ["Articles preserved in Trove each year, by state.", "Height of each band = number of articles."]},
    "width": "container", "height": 380,
    "data": {"url": "data/articles_by_year_state.csv"},
    "layer": [
        {
            "mark": {"type": "area", "interpolate": "monotone", "opacity": 0.92},
            "encoding": {
                "x": {"field": "year", "type": "quantitative", "title": "Year",
                      "axis": {"format": "d", "tickCount": 10, "grid": False},
                      "scale": {"domain": [1810, 1959], "nice": False}},
                # the bands stack up from zero, so the top edge is the national total and the y-axis can be read.
                # The fixed domain leaves empty space at the top so the event labels never touch the bands.
                "y": {"aggregate": "sum", "field": "total", "type": "quantitative", "stack": "zero",
                      "scale": {"domain": [0, 5500000]},
                      "axis": {"title": "Articles per year", "grid": True, "values": [0, 1000000, 2000000, 3000000, 4000000, 5000000],
                               "labelExpr": "datum.value == 0 ? '0' : (datum.value / 1000000) + ' million'"}},
                "color": {"field": "group", "type": "nominal", "title": "State",
                          "scale": STATE_SCALE, "legend": {"orient": "top", "columns": {"expr": "width < 520 ? 1 : 3"}, "title": None, "labelLimit": 360, "columnPadding": 16}},
                "tooltip": [{"field": "group", "title": "State"}, {"field": "year", "title": "Year", "format": "d"},
                            {"field": "total", "title": "Articles", "format": ","}],
            },
        },
        *event(1851, ["Gold rushes", "begin"]),
        *event(1901, ["Federation"], align="right"),
        *event(1914, ["First", "World War", "begins"]),
        *event(1939, ["Second", "World War", "begins"]),
        # Victoria: 19,022 articles in 1851 and 74,841 in 1859. Western Australia: 114,202 in 1895 and 359,283 in 1898.
        area_note(1848, 1.15, ["Gold rushes: Victoria's", "total grows almost", "fourfold, 1851 to 1859"], align="right"),
        area_note(1893, 2.45, ["1890s gold rush: Western", "Australia's yearly total", "triples in three years"], align="right"),
    ],
})

# ======================================================= 2. BUTTERFLY
# long-format data: launched titles are negative (drawn left), closed titles positive (drawn right).
# The grey segment is the Victorian papers that Trove holds only for 1914-1918.
lc_colour = {"domain": ["Titles launched", "Titles closed", SLICE], "range": [LAUNCH, CLOSE, SLICE_COLOUR]}


def butterfly_note(decade, x0, x1, lines):
    """a note in a box on the row of one decade; the box runs from bar-length x0 to x1 (negative = left side)"""
    box = {"data": {"values": [{"label": decade, "x0": x0, "x1": x1}]},
           "mark": {"type": "bar", "height": {"band": 0.8}, "fill": "#fffdf7", "stroke": "#8f866f",
                    "strokeWidth": 1, "cornerRadius": 3, "tooltip": None},
           "encoding": {"x": {"field": "x0", "type": "quantitative"}, "x2": {"field": "x1"}}}
    text = {"data": {"values": [{"label": decade, "x": x0}]},
            "mark": {"type": "text", "align": "left", "baseline": "middle", "dx": 7, "fontSize": 11,
                     "fontStyle": "italic", "color": INK, "lineHeight": 13, "dy": -6.5},
            "encoding": {"x": {"field": "x", "type": "quantitative"}, "text": {"value": lines}}}
    return [box, text]
DEC = [f"{d}s" for d in range(1830, 1950, 10)]
write("02_butterfly.vg.json", {
    "title": {"text": "Newspaper titles launched and closed, by decade",
              "subtitle": ["Each bar counts titles that started (left)", "or stopped (right) in that decade."]},
    "width": "container", "height": 560,
    "encoding": {"y": {"field": "label", "type": "ordinal", "title": "Decade", "sort": DEC,
                       "axis": {"labelFontSize": 12, "domain": False, "ticks": False}}},
    # (fixed x range so the notes on the right and left always have room)
    "layer": [
        {
            "data": {"url": "data/butterfly_long.csv"},
            "mark": {"type": "bar", "height": {"band": 0.72}},
            "encoding": {
                "x": {"field": "value", "type": "quantitative", "title": "\u2190 Titles launched        Titles closed \u2192",
                      "scale": {"domain": [-385, 385], "nice": False},
                      "axis": {"values": [-300, -200, -100, 0, 100, 200, 300], "labelExpr": "abs(datum.value)"}},
                "color": {"field": "series", "type": "nominal", "scale": lc_colour,
                          "legend": {"orient": "top", "title": None, "columns": 1, "labelLimit": 380}},
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
        *butterfly_note("1860s", 115, 375, ["Gold rushes, railways: most", "launches of any decade"]),
        *butterfly_note("1870s", 115, 375, ["Grey bars below: slices,", "not new launches or closures"]),
        *butterfly_note("1940s", -372, -112, ["Depression and war years:", "new launches more than halve"]),
    ],
})

# ============================================================ 3. GANTT
GY = {"field": "label", "type": "nominal", "title": "Newspaper",
      "sort": column("data/longest_running_titles.csv", "label"),
      "axis": {"labelLimit": 205, "ticks": False, "domain": False, "labelFontSize": 11}}
# only the states that actually appear in this chart get a legend entry (same colours as everywhere else)
GANTT_STATES = [s for s in STATE_ORDER_8 if s in set(column("data/longest_running_titles.csv", "state"))]
GANTT_COLOURS = [STATE_COLOURS_8[STATE_ORDER_8.index(s)] for s in GANTT_STATES]
write("03_gantt.vg.json", {
    "title": {"text": "The 15 longest-running newspapers in Trove",
              "subtitle": ["Bars show each title's run in Trove;", "the number is its length in years"]},
    "width": "container", "height": 400,
    "data": {"url": "data/longest_running_titles.csv"},
    "layer": [
        {"mark": {"type": "bar", "height": {"band": 0.6}, "cornerRadius": 2},
         "encoding": {
             "y": GY,
             "x": {"field": "start", "type": "quantitative", "title": "Year",
                   "scale": {"domain": [1835, 2035], "nice": False},
                   "axis": {"format": "d", "values": list(range(1840, 2021, 20))}},
             "x2": {"field": "end"},
             "color": {"field": "state", "type": "nominal", "scale": {"domain": GANTT_STATES, "range": GANTT_COLOURS},
                       "legend": {"orient": "top", "title": None, "columns": {"expr": "width < 200 ? 1 : width < 340 ? 2 : 4"}, "labelLimit": 200}},
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
        # note below the 1954 line, in the empty space under the bars' year-count labels. 10 of the 15 runs end in 1954.
        {"data": {"values": [{"x": 1966}]},
         "mark": {"type": "text", "align": "left", "dx": 0, "baseline": "top", "fontStyle": "italic", "fontSize": 11, "y": {"expr": "height - 76"},
                  "color": INK, "lineHeight": 13},
         "encoding": {"x": {"field": "x", "type": "quantitative"},
                      "text": {"value": ["1954: Trove's coverage", "ends. Ten of these 15", "stop here, so real runs", "may be longer"]}}},
    ],
})

# ========================================== 4. OVERVIEW (linked brush)
write("04_overview.vg.json", {
    "title": {"text": ["Drag across the chart to choose",
                       "the years shown on the maps below"],
              "fontSize": 12.5, "font": BODY_FONT, "fontStyle": "italic", "fontWeight": 400},
    "width": "container", "height": 130,
    "data": {"url": "data/active_titles_by_year_state.csv"},
    "params": [{"name": "brush", "value": {"year": [1850, 1900]},
                "select": {"type": "interval", "encodings": ["x"]}}],
    "mark": {"type": "area", "interpolate": "monotone"},
    "encoding": {
        "x": {"field": "year", "type": "quantitative", "title": "Year",
              "axis": {"format": "d", "tickCount": 15, "grid": False}, "scale": {"domain": [1803, 1954], "nice": False}},
        "y": {"aggregate": "sum", "field": "titles", "type": "quantitative", "title": "Titles in print",
              "axis": {"tickCount": 3}},
        "color": {"field": "group", "type": "nominal", "title": None,
                  "scale": {"domain": STATE_ORDER + [SLICE], "range": STATE_COLOURS + [SLICE_COLOUR]},
                  "legend": {"orient": "top", "columns": {"expr": "width < 480 ? 1 : width < 760 ? 3 : 4"}, "labelLimit": 360}},
        "order": {"field": "group", "sort": "descending"},
        "tooltip": [{"field": "group", "title": "State"}, {"field": "year", "format": "d", "title": "Year"},
                    {"field": "titles", "title": "Titles in print"}],
    },
})

# ============================== 5. DOT MAP, SMALL MULTIPLES BY ERA
# three side-by-side panels (one per era), each a base map + one dot per title
ERAS = [("1. Before 1860", "Before 1860"), ("2. 1860-1899", "1860\u20131899"), ("3. 1900 onwards", "1900 onwards")]
ERA_SCALE = 480   # pixels per radian of the Albers projection: fits the whole country in a 320 x 300 panel


def era_panel(era, label, show_legend):
    # the heading, sub-heading and one short text per era are written in index.html (.era-block),
    # so the panels themselves carry no Vega-Lite titles
    return {
        "width": 320, "height": 300,
        "projection": {**PROJ, "center": [133.5 - CENTRAL_MERIDIAN, -27.5], "scale": ERA_SCALE, "translate": [160, 150]},
        "layer": [
            {"data": TOPO, "mark": {"type": "geoshape", "fill": LAND, "stroke": "white", "strokeWidth": 0.8}},
            {
                "data": {"url": "data/titles.csv"},
                "transform": [{"filter": f"{HAS_PLACE} && datum.era == '{era}'"}],
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
    "hconcat": [era_panel(e, l, i == 1) for i, (e, l) in enumerate(ERAS)],
    "resolve": {"scale": {"color": "shared"}},
})

# ===================== 6. PROPORTIONAL SYMBOL MAP (zoom + linked years)
# [centre longitude, centre latitude, scale]; the scale is in pixels per radian of the Albers projection.
# (The old Mercator presets were the same views, with scales about 1/cos(latitude) smaller.)
FOCUS = [
    ([134, -28.5, 865], "All of Australia"),
    ([148, -38.3, 2800], "South-east: Victoria, New South Wales, Tasmania"),   # re-centred south so Tasmania is in view
    ([145.3, -37.3, 7790], "Melbourne and Victoria"),
    ([151.0, -33.2, 8370], "Sydney and the Hunter"),
    ([138.6, -34.4, 6300], "Adelaide and the Murray"),
    ([119.5, -31.0, 3970], "Perth and the goldfields"),
    ([151.5, -24.5, 1650], "Queensland coast"),
]
write("06_symbol_map.vg.json", {
    "title": {"text": "Titles in print, town by town"},
    "width": 620, "height": 520,
    "params": YEAR_PARAMS + [{
        "name": "focus", "value": FOCUS[0][0],
        "bind": {"input": "select", "options": [f[0] for f in FOCUS], "labels": [f[1] for f in FOCUS],
                 "name": "Zoom to: "},
    }],
    "projection": {**PROJ, "center": {"expr": f"[focus[0] - {CENTRAL_MERIDIAN}, focus[1]]"}, "scale": {"expr": "focus[2]"}},
    "layer": [
        base_layer(),
        {
            "data": {"url": "data/titles.csv"},
            "transform": [
                {"filter": HAS_PLACE + " && " + ACTIVE},
                {"aggregate": [{"op": "count", "as": "n"}, {"op": "sum", "field": "articles", "as": "arts"}],
                 "groupby": ["place", "state", "lat", "lon"]},
            ],
            "mark": {"type": "circle", "opacity": 0.72, "stroke": "white", "strokeWidth": 0.6},
            "encoding": {
                "longitude": {"field": "lon", "type": "quantitative"},
                "latitude": {"field": "lat", "type": "quantitative"},
                # the size legend is drawn in HTML next to the zoom menu (see index.html), so it never
                # covers the map. Its circles use the same sqrt scale: area = 1900 * sqrt(n / 120).
                "size": {"field": "n", "type": "quantitative", "title": "Titles in print",
                         "scale": {"type": "sqrt", "domain": [0, 120], "range": [0, 1900]},
                         "legend": None},
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
                {"filter": HAS_PLACE + " && " + ACTIVE},
                {"aggregate": [{"op": "count", "as": "n"}], "groupby": ["place", "lat", "lon"]},
                {"filter": "datum.n >= 14"},
            ],
            # Perth sits right next to Fremantle, so its label is lifted higher to stop them overlapping
            "mark": {"type": "text", "dy": {"expr": "datum.place == 'Perth' ? -50 : -26"}, "fontSize": 11,
                     "fontStyle": "italic", "fill": INK},
            "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                         "latitude": {"field": "lat", "type": "quantitative"},
                         "text": {"field": "place"}},
        },
    ],
})

# ============================================ 7. CHOROPLETH (linked)
# Always normalised: titles per 100,000 km2. Raw counts are not used, because a big state would look
# "darker" only because it is big.
LOOK = [
    {"filter": "datum.state != 'International' && datum.state != 'National' && " + ACTIVE},
    {"aggregate": [{"op": "count", "as": "n"}], "groupby": ["state"]},
    {"lookup": "state", "from": {"data": {"url": "data/state_area.csv"}, "key": "state", "fields": ["area_km2"]}},
    {"calculate": "datum.n / datum.area_km2 * 100000", "as": "per100k"},
]
choro_base = base_layer(None, prefix="No data: ")
choro_base["mark"] = {"type": "geoshape", "stroke": "white", "strokeWidth": 1}
# a one-item legend (light grey square labelled "No data") so the grey states are explained on the map itself
choro_base["encoding"]["fill"] = {"datum": "No data", "type": "nominal", "title": None,
                                  "scale": {"domain": ["No data"], "range": [NO_DATA]},
                                  "legend": {"orient": "bottom-left", "symbolType": "square", "symbolSize": 110,
                                             "symbolStrokeColor": "#b9ae96", "symbolStrokeWidth": 0.6, "offset": 6}}
write("07_choropleth.vg.json", {
    "title": {"text": "Titles in print, by state"},
    "width": "container", "height": 330,
    "params": YEAR_PARAMS,
    "projection": PROJ,
    "layer": [
        choro_base,
        {
            "data": {"url": "data/titles.csv"},
            "transform": LOOK + [{"lookup": "state", "from": {"data": TOPO, "key": "properties.STE_NAME21"}, "as": "geo"}],
            "mark": {"type": "geoshape", "stroke": "white", "strokeWidth": 1},
            "encoding": {
                "shape": {"field": "geo", "type": "geojson"},
                "color": {"field": "per100k", "type": "quantitative", "title": "Titles per 100,000 km\u00b2",
                          "scale": {"type": "sqrt", "range": ["#e3f1ee", "#8cc4bb", "#4aa093"], "domainMin": 0},
                          "legend": {"orient": "bottom-left", "format": "~s", "gradientLength": 120}},
                "tooltip": [{"field": "state", "title": "State"},
                            {"field": "n", "title": "Titles in print"},
                            {"field": "per100k", "title": "Per 100,000 km\u00b2", "format": ".1f"}],
            },
        },
        {
            "data": {"values": [
                {"s": ["New South", "Wales"], "lon": 146.5, "lat": -32.3}, {"s": "Victoria", "lon": 144.8, "lat": -36.9},
                {"s": "Queensland", "lon": 144.5, "lat": -22.5}, {"s": ["South", "Australia"], "lon": 135.0, "lat": -30.0},
                {"s": ["Western", "Australia"], "lon": 122.0, "lat": -25.5}, {"s": "Tasmania", "lon": 146.6, "lat": -42.1},
                {"s": ["Northern", "Territory"], "lon": 133.5, "lat": -19.5}]},
            "mark": {"type": "text", "fontSize": 11, "fontWeight": 700, "color": INK, "opacity": 0.8},
            "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                         "latitude": {"field": "lat", "type": "quantitative"},
                         "text": {"field": "s"}},
        },
        {   # a note that follows the chosen years: which state has the most titles for its size
            "data": {"url": "data/titles.csv"},
            "transform": LOOK + [
                {"window": [{"op": "rank", "as": "rk"}], "sort": [{"field": "per100k", "order": "descending"}]},
                {"filter": "datum.rk == 1"},
                {"calculate": "'Most titles for its size: ' + datum.state", "as": "top"},
            ],
            "mark": {"type": "text", "x": 0, "y": 0, "align": "left", "baseline": "top", "fontSize": 11,
                     "fontStyle": "italic", "color": INK},
            "encoding": {"text": {"field": "top"}},
        },
    ],
})

# ================================================= 8. BIN MAP (linked)
write("08_bin_map.vg.json", {
    "title": {"text": "Where titles clustered"},
    "width": "container", "height": 330,
    "params": YEAR_PARAMS,
    "projection": PROJ,
    "layer": [
        base_layer(),
        {
            "data": {"url": "data/titles.csv"},
            "transform": [
                {"filter": HAS_SQUARE + " && " + ACTIVE},
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
                          "legend": {"orient": "left", "offset": 4, "values": [1, 3, 6, 11, 26, 51],
                                     "labelExpr": "datum.value == 1 ? '1–2' : datum.value == 3 ? '3–5' : datum.value == 6 ? '6–10' : datum.value == 11 ? '11–25' : datum.value == 26 ? '26–50' : '51+'"}},
                "tooltip": [{"field": "n", "title": "Titles in this square"}],
            },
        },
        outline_layer(),
        {   # reading note along the top edge, in the empty sea
            "data": {"values": [{"k": 1}]},
            "mark": {"type": "text", "x": "width", "y": 0, "align": "right", "baseline": "top", "fontSize": 11,
                     "fontStyle": "italic", "color": INK},
            "encoding": {"text": {"value": "Darkest squares: mostly around the big cities"}},
        },
    ],
})

# ============================================================ 9. BUMP
def bump_note(year, lines):
    """italic note in the empty band above rank 1, centred over one year's column"""
    return {"data": {"values": [{"k": 1}]},
            "mark": {"type": "text", "align": "center", "baseline": "bottom", "fontSize": 11, "fontStyle": "italic",
                     "color": INK, "lineHeight": 13},
            "encoding": {"x": {"value": {"expr": f"scale('x', '{year}') + bandwidth('x') / 2"}},
                         "y": {"value": {"expr": "scale('y', 0.15)"}},
                         "text": {"value": lines}, "color": {"value": INK}}}


write("09_bump.vg.json", {
    "title": {"text": ["Western Australia rose from 6th", "to 2nd place between 1870 and 1930"],
              "subtitle": ["States ranked by newspapers in print.", "1st = highest rank (the most)."]},
    "width": "container", "height": 330,
    "data": {"url": "data/bump_active_titles.csv"},
    "encoding": {
        "x": {"field": "year", "type": "ordinal", "title": "Year", "axis": {"labelAngle": 0, "grid": False, "labelFontSize": 11},
              "scale": {"padding": 0.4}},
        "y": {"field": "rank", "type": "quantitative", "title": "Rank",
              "scale": {"domain": [-1.0, 6.4], "reverse": True},
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
        # notes in the empty band above rank 1
        bump_note(1870, ["1890s gold rushes:", "Western Australia", "climbs from 5th to 3rd"]),
        bump_note(1930, ["1930: Western", "Australia moves", "ahead of Victoria"]),
        {"transform": [{"filter": "datum.year == 1950"}],
         "mark": {"type": "text", "align": "left", "dx": 14, "fontSize": 11, "fontWeight": 600},
         "encoding": {"text": {"field": "state"}, "color": {"field": "state", "type": "nominal", "scale": STATE_SCALE_8, "legend": None}}},
    ],
})

# ======================================================== 10. LOLLIPOP
# town labels read "Sydney, NSW" in the data; show the full state name instead of the abbreviation
TOWN_LABEL = ("split(datum.label, ', ')[0] + ', ' + ({'NSW': 'New South Wales', 'VIC': 'Victoria', 'QLD': 'Queensland', "
              "'SA': 'South Australia', 'WA': 'Western Australia', 'TAS': 'Tasmania', 'NT': 'Northern Territory', "
              "'ACT': 'Australian Capital Territory'})[split(datum.label, ', ')[1]]")
# every town is slate grey; Sydney, the town with the most titles, gets the bright highlight colour
TOWN_FULL = TOWN_LABEL.replace("datum.label", "datum.town")      # same text for the hover box
LOLLI_COLOUR = {"condition": {"test": "datum.town == 'Sydney, NSW'", "value": LOLLI_HI}, "value": LOLLI}
LY = {"field": "town", "type": "nominal", "sort": column("data/top_towns.csv", "town"), "title": "Town",
      "axis": {"ticks": False, "domain": False, "labelFontSize": 11, "labelLimit": 320, "labelExpr": TOWN_LABEL}}
LX = {"field": "titles", "type": "quantitative", "title": "Number of titles", "axis": {"grid": True, "tickMinStep": 25}}
write("10_lollipop.vg.json", {
    "title": {"text": ["Sydney had the most newspaper titles;", "Perth came a clear second"],
              "subtitle": "The 15 towns with the most titles in Trove"},
    "width": "container", "height": 360,
    "data": {"url": "data/top_towns.csv"},
    "transform": [{"calculate": TOWN_FULL, "as": "town_full"}],
    "layer": [
        {"mark": {"type": "rule", "strokeWidth": 3},
         "encoding": {"y": LY, "x": LX, "x2": {"datum": 0}, "color": LOLLI_COLOUR}},
        {"mark": {"type": "circle", "size": 190, "opacity": 1},
         "encoding": {"y": LY, "x": LX, "color": LOLLI_COLOUR,
                      "tooltip": [{"field": "town_full", "title": "Town"}, {"field": "titles", "title": "Titles"},
                                  {"field": "articles", "title": "Articles in Trove", "format": ","}]}},
        {"mark": {"type": "text", "align": "left", "dx": 12, "fontSize": 11, "color": INK},
         "encoding": {"y": LY, "x": LX, "text": {"field": "titles"}, "color": {"value": INK}}},
        # annotation in the empty bottom-right corner. Six of the 15 towns are in Western Australia
        # (Perth, Fremantle, Geraldton, Coolgardie, Kalgoorlie, Bunbury), so the note says that.
        {"data": {"values": [{"note": 1}]},
         "mark": {"type": "text", "align": "right", "baseline": "top", "x": "width", "y": {"expr": "height - 80"},
                  "dx": -4, "fontSize": 11, "fontStyle": "italic", "lineHeight": 15, "color": INK},
         "encoding": {"text": {"value": ["Western Australia has 6 of", "the top 15 towns, helped by", "its 1890s gold rushes; no", "other state has more than 3."]}}},
    ],
})

# ================================================ 11. INDEXED LINE
def callout(year, index, box_year, box_index, box_w, text, below=True, box_h=None):
    """A boxed note in open space, joined to its data point by a thin line.
    (year, index) is the data point; (box_year, box_index) is the CENTRE of the box in data units.
    The box is box_w pixels wide and just tall enough for its lines, kept inside the plot, below (or above) its point."""
    LH = 13                                              # line height in pixels
    n = len(text)
    if box_h is None:
        box_h = n * LH + 16                              # text height plus 8 px of padding top and bottom
    lift = -(n - 1) * LH / 2                             # Vega puts the first line at the middle, so lift the block to centre it
    one = {"data": {"values": [{"k": 1}]}}
    px, py = f"scale('x', {year})", f"scale('y', {index})"
    cx = f"max({box_w / 2 + 2}, min(width - {box_w / 2 + 2}, scale('x', {box_year})))"
    cy = f"scale('y', {box_index})"
    near = box_h / 2 if below else -box_h / 2          # box edge facing the point
    ring = 6 if below else -6                           # start the line just outside the ring marker
    # the chart's own encodings (year, index, state colour) are inherited by every layer,
    # so each channel is overridden here with a fixed value
    return [
        {**one, "mark": {"type": "rule", "strokeWidth": 0.9},
         "encoding": {"x": {"value": {"expr": px}}, "y": {"value": {"expr": f"{py} + {ring}"}},
                      "x2": {"value": {"expr": cx}}, "y2": {"value": {"expr": f"{cy} - {near}"}},
                      "color": {"value": MUTED}}},
        {**one, "mark": {"type": "rect", "strokeWidth": 1, "cornerRadius": 3},
         "encoding": {"x": {"value": {"expr": f"{cx} - {box_w / 2}"}}, "x2": {"value": {"expr": f"{cx} + {box_w / 2}"}},
                      "y": {"value": {"expr": f"{cy} - {box_h / 2}"}}, "y2": {"value": {"expr": f"{cy} + {box_h / 2}"}},
                      "color": None, "fill": {"value": BG}, "stroke": {"value": "#8f866f"}}},
        {**one, "mark": {"type": "text", "align": "center", "baseline": "middle", "fontSize": 11,
                         "lineHeight": LH, "dy": lift},
         "encoding": {"x": {"value": {"expr": cx}}, "y": {"value": {"expr": cy}},
                      "text": {"value": text}, "color": {"value": INK}}},
    ]


write("11_indexed_line.vg.json", {
    "title": {"text": ["By 1943, preserved articles fell", "to just over half their 1929 level"],
              "subtitle": ["Each line shows a state's yearly total", "compared with its own 1929 total (1929 = 100)"]},
    "width": "container", "height": 340,
    "data": {"url": "data/articles_index_1929.csv"},
    "transform": [{"calculate": "datum.state == 'Australia' ? 1 : 0", "as": "is_au"}],
    "encoding": {
        "x": {"field": "year", "type": "quantitative", "title": "Year",
              "axis": {"format": "d", "values": [1929, 1934, 1939, 1944, 1949, 1954], "grid": False}, "scale": {"domain": [1929, 1966], "nice": False}},
        "y": {"field": "index", "type": "quantitative", "title": "Index (1929 = 100)",
              "scale": {"domain": [14, 115]}},
        "color": {"field": "state", "type": "nominal", "title": None,
                  "scale": {"domain": ["Australia"] + STATE_ORDER[:6], "range": [INK] + STATE_COLOURS[:6]},
                  "legend": {"orient": "top", "columns": {"expr": "width < 380 ? 2 : 4"}}},
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
        *callout(1931, 88.5, 1932.8, 50, 190, ["1931: the Depression dip.", "South Australia falls most"]),
        *callout(1943, 54.4, 1943.6, 27, 214, ["1943: wartime low. Every state is", "down; South Australia and Queensland", "fall furthest"]),
        # end-of-line labels, so the lines can be read without the legend (nudged apart where lines end close together)
        {"transform": [{"filter": "datum.year == 1954"}],
         "mark": {"type": "text", "align": "left", "dx": 8, "fontSize": 11, "fontWeight": 600,
                  "dy": {"expr": "datum.state == 'Australia' ? -3 : datum.state == 'Victoria' ? 1 : datum.state == 'Western Australia' ? 1 : 0"}},
         "encoding": {"text": {"field": "state"}}},
        {"data": {"values": [{"year": 1943, "index": 54.4}, {"year": 1931, "index": 88.5}]},
         "mark": {"type": "point", "size": 90, "filled": False, "color": INK, "strokeWidth": 1.5},
         "encoding": {"x": {"field": "year", "type": "quantitative"}, "y": {"field": "index", "type": "quantitative"},
                      "color": {"value": INK}}},
    ],
})

# ============================================================ 12. HEATMAP
write("12_heatmap.vg.json", {
    "title": {"text": ["Newspaper titles added to Trove's",
                       "list each year, by state"],
              "subtitle": ["States peaked in different years: New South Wales", "and Victoria in 2013, Western Australia in 2020"]},
    "width": "container", "height": 300,
    "data": {"url": "data/titles_added_to_trove.csv"},
    "encoding": {
        "x": {"field": "year", "type": "ordinal", "title": "Year", "axis": {"labelAngle": 0, "orient": "top", "domain": False, "ticks": False, "labelOverlap": True}},
        "y": {"field": "state", "type": "nominal", "title": "State",
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

# =============================================================== 13. CLIFF
CX = {"field": "year", "type": "quantitative", "title": "Year",
      "axis": {"format": "d", "tickCount": 10, "grid": False},
      "scale": {"domain": [1850, 2023], "nice": False, "zero": False}}
CY = {"field": "total", "type": "quantitative", "title": "Articles (log scale)",
      "scale": {"type": "log", "domain": [1000, 10000000]}, "axis": {"format": "~s", "tickCount": 4}}
write("13_cliff.vg.json", {
    "title": {"text": "Trove's articles fall 88% after 1954",
              "subtitle": ["Articles per year, on a log scale:", "each step up the axis is ten times more"]},
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
        {"data": {"values": [{"year": 1954, "total": 3661437}]},
         "mark": {"type": "text", "align": "right", "dx": -10, "dy": -34, "fontSize": 11, "fontStyle": "italic", "color": INK,
                  "lineHeight": 13},
         "encoding": {"x": CX, "y": CY, "text": {"value": ["1954: the last year with", "wide coverage"]}}},
        {"data": {"values": [{"year": 1955, "total": 436398}]},
         "mark": {"type": "text", "align": "left", "dx": 10, "fontSize": 11, "fontStyle": "italic", "color": INK,
                  "lineHeight": 13},
         "encoding": {"x": CX, "y": CY, "text": {"value": ["1955: copyright limits what", "Trove could digitise,", "so articles fall by 88%"]}}},
        {"data": {"values": [{"year": 1989, "total": 1500}]},
         "mark": {"type": "text", "align": "center", "fontSize": 11, "color": MUTED},
         "encoding": {"x": CX, "y": CY, "text": {"value": "After 1954: only papers with permission"}}},
    ],
})

# ====================================================== 14. CONNECTED DOT PLOT
DUMB_ORDER = ["Western Australia", "Queensland", "South Australia", "New South Wales", "Tasmania", "Victoria", TERRITORIES]


def dumb_note(group, x, lines):
    return {"data": {"values": [{"group": group, "x": x}]},
            "mark": {"type": "text", "align": "left", "baseline": "middle", "dx": 10, "fontSize": 11,
                     "fontStyle": "italic", "color": INK, "lineHeight": 13},
            "encoding": {"x": {"field": "x", "type": "quantitative"}, "text": {"value": lines}}}
write("14_dumbbell.vg.json", {
    "title": {"text": ["Western Australia's titles more than", "doubled while Victoria's fell"],
              "subtitle": "Titles in print by state, 1900 against 1930"},
    "width": "container", "height": 320,
    "data": {"url": "data/active_titles_by_year_state.csv",
             "format": {"type": "csv", "parse": {"year": "number", "titles": "number"}}},
    "transform": [{"filter": "(datum.year == 1900 || datum.year == 1930) && indexof(datum.group, 'Victorian papers') < 0"}],
    "encoding": {"y": {"field": "group", "type": "nominal", "title": "State", "sort": DUMB_ORDER,
                       "axis": {"domain": False, "ticks": False, "labelLimit": 150,
                                "labelExpr": "datum.label == '" + TERRITORIES + "' ? ['Northern Territory and', 'Australian Capital Territory'] : datum.label"}}},
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
        # notes beside the two biggest changes. Victoria is the only state that lost many titles (110 to 65).
        dumb_note("Western Australia", 91, ["The gold rushes likely", "pulled the press west"]),
        dumb_note("Victoria", 110, ["The only state to", "lose many titles"]),
    ],
})

# ============================================================ 15. NON-ENGLISH LANGUAGES
# the most common language gets the highlight colour, the rest stay muted
LANG_COLOUR = {"condition": {"test": "datum.language_full == 'German'", "value": TEAL}, "value": "#a39574"}
write("15_languages.vg.json", {
    "title": {"text": ["German, Italian and Chinese lead", "the press in other languages"],
              "subtitle": "Titles printed partly or wholly in another language, begun by 1954"},
    "width": "container", "height": 320,
    "data": {"url": "data/non_english_languages.csv"},
    "encoding": {
        "y": {"field": "language_full", "type": "nominal", "title": "Language",
              "sort": column("data/non_english_languages.csv", "language_full"),
              "axis": {"ticks": False, "domain": False, "labelFontSize": 11.5}},
        "x": {"field": "titles", "type": "quantitative", "title": "Number of titles",
              "axis": {"grid": True, "values": list(range(0, 10)), "format": "d"}, "scale": {"domainMin": 0}},
    },
    "layer": [
        {"mark": {"type": "rule", "strokeWidth": 3},
         "encoding": {"x2": {"datum": 0}, "color": LANG_COLOUR}},
        {"mark": {"type": "circle", "size": 170, "opacity": 1},
         "encoding": {"color": LANG_COLOUR, "tooltip": [{"field": "language_full", "title": "Language"},
                                  {"field": "titles", "title": "Titles"},
                                  {"field": "first_year", "title": "First title appeared", "format": "d"}]}},
        # the oldest presses: German from 1848, Chinese from 1856 (the gold rushes)
        {"data": {"values": [{"language_full": "French", "x": 4.2}]},
         "mark": {"type": "text", "align": "left", "baseline": "middle", "fontSize": 11, "fontStyle": "italic", "color": INK,
                  "lineHeight": 13},
         "encoding": {"x": {"field": "x", "type": "quantitative"},
                      "text": {"value": ["German began in 1848, Chinese in 1856,", "during the gold rushes"]}}},
        # the label is just the number of titles; the year each language first appeared is in the tooltip
        {"mark": {"type": "text", "align": "left", "dx": 12, "fontSize": 11, "color": "#6f665a"},
         "encoding": {"text": {"field": "titles", "type": "quantitative"}}},
    ],
})