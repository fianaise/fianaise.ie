"""Download Dún Laoghaire-Rathdown's open bicycle counter data.

DLR publishes hourly counts from its permanent bicycle counters on Smart Dublin
(data.smartdublin.ie), one CSV per year, plus a dataset of counter locations.
This script asks the Smart Dublin CKAN API for both datasets and saves every
CSV and GeoJSON resource to analysis/cycling/data/raw/, keeping the file name
the council gave it. A file is only rewritten when its contents change, so a
run with nothing new leaves the repo untouched.

Licence: Creative Commons Attribution (DLR via Smart Dublin).

Usage (from the repo root):
    pip install requests
    python3 tools/fetch_cycle_counts.py
"""
import os
import sys
from urllib.parse import urlparse

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "analysis", "cycling", "data", "raw")
API = "https://data.smartdublin.ie/api/3/action/package_show"
DATASETS = ["bicycle-traffic-counts-dlr", "bicycle-counter-locations-dlr"]
FORMATS = {"csv", "geojson"}
HEADERS = {"User-Agent": "fianaise.ie data refresh (+https://github.com/fianaise/fianaise.ie)"}


def main():
    os.makedirs(RAW, exist_ok=True)
    changed = 0
    for ds in DATASETS:
        r = requests.get(API, params={"id": ds}, headers=HEADERS, timeout=60)
        r.raise_for_status()
        for res in r.json()["result"]["resources"]:
            if (res.get("format") or "").lower() not in FORMATS:
                continue
            name = os.path.basename(urlparse(res["url"]).path)
            if not name:
                continue
            body = requests.get(res["url"], headers=HEADERS, timeout=300)
            body.raise_for_status()
            path = os.path.join(RAW, f"{ds}__{name}")
            old = open(path, "rb").read() if os.path.exists(path) else None
            if old != body.content:
                with open(path, "wb") as f:
                    f.write(body.content)
                changed += 1
                print("saved", os.path.relpath(path, ROOT), len(body.content))
    print(f"{changed} file(s) new or changed")


if __name__ == "__main__":
    sys.exit(main())
