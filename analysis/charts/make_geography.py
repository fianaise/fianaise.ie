"""Build the simplified county outlines the maps draw on.

Reads Natural Earth's 1:10m admin-1 boundaries, keeps the 26 counties
(merging Dublin's four council areas, the two Tipperarys, and the city and
county parts of Cork, Galway, Limerick and Waterford) plus Northern Ireland
as one context shape, simplifies them, and writes
analysis/charts/data/ireland_counties.geojson.

Usage: python3 analysis/charts/make_geography.py path/to/ne_10m_admin_1_states_provinces.geojson
(download from https://github.com/nvkelso/natural-earth-vector/tree/master/geojson)
"""
import json
import os
import sys

from shapely.geometry import MultiPolygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

NAME_MAP = {
    "Laoighis": "Laois",
    "North Tipperary": "Tipperary",
    "South Tipperary": "Tipperary",
    "Dún Laoghaire–Rathdown": "Dublin",
    "Fingal": "Dublin",
    "South Dublin": "Dublin",
}
TOLERANCE = 0.004   # degrees, about 300 m


def clockwise(geom):
    """d3-geo, which Plotly draws with, wants exterior rings clockwise."""
    if geom.geom_type == "Polygon":
        return orient(geom, sign=-1.0)
    return MultiPolygon([orient(p, sign=-1.0) for p in geom.geoms])


def rounded(geom):
    geom = clockwise(geom)

    def r(c):
        return [round(c[0], 4), round(c[1], 4)]
    g = mapping(geom)
    if g["type"] == "Polygon":
        g["coordinates"] = [[r(c) for c in ring] for ring in g["coordinates"]]
    else:
        g["coordinates"] = [[[r(c) for c in ring] for ring in poly] for poly in g["coordinates"]]
    return g


ne = json.load(open(sys.argv[1], encoding="utf-8"))
counties, ni = {}, []
for f in ne["features"]:
    p = f["properties"]
    if p.get("admin") == "Ireland":
        counties.setdefault(NAME_MAP.get(p["name"], p["name"]), []).append(shape(f["geometry"]))
    elif p.get("admin") == "United Kingdom" and p.get("geonunit") == "Northern Ireland":
        ni.append(shape(f["geometry"]))

features = [
    {"type": "Feature", "id": name, "properties": {"name": name},
     "geometry": rounded(unary_union(parts).simplify(TOLERANCE, preserve_topology=True))}
    for name, parts in sorted(counties.items())
]
features.append({"type": "Feature", "id": "Northern Ireland", "properties": {"name": "Northern Ireland"},
                 "geometry": rounded(unary_union(ni).simplify(TOLERANCE, preserve_topology=True))})
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ireland_counties.geojson")
json.dump({"type": "FeatureCollection", "features": features}, open(out, "w", encoding="utf-8"), separators=(",", ":"))
print(f"wrote {out}: {len(features) - 1} counties + Northern Ireland")
