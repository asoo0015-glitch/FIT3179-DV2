"""
prepare_data.py - turns the raw Trove + ABS downloads in raw/ into the small
files in data/ that the Vega-Lite charts read.

Run from the project folder:   python prepare_data.py
Needs: pip install pandas openpyxl
"""
import json
import re
from pathlib import Path

import pandas as pd

from make_cells import build_cells, cell_id_for

RAW = Path("raw")
OUT = Path("data")
OUT.mkdir(exist_ok=True)

LAST_YEAR = 1954  # Trove's copyright cut-off: most digitised papers stop here

STATE_FULL = {
    "ACT": "Australian Capital Territory",
    "NSW": "New South Wales", "VIC": "Victoria", "QLD": "Queensland",
    "SA": "South Australia", "WA": "Western Australia", "TAS": "Tasmania",
    "NT": "Northern Territory",
}
MAIN_STATES = ["New South Wales", "Victoria", "Queensland", "South Australia",
               "Western Australia", "Tasmania"]
REAL_STATES = MAIN_STATES + ["Northern Territory", "Australian Capital Territory"]


def save(df, name):
    df.to_csv(OUT / name, index=False)
    print(f"{name:45s} {len(df):6d} rows  {(OUT / name).stat().st_size / 1024:7.1f} KB")


# ---------------------------------------------------------------- titles
news = pd.read_csv(RAW / "total_articles_by_newspaper.csv")
news["start"] = pd.to_datetime(news.start_date, errors="coerce").dt.year
news["end"] = pd.to_datetime(news.end_date, errors="coerce").dt.year
news = news.dropna(subset=["start", "end"]).copy()
news[["start", "end"]] = news[["start", "end"]].astype(int)
news["state"] = news.state.replace({"ACT": "Australian Capital Territory"})
# Many Victorian local papers appear in Trove ONLY for 1914-1918 (a WWI digitisation project).
# We keep them but flag them so the charts can show them separately.
news["wwi_slice"] = ((news.state == "Victoria") & (news.start == 1914) & (news.end == 1918)).astype(int)
news["short"] = news.title.str.replace(r"\s*\(.*$", "", regex=True).str.strip()

loc = pd.read_excel(RAW / "trove-newspaper-titles-locations.csv.xlsx")
# a few titles list several places (e.g. a district); keep the first listed
loc = loc.dropna(subset=["latitude", "longitude"]).drop_duplicates("title_id")
titles = news.merge(loc[["title_id", "place", "latitude", "longitude"]],
                    on="title_id", how="left")


# bin map: 200 km x 200 km squares in the Albers equal-area projection (defined in make_cells.py)
titles["cell_id"] = titles.apply(
    lambda r: cell_id_for(r.longitude, r.latitude) if pd.notna(r.latitude) else "", axis=1)
titles["era"] = pd.cut(titles.start, [0, 1859, 1899, 3000],
                       labels=["1. Before 1860", "2. 1860-1899", "3. 1900 onwards"]).astype(str)
titles = titles.rename(columns={"total": "articles", "latitude": "lat", "longitude": "lon"})
CAPITALS = ("Sydney", "Melbourne", "Brisbane", "Adelaide", "Perth", "Hobart", "Darwin", "Canberra")
titles["place_type"] = titles.place.apply(
    lambda p: "Capital city" if isinstance(p, str) and p.startswith(CAPITALS) else "Regional town")
titles["lat"] = titles.lat.round(4)
titles["lon"] = titles.lon.round(4)
save(titles[["title_id", "short", "state", "place", "lat", "lon", "start", "end",
             "articles", "cell_id", "era", "place_type", "wwi_slice"]], "titles.csv")

# the squares themselves (polygons) for the bin map; equal area, so a darker square really means more titles
cells = build_cells(titles.cell_id.unique())
(OUT / "cells.geojson").write_text(json.dumps(cells), encoding="utf-8")
print("cells.geojson", len(cells["features"]), "squares")

# state areas from the ABS shapefile (exported with mapshaper)
area = pd.read_csv(RAW / "ste" / "states_info.csv").rename(
    columns={"STE_NAME21": "state", "AREASQKM21": "area_km2"})
area = area[area.state.isin(REAL_STATES)]
save(area, "state_area.csv")

# ------------------------------------------------- titles active per year
real = titles[titles.state.isin(REAL_STATES)]
rows = []
for y in range(1803, LAST_YEAR + 1):
    act = real[(real.start <= y) & (real.end >= y)].groupby("state").size()
    for s in REAL_STATES:
        rows.append({"year": y, "state": s, "titles": int(act.get(s, 0))})
active = pd.DataFrame(rows)
# Victorian titles that exist in Trove only for 1914-1918 get their own group
sl = real[real.wwi_slice == 1]
core = real[real.wwi_slice == 0]
rows = []
for y in range(1803, LAST_YEAR + 1):
    act = core[(core.start <= y) & (core.end >= y)].groupby("state").size()
    for s_ in REAL_STATES:
        g = "Northern Territory and Australian Capital Territory" if s_ in ("Northern Territory", "Australian Capital Territory") else s_
        rows.append({"group": g, "year": y, "titles": int(act.get(s_, 0))})
    rows.append({"group": "Victorian papers in Trove only for 1914\u20131918", "year": y,
                 "titles": int(((sl.start <= y) & (sl.end >= y)).sum())})
active = pd.DataFrame(rows).groupby(["group", "year"], as_index=False).titles.sum()
save(active, "active_titles_by_year_state.csv")

# --------------------------------------------------- launched vs ended
dec = pd.DataFrame({"decade": range(1830, 1950, 10)})
dec["Launched"] = dec.decade.apply(lambda d: int(((titles.start // 10 * 10) == d).sum()))
dec["Closed"] = dec.decade.apply(lambda d: int(((titles.end // 10 * 10) == d).sum()))
dec["Launched_slice"] = dec.decade.apply(lambda d: int((((titles.start // 10 * 10) == d) & (titles.wwi_slice == 1)).sum()))
dec["Closed_slice"] = dec.decade.apply(lambda d: int((((titles.end // 10 * 10) == d) & (titles.wwi_slice == 1)).sum()))
dec["Launched_core"] = dec.Launched - dec.Launched_slice
dec["Closed_core"] = dec.Closed - dec.Closed_slice
dec["label"] = dec.decade.astype(str) + "s"
dec["net"] = dec.Launched - dec.Closed
save(dec, "titles_launched_closed_by_decade.csv")

# long format for the butterfly chart: launched = negative (left), closed = positive (right)
lng = []
for _, r in dec.iterrows():
    base = {"decade": r.decade, "label": r.label, "net": r.net}
    lng += [
        {**base, "series": "Titles launched", "value": -int(r.Launched_core), "stack_order": 0},
        {**base, "series": "Victorian papers in Trove only for 1914\u20131918", "value": -int(r.Launched_slice), "stack_order": 1, "side": "launched"},
        {**base, "series": "Titles closed", "value": int(r.Closed_core), "stack_order": 0},
        {**base, "series": "Victorian papers in Trove only for 1914\u20131918", "value": int(r.Closed_slice), "stack_order": 1, "side": "closed"},
    ]
save(pd.DataFrame(lng), "butterfly_long.csv")

# ------------------------------------------------------ longest running
lr = titles[titles.state.isin(REAL_STATES)].copy()
lr["years"] = lr.end - lr.start + 1
lr = lr.sort_values("years", ascending=False).head(15)
lr["label"] = lr.short.apply(lambda t: t if len(t) <= 34 else t[:33].rstrip() + "\u2026")
lr["place"] = lr.place.fillna("")
save(lr[["title_id", "label", "place", "state", "start", "end", "years", "articles"]],
     "longest_running_titles.csv")

# ----------------------------------------------- articles per year/state
ay = pd.read_csv(RAW / "total_articles_by_year_and_state.csv")
ay = ay[ay.state.isin(REAL_STATES) & ay.year.between(1803, LAST_YEAR)].copy()
ay["group"] = ay.state.replace({"Northern Territory": "Northern Territory and Australian Capital Territory",
                                "Australian Capital Territory": "Northern Territory and Australian Capital Territory"})
stream = ay.groupby(["group", "year"], as_index=False).total.sum()
save(stream, "articles_by_year_state.csv")

# indexed to 1929 = 100
idx = ay.groupby(["state", "year"], as_index=False).total.sum()
au = idx.groupby("year", as_index=False).total.sum().assign(state="Australia")
idx = pd.concat([idx[idx.state.isin(MAIN_STATES)], au])
idx = idx[idx.year.between(1929, LAST_YEAR)]
base = idx[idx.year == 1929].set_index("state").total
idx["index"] = (idx.total / idx.state.map(base) * 100).round(1)
save(idx[["state", "year", "total", "index"]], "articles_index_1929.csv")

# -------------------------------------------------------------- bump
bump = []
for y in range(1850, 1951, 10):
    a = real[(real.start <= y) & (real.end >= y) & real.state.isin(MAIN_STATES)] \
        .groupby("state").size().reindex(MAIN_STATES, fill_value=0)
    tot = real.groupby("state").articles.sum()
    order = sorted(MAIN_STATES, key=lambda s: (-a[s], -tot.get(s, 0)))
    for r, s in enumerate(order, 1):
        bump.append({"year": y, "state": s, "titles": int(a[s]), "rank": r})
save(pd.DataFrame(bump), "bump_active_titles.csv")

# ---------------------------------------------------------- lollipop
towns = titles.dropna(subset=["place"]).copy()
towns["town"] = towns.place + ", " + towns.state.map(
    {v: k for k, v in STATE_FULL.items()})
tt = towns.groupby("town").agg(titles=("title_id", "count"),
                               articles=("articles", "sum"),
                               state=("state", "first")).reset_index()
save(tt.sort_values("titles", ascending=False).head(15), "top_towns.csv")

# --------------------------------- proportional symbol map: town table
pl = titles.dropna(subset=["lat"]).copy()
# town summary used for tooltip joins (map filters title rows directly)

# ----------------------------------------------------- heat map (Trove)
fa = pd.read_csv(RAW / "trove_newspaper_titles_first_appearance_2009_2021.csv")
fa["year"] = fa.capture_date.str[:4].astype(int)


def parse_state(p):
    if not isinstance(p, str):
        return "Other / unknown"
    tok = p.split(",")[-1].strip().upper()
    return {"VIC": "Victoria", "NSW": "New South Wales", "QLD": "Queensland",
            "SA": "South Australia", "WA": "Western Australia", "TAS": "Tasmania",
            "NT": "Northern Territory", "ACT": "Australian Capital Territory"
            }.get(tok, "Other / unknown")


fa["state"] = fa.place.apply(parse_state)
hm = fa.groupby(["year", "state"], as_index=False).size().rename(columns={"size": "titles"})
# 2009 is the first snapshot (titles already online), so start the heat map at 2010
save(hm[hm.year >= 2010], "titles_added_to_trove.csv")

# ------------------------------------------------------------- waffle
cat = pd.read_csv(RAW / "total_articles_by_category.csv").set_index("category").total
total = cat.sum()
groups = {
    "News and other articles": cat["Article"] + cat[["Arts And Culture", "Commerce And Business", "Editorial", "Humour",
                                                       "Law, Courts, And Crime", "Letters", "Literature", "News",
                                                       "Obituaries", "Official Appointments And Notices", "Puzzles",
                                                       "Reviews", "Shipping Notices", "Sport And Games", "Weather"]].sum(),
    "Advertising": cat["Advertising"] + cat[["Classified Advertisements And Notices", "Display Advertisement"]].sum(),
    "Lists, results and guides": cat["Detailed Lists, Results, Guides"],
    "Family notices": cat["Family Notices"],
}
shares = {k: v / total * 100 for k, v in groups.items()}
# largest-remainder rounding so the 100 squares add up exactly
floor = {k: int(v) for k, v in shares.items()}
left = 100 - sum(floor.values())
for k in sorted(shares, key=lambda k: shares[k] - floor[k], reverse=True)[:left]:
    floor[k] += 1
cells_w, i = [], 0
for k, n in floor.items():
    for _ in range(n):
        cells_w.append({"row": i // 10, "col": i % 10, "category": f"{k} ({floor[k]}%)",
                        "share_pct": round(shares[k], 1)})
        i += 1
save(pd.DataFrame(cells_w), "waffle_cells.csv")

# --------------------------------------------------------- the cliff
tot = pd.read_csv(RAW / "total_articles_by_year.csv")
save(tot[tot.year.between(1850, 2023)], "articles_all_years.csv")

# ------------------------------------------------------- sanity numbers
print("\nNUMBERS FOR THE STORY")
t = tot.set_index("year").total
print("articles 1850/1880/1900/1915:", t[1850], t[1880], t[1900], t[1915], "peak year", t.loc[:1954].idxmax())
print("launched/closed/net by decade:\n", dec.to_string(index=False))
print("share % ", {k: round(v, 1) for k, v in shares.items()}, "total", int(total))
print(idx[(idx.year.isin([1931, 1943])) ].pivot(index="year", columns="state", values="index"))
print(pd.DataFrame(bump).pivot(index="year", columns="state", values="rank"))
print(tt.sort_values("titles", ascending=False).head(6).to_string(index=False))
print(lr[["label", "start", "end", "years"]].to_string(index=False))
print(hm.groupby("year").titles.sum().to_dict())
print("titles total", len(titles), "with coords", titles.lat.notna().sum())

print("WWI slices:", int(titles.wwi_slice.sum()))
tot_act = active.groupby("year").titles.sum()
core_act = active[~active.group.str.startswith("Victorian papers")].groupby("year").titles.sum()
print("titles in print: peak all", tot_act.idxmax(), tot_act.max(), "| excluding slices", core_act.idxmax(), core_act.max(), "| 1900", core_act[1900], "1916", core_act[1916], "1930", core_act[1930], "1945", core_act[1945], "1954", core_act[1954])
print("SA/QLD/VIC 1943 idx:", idx[idx.year == 1943].set_index("state")["index"].to_dict())
print("lowest Australia year:", idx[idx.state == "Australia"].sort_values("index").head(2)[["year", "index"]].values.tolist())
print("1954->1955:", t[1954], t[1955], round((1 - t[1955] / t[1954]) * 100, 1), "% drop")
print("corrections share:", round(16285201 / 251022068 * 100, 1))
print("most articles title:", news.sort_values("total", ascending=False).head(3)[["short", "total"]].values.tolist())
print("non-english sample:", titles[titles.short.str.contains("Courrier|Deutsche|Zeitung|Chinese|Italian|Greek", regex=True)].short.head(8).tolist())

ne = pd.read_csv("data/newspapers_non_english.csv")
ne["start"] = ne.title.str.extract(r":\s*(\d{4})")[0].astype(int)      # first year in the "(place : 1914 - 1937)" bracket
ne = ne[ne.start <= 1954]                                                # keep to the 1803-1954 story
ne = ne[~ne.language.isin(["en", "la"]) & (ne.proportion >= 0.2)]       # a fifth or more of the text; Latin is dropped (likely OCR misreads)
ne["language_full"] = ne.language_full.str.replace(r" \(1453-\)", "", regex=True)   # "Modern Greek (1453-)" -> "Modern Greek"
lang = (ne.groupby("language_full")
          .agg(titles=("id", "nunique"), first_year=("start", "min"))
          .reset_index().sort_values(["titles", "first_year"], ascending=[False, True]))
save(lang, "non_english_languages.csv")
print("non-English languages:", lang.values.tolist())