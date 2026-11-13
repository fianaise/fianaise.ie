"""Write the tables on the Irish airspace page (airspace/_*.md) from data/viz_data.json and
data/daily-summary.csv. Run from anywhere after build.py: python3 -I analysis/airspace/make_page.py"""
import csv, json, os, datetime as dt
from collections import defaultdict
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
D = json.load(open(os.path.join(HERE, "data", "viz_data.json")))
OPS = {"NJE": "NetJets Europe", "VJT": "VistaJet", "FJO": "Flexjet", "LUA": "Luxaviation"}


def when(t):
    # Ireland is on GMT in November, so UTC is Irish time.
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%a %d %b, %H:%M")


moves = defaultdict(list)
for m in D["moves"]:
    moves[m["h"]].append(m)


def movement_text(h):
    out = []
    for m in sorted(moves[h], key=lambda m: m["t"]):
        verb = "landed at" if m["k"] == "arr" else "left"
        out.append(f"{verb} {m['ap']} {when(m['t'])}")
    return "; ".join(out) if out else ""


def first_time(a):
    ms = moves[a["h"]]
    return min(m["t"] for m in ms) if ms else 0


def tidy(s):
    return " ".join(w.capitalize() if w.isupper() and len(w) > 3 and w.isalpha() else w for w in (s or "").split())


def aircraft_row(a, who=None):
    cells = [escape(a["reg"] or ""), escape(tidy(a.get("desc")) or a.get("type") or ""),
             escape(", ".join(a["cs"])), escape(movement_text(a["h"]))]
    if who is not None:
        cells.insert(0, escape(who))
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


gov = [a for a in D["aircraft"] if a["cat"] == "gov"]
by_country = defaultdict(list)
for a in gov:
    by_country[a["country"]].append(a)
order = sorted(by_country, key=lambda c: min(first_time(a) for a in by_country[c]))

lines = ['<div class="airspace-table">', "",
         f"{len(gov)} government aircraft from {len([c for c in by_country if c != 'Unidentified'])} countries. "
         "Click a country to see each plane, its serial or registration, its callsigns and when it landed and left.", ""]
for c in order:
    planes = sorted(by_country[c], key=first_time)
    aps = sorted({m["ap"] for a in planes for m in moves[a["h"]]})
    first = min(first_time(a) for a in planes)
    n = len(planes)
    lines.append(f'<details><summary><span class="as-country">{escape(c)}</span>'
                 f'<span class="as-meta">{n} plane{"s" if n > 1 else ""} · {escape(", ".join(aps))} · first seen {when(first)}</span></summary>')
    lines.append('<table class="table table-sm"><thead><tr><th>Serial or registration</th><th>Aircraft</th>'
                 '<th>Callsigns</th><th>Landings and take-offs in Ireland</th></tr></thead><tbody>')
    lines += [aircraft_row(a) for a in planes]
    lines.append("</tbody></table></details>")
lines += ["", "</div>", ""]
open(os.path.join(ROOT, "airspace", "_government-flights.md"), "w").write("\n".join(lines))

priv = sorted([a for a in D["aircraft"] if a["cat"] == "private"], key=first_time)


def operator(a):
    for c in a["cs"]:
        if c[:3] in OPS:
            return OPS[c[:3]]
    if a.get("op"):
        return a["op"].split(",")[0].title()
    return "Not listed"


lines = ['<div class="airspace-table">', "",
         f'<details><summary><span class="as-country">Private and charter jets</span>'
         f'<span class="as-meta">{len(priv)} planes · operator as registered, or from the callsign</span></summary>',
         '<table class="table table-sm"><thead><tr><th>Operator</th><th>Registration</th><th>Aircraft</th>'
         '<th>Callsigns</th><th>Landings and take-offs in Ireland</th></tr></thead><tbody>']
lines += [aircraft_row(a, operator(a)) for a in priv]
lines += ["</tbody></table></details>", "", "</div>", ""]
open(os.path.join(ROOT, "airspace", "_private-jets.md"), "w").write("\n".join(lines))

rows = list(csv.DictReader(open(os.path.join(HERE, "data", "daily-summary.csv"))))
lines = ["| Day | Foreign government and military aircraft | Business jets | All aircraft using an Irish airport |",
         "| --- | ---: | ---: | ---: |"]
for r in rows:
    d = dt.datetime.strptime(r["date"], "%Y-%m-%d").strftime("%a %d %b")
    if r["note"]:
        d += " (incomplete data)"
    if r["date"] >= "2026-11-11":
        d = f"**{d}**"
    lines.append(f"| {d} | {r['foreign_military_state_aircraft']} | {r['bizjets_using_irish_airport']} | {r['aircraft_using_irish_airport']} |")
open(os.path.join(ROOT, "airspace", "_daily-counts.md"), "w").write("\n".join(lines) + "\n")
print("written")
