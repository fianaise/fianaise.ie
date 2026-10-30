"""Download the Department of Education's mainstream primary school lists.

Each school year the Department publishes "Data on Individual Schools": a
spreadsheet of every primary school with its ethos, county and coordinates.
This script reads the gov.ie collection page (and the pages it links to),
finds the primary mainstream spreadsheets, and saves any that are new or
changed to analysis/charts/data/raw/ as

    Data_on_Individual_Schools_Mainstream_<YYYY>_<YY>[_preliminary].xlsx

which is where analysis/charts/make_maps.py looks for them. Lists older than
the newest one already saved are skipped. A file is only rewritten when its
contents change, so a run with nothing new leaves the repo untouched.

Usage (from the repo root):
    pip install requests beautifulsoup4 pandas openpyxl
    python3 tools/fetch_school_lists.py
"""
import io
import os
import re
import sys
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW = os.path.join(ROOT, "analysis", "charts", "data", "raw")
sys.path.insert(0, os.path.join(ROOT, "analysis", "charts"))

COLLECTION = "https://www.gov.ie/en/department-of-education/collections/data-on-individual-schools/"
CKAN = "https://data.gov.ie/api/3/action/package_search"
HEADERS = {"User-Agent": "fianaise.ie data refresh (+https://github.com/fianaise/fianaise.ie)"}
SKIP = re.compile(r"post[- ]?primary|second[- ]level", re.I)


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r


def school_year(text):
    """'2025/2026', '2025-26', '2025_26' -> '2025_26'; None if no year."""
    m = re.search(r"(20\d\d)\s*[-_/ ]\s*(?:20)?(\d\d)(?!\d)", text)
    return f"{m.group(1)}_{m.group(2)}" if m else None


def spreadsheet_links(url, depth=1, seen=None):
    """(xlsx url, (link text, page heading)) for every spreadsheet on a page and, to the
    given depth, on the gov.ie pages it links to."""
    seen = seen if seen is not None else set()
    if url in seen:
        return []
    seen.add(url)
    soup = BeautifulSoup(get(url).text, "html.parser")
    heading = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else ""
    found, pages = [], []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        text = a.get_text(" ", strip=True)
        if urlparse(href).path.lower().endswith((".xlsx", ".xls")):
            found.append((href, (f"{text} | {os.path.basename(urlparse(href).path)}", heading)))
        elif (depth > 0 and urlparse(href).netloc == "www.gov.ie"
              and "individual-schools" in href.lower() and href.split("#")[0] != url):
            pages.append(href.split("#")[0])
    for page in pages:
        found += spreadsheet_links(page, depth - 1, seen)
    return found


def data_gov_ie_links():
    """The same spreadsheets as listed on data.gov.ie, the national open data portal."""
    r = get(f'{CKAN}?q="individual schools"&rows=50').json()
    found = []
    for pkg in r["result"]["results"]:
        for res in pkg.get("resources", []):
            url = res.get("url") or ""
            if urlparse(url).path.lower().endswith((".xlsx", ".xls")) or (res.get("format") or "").lower() in ("xlsx", "xls"):
                found.append((url, (f"{res.get('name') or ''} | {os.path.basename(urlparse(url).path)}", pkg.get("title", ""))))
    return found


def main():
    from make_maps import latest_school_list, read_school_list, school_list_year

    newest = school_list_year(latest_school_list()).replace("-", "_")
    links = {}
    for name, source in (("gov.ie", lambda: spreadsheet_links(COLLECTION)), ("data.gov.ie", data_gov_ie_links)):
        try:
            found = dict(source())
        except (requests.RequestException, KeyError, ValueError) as e:
            print(f"{name}: could not read ({e})")
            continue
        print(f"{name}: {len(found)} spreadsheets")
        links.update(found)
    print(f"Newest saved list is {newest}")
    if not links:
        sys.exit("No spreadsheets found on gov.ie or data.gov.ie; the pages may have changed.")
    changed = 0
    for href, (link, heading) in links.items():
        # The link's own year wins over the page's: a page can list past years too.
        year = school_year(link) or school_year(heading)
        context = f"{heading} | {link}"
        if not year or year < newest or SKIP.search(context) or not re.search(r"primary|mainstream", context, re.I):
            print(f"  skip {year or 'no year'}: {context}")
            continue
        content = get(href).content
        try:
            df = read_school_list(io.BytesIO(content))
        except (StopIteration, ValueError) as e:
            print(f"  skip {href}: no mainstream sheet ({e!r})")
            continue
        if "Ethos Description" not in df.columns or "School Latitude" not in df.columns:
            print(f"  skip {href}: missing ethos or coordinates")
            continue
        suffix = "_preliminary" if "preliminary" in context.lower() else ""
        out = os.path.join(RAW, f"Data_on_Individual_Schools_Mainstream_{year}{suffix}.xlsx")
        if os.path.exists(out) and open(out, "rb").read() == content:
            print(f"  unchanged {os.path.basename(out)}")
            continue
        with open(out, "wb") as f:
            f.write(content)
        changed += 1
        print(f"  saved {os.path.basename(out)} ({len(df):,} schools) from {href}")
    print(f"{changed} school list(s) new or updated")


if __name__ == "__main__":
    main()
