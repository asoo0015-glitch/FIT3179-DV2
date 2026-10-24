"""
make_cells.py - the equal-area square grid behind the bin map (js/08_bin_map.vg.json).

Why: the bin map shades each square by how many titles it holds, so every square must cover the
same area. The old grid was 2-degree longitude/latitude boxes, whose area shrinks towards the south
(a box in Tasmania is about 25% smaller than one in Cape York) and that is not a fair comparison.
Here the squares are 200 km x 200 km in the Albers equal-area conic projection that every map on the
page uses, so each square really covers 40,000 km2.

The projection maths below is the same spherical conic equal-area formula d3-geo uses (the library
inside Vega-Lite), with the same settings as the maps: standard parallels 18 S and 36 S and central
meridian 132 E. That makes each square come out as an exact upright square on screen.

Run from the project folder:    python make_cells.py
It reads data/titles.csv, rewrites its cell_id column and writes data/cells.geojson.
prepare_data.py imports cell_id_for() / build_cells() from here, so the grid is defined in one place.
Needs only the standard library.
"""
import csv
import json
import math
from pathlib import Path

# ---- settings shared with make_specs.py (PROJECTION) ------------------------------------------
PARALLELS = (-18.0, -36.0)   # standard parallels, as in Geoscience Australia's "Australian Albers"
CENTRAL_MERIDIAN = 132.0     # degrees east
SIDE_KM = 200.0              # width of a bin-map square
EARTH_RADIUS_KM = 6371.0088  # d3 treats the Earth as a sphere

_phi0, _phi1 = (math.radians(p) for p in PARALLELS)
_n = (math.sin(_phi0) + math.sin(_phi1)) / 2
_c = 1 + math.sin(_phi0) * (2 * _n - math.sin(_phi0))
_r0 = math.sqrt(_c) / _n
SIDE = SIDE_KM / EARTH_RADIUS_KM          # square width on the unit sphere


def project(lon, lat):
    """lon/lat in degrees -> (x, y) on the unit sphere, y pointing north."""
    lam = math.radians(lon - CENTRAL_MERIDIAN)
    r = math.sqrt(_c - 2 * _n * math.sin(math.radians(lat))) / _n
    return r * math.sin(lam * _n), _r0 - r * math.cos(lam * _n)


def unproject(x, y):
    """(x, y) -> lon/lat in degrees (inverse of project)."""
    r0y = _r0 - y
    sign = 1 if r0y > 0 else -1
    lam = math.atan2(x, abs(r0y)) * sign
    if r0y * _n < 0:
        lam -= math.pi * (1 if x > 0 else -1) * sign
    lat = math.degrees(math.asin((_c - (x * x + r0y * r0y) * _n * _n) / (2 * _n)))
    return math.degrees(lam / _n) + CENTRAL_MERIDIAN, lat


def cell_index(lon, lat):
    x, y = project(lon, lat)
    return math.floor(x / SIDE), math.floor(y / SIDE)


def cell_id_for(lon, lat):
    """Name of the square holding this point, e.g. '3_-9' (column_row)."""
    i, j = cell_index(lon, lat)
    return f"{i}_{j}"


def cell_polygon(cell_id):
    """GeoJSON polygon for a square, corners in lon/lat. Clockwise (south-west, north-west, north-east,
    south-east), the winding d3-geo expects for an exterior ring."""
    i, j = map(int, cell_id.split("_"))
    corners = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j), (i, j)]
    ring = [[round(v, 4) for v in unproject(a * SIDE, b * SIDE)] for a, b in corners]
    return {"type": "Feature", "properties": {"cell_id": cell_id},
            "geometry": {"type": "Polygon", "coordinates": [ring]}}


def build_cells(cell_ids):
    ids = sorted({c for c in cell_ids if c}, key=lambda s: tuple(map(int, s.split("_"))))
    return {"type": "FeatureCollection", "features": [cell_polygon(c) for c in ids]}


if __name__ == "__main__":
    data = Path("data")
    with open(data / "titles.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    for r in rows:
        r["cell_id"] = cell_id_for(float(r["lon"]), float(r["lat"])) if r["lat"] != "" and r["lon"] != "" else ""
    # newline="" + lineterminator="\n" keeps the file's existing LF line endings on every platform
    with open(data / "titles.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    cells = build_cells(r["cell_id"] for r in rows)
    (data / "cells.geojson").write_text(json.dumps(cells), encoding="utf-8")
    print("titles.csv: cell_id updated for", sum(1 for r in rows if r["cell_id"]), "titles")
    print("cells.geojson:", len(cells["features"]), "squares of", SIDE_KM, "km x", SIDE_KM, "km")
