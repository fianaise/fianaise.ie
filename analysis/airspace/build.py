"""Merge the tracks in data/tracks/ into data/viz_data.json, with each aircraft's country and its
landings and take-offs at Irish airports. Run after summarise.py and tracks.py."""
import json, math, glob, re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
AP = {"Dublin": (53.4213, -6.2701), "Baldonnel/Weston": (53.32, -6.47), "Shannon": (52.7020, -8.9248),
      "Cork": (51.8413, -8.4911), "Knock": (53.9103, -8.8185), "Kerry": (52.1809, -9.5238),
      "Waterford": (52.1872, -7.0869), "Donegal": (55.0443, -8.3410), "Sligo": (54.2802, -8.5992)}
GOV_CIVIL = {"3A-MGA": "Monaco", "YU-SRB": "Serbia", "Z3-MKD": "North Macedonia", "4L-GTG": "Georgia",
             "9A-CRO": "Croatia", "OM-BYA": "Slovakia", "OM-BYB": "Slovakia", "G-GBNI": "United Kingdom",
             "4K-AI001": "Azerbaijan", "F-HYTV": "France", "UR-ABA": "Ukraine"}
MIL_COUNTRY = {"SAM": "United States", "GAF": "Germany", "IAM": "Italy", "PLF": "Poland", "HAF": "Greece",
               "CTM": "France", "AFP": "Portugal", "ROF": "Romania", "BGF": "Bulgaria", "SUI": "Switzerland",
               "FIE": "Hungary", "CEF": "Czechia", "CFC": "Canada", "LYF": "Lithuania", "SSG": "Slovakia",
               "UKN": "Ukraine", "KRH": "United Kingdom", "AHY": "Azerbaijan", "LSV": "Luxembourg"}

def km(a, b, c, d):
    p = math.pi / 180
    return 6371 * math.hypot((d - b) * p * math.cos((a + c) / 2 * p), (c - a) * p)

def near_ap(lat, lon):
    for n, (a, b) in AP.items():
        if km(lat, lon, a, b) < 9:
            return n
    return None

merged = {}
for f in sorted(glob.glob(os.path.join(DATA, "tracks", "*.json"))):
    for h, v in json.load(open(f)).items():
        m = merged.setdefault(h, {**v, "pts": []})
        m["pts"] += v["pts"]

import csv
rows = list(csv.DictReader(open(os.path.join(DATA, "aircraft.csv"))))
calls = {}
for r in rows:
    calls.setdefault(r["hex"].lower(), set()).update(x for x in r["callsigns"].split("|") if x)

out = []
moves = []
for h, v in merged.items():
    pts = sorted(v["pts"])
    if not pts:
        continue
    reg = v.get("r") or h.upper()
    mil = int(v.get("dbFlags") or 0) & 1
    cs = sorted(calls.get(h, []))
    country = GOV_CIVIL.get(reg)
    if not country:
        for c in cs:
            if c[:3] in MIL_COUNTRY:
                country = MIL_COUNTRY[c[:3]]; break
    if not country and v.get("ownOp", "") and "Government of" in (v.get("ownOp") or ""):
        country = v["ownOp"].replace("Government of ", "")
    cat = "gov" if (mil or reg in GOV_CIVIL or country) else "private"
    if cat == "gov" and not country:
        country = "Unidentified"
    # movements
    state = None; run = None
    for i, (t, la, lo, al) in enumerate(pts):
        low = al is not None and isinstance(al, (int, float)) and al < 1500
        ap = near_ap(la, lo) if low else None
        if ap:
            if run is None:
                run = [ap, i, i]
            else:
                run[2] = i
        else:
            if run is not None:
                ap_, s, e = run
                if s > 0 and (pts[s][0] - pts[s - 1][0]) < 1800:
                    moves.append({"h": h, "ap": ap_, "t": pts[s][0], "k": "arr"})
                if pts[i][0] - pts[e][0] < 1800:
                    moves.append({"h": h, "ap": ap_, "t": pts[e][0], "k": "dep"})
                run = None
    if run is not None:
        ap_, s, e = run
        if s > 0 and (pts[s][0] - pts[s - 1][0]) < 1800:
            moves.append({"h": h, "ap": ap_, "t": pts[s][0], "k": "arr"})
    out.append({"h": h, "reg": reg, "type": v.get("t"), "desc": v.get("desc"), "op": v.get("ownOp"),
                "cat": cat, "country": country, "cs": cs,
                "p": [[t, la, lo, al if isinstance(al, (int, float)) else 0] for t, la, lo, al in pts]})
# only keep aircraft with at least one Irish movement
mv_h = {m["h"] for m in moves}
out = [o for o in out if o["h"] in mv_h]
for m in moves:
    m["cat"] = next(o["cat"] for o in out if o["h"] == m["h"])
json.dump({"aircraft": out, "moves": moves, "airports": AP}, open(os.path.join(DATA, "viz_data.json"), "w"), separators=(",", ":"))
from collections import Counter
print(len(out), Counter(o["cat"] for o in out), len(moves), Counter((m["k"], m["cat"]) for m in moves))
print([ (o["reg"], o["country"]) for o in out if o["cat"]=="gov"])
