"""Write the data behind the charities graphic as a CSV, for the "Download data"
button under it on the site: figures/data/charities_landscape.csv.

Reads the data.json that build_data.py writes (or, with --from-figure, the copy
inlined in figures/charities_landscape.html).

Usage: python3 -I write_csv.py data.json ../../figures/data/charities_landscape.csv
       python3 -I write_csv.py --from-figure ../../figures/charities_landscape.html ../../figures/data/charities_landscape.csv
"""
import csv
import json
import re
import sys


def load(args):
    if args[0] == "--from-figure":
        html = open(args[1], encoding="utf-8").read()
        m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
        return json.loads(m.group(1).replace("<\\/", "</")), args[2]
    return json.load(open(args[0], encoding="utf-8")), args[1]


d, out = load(sys.argv[1:])
purposes = [h["full"] for h in sorted(d["hubs"], key=lambda h: h["id"])]
school_kind = {0: "", 1: "Catholic ethos", 2: "Joint Catholic patronage"}
source = (f"Charities Regulator, Public Register of Charitable Organisations (effective {d['stats'].get('effective', '')}); "
          "school ethos and patron from Department of Education, Data on Individual Schools; "
          "https://fianaise.ie/religion/charities.html")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Registered charity number", "Charity name", "County", "Governing form", "Charitable purposes",
                "Matched school", "School ethos", "School patron", "Catholic school", "Source"])
    for i, r in enumerate(d["c"]):
        mask, name, number, county, form = r[2], r[3], r[4], r[5], r[6]
        ethos = d["ethos"][r[8]] if r[8] >= 0 else ""
        patron = d["patrons"][r[9]] if r[9] >= 0 else ""
        purp = "; ".join(p for j, p in enumerate(purposes) if mask & (1 << j))
        w.writerow([number, name, county, form, purp, r[10], ethos, patron, school_kind.get(r[11], ""),
                    source if i == 0 else ""])
print("wrote", out, len(d["c"]))
