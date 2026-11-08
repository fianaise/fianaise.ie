"""Load DLR's hourly bicycle counts into one tidy table.

DLR publishes one CSV per year on Smart Dublin, and the column names drift
from year to year (spelling, direction labels, notes such as "Decommissioned
Counter"). This module maps every year's total column for each counter onto
one stable key, drops the per-direction columns, and cleans out counter
faults. Both chart scripts in this folder use it.
"""
import glob
import os
import re

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "analysis", "cycling", "data", "raw")

# key: (label, area, site, lat, lon, what it counts). Coordinates from DLR's
# "Bicycle/Pedestrian Counter Locations" dataset. "site" groups counters that
# stand within a few metres of each other, for the map.
COUNTERS = {
    "seapoint": ("Seapoint (Coastal Mobility Route)", "Dún Laoghaire", "Seapoint", 53.297513, -6.160875, "two-way, shared path"),
    "york_road": ("York Road", "Dún Laoghaire", "York Road", 53.296157, -6.142648, "two-way"),
    "peoples_park": ("People's Park", "Dún Laoghaire", "People's Park", 53.291536, -6.128758, "two-way, shared path"),
    "glenageary": ("The Metals, Glenageary DART", "Glenageary", "The Metals", 53.281353, -6.123037, "two-way, shared path"),
    "rock_road_totem": ("Rock Road cycle track", "Booterstown", "Rock Road", 53.308175, -6.195250, "cycle track (inbound only before 2026)"),
    "rock_road_bus_lane": ("Rock Road bus lane", "Booterstown", "Rock Road", 53.308565, -6.195736, "one-way"),
    "rock_road_park": ("Rock Road park path", "Booterstown", "Rock Road", 53.308825, -6.195771, "two-way, shared path"),
    "n11_totem": ("N11 Stillorgan Road, inbound", "Stillorgan Road", "N11", 53.306391, -6.212898, "inbound"),
    "n11_montrose": ("N11 Stillorgan Road, Montrose", "Stillorgan Road", "N11", 53.306917, -6.213177, "two-way cycle track"),
    "n11_ucd": ("N11 before UCD", "Stillorgan Road", "N11", 53.304632, -6.210272, "two-way"),
    "clonskeagh": ("Clonskeagh Road", "Clonskeagh", "Clonskeagh", 53.306328, -6.237046, "two-way"),
    "grange_road": ("Grange Road", "Rathfarnham", "Grange Road", 53.286436, -6.277608, "one-way"),
    "wyattville_from_n11": ("Wyattville Road, from N11", "Loughlinstown", "Wyattville Road", 53.250735, -6.133348, "one-way"),
    "wyattville_to_n11": ("Wyattville Road, towards N11", "Loughlinstown", "Wyattville Road", 53.250396, -6.133277, "one-way"),
    "wyattville_park_gates": ("Wyattville Road, park gates", "Loughlinstown", "Wyattville Road", 53.251206, -6.132942, "two-way, shared path"),
    "wyattville_steps": ("Wyattville Road, steps (closed)", "Loughlinstown", "Wyattville Road", 53.251153, -6.132481, "two-way, shared path"),
}

PATTERNS = [
    (r"seapoint beach", "seapoint"),
    (r"york road", "york_road"),
    (r"peoples park", "peoples_park"),
    (r"^glenageary", "glenageary"),
    (r"^rock road totem", "rock_road_totem"),
    (r"^rock road bus lane", "rock_road_bus_lane"),
    (r"^rock road park", "rock_road_park"),
    (r"^n11 totem", "n11_totem"),
    (r"^n11 outbound \(montrose\)", "n11_montrose"),
    (r"^n11 before ucd", "n11_ucd"),
    (r"^clonskeagh", "clonskeagh"),
    (r"^grange road", "grange_road"),
    (r"bicycles from n11", "wyattville_from_n11"),
    (r"bicycles towards n11", "wyattville_to_n11"),
    (r"park gates", "wyattville_park_gates"),
    (r"at steps", "wyattville_steps"),
]
DIRECTION = re.compile(r"(\bin\b|\bout\b|north|south|\bin-|\bout-)", re.I)


def counter_key(column):
    """The counter a total column belongs to, or None for direction splits."""
    n = column.lower().replace("(montrose)", "MONTROSE")
    if DIRECTION.search(n):
        return None
    n = n.replace("MONTROSE", "(montrose)").replace("laogaire", "laoghaire")
    for pattern, key in PATTERNS:
        if re.search(pattern, n):
            return key
    return None


def load_hourly():
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW, "bicycle-traffic-counts-dlr__*.csv"))):
        d = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        t = d.columns[0]
        dayfirst = d[t].astype(str).str.match(r"\d\d/\d\d/\d{4}").all()
        fmt = "%d/%m/%Y %H:%M" if dayfirst else "%b %d, %Y %I:%M %p"
        keep = {c: counter_key(c) for c in d.columns[1:] if counter_key(c)}
        x = d[list(keep)].rename(columns=keep).apply(pd.to_numeric, errors="coerce")
        x = x.T.groupby(level=0).first().T  # one column per counter
        x.index = pd.to_datetime(d[t], format=fmt, errors="coerce")
        x = x[x.index.notna()]
        frames.append(x.groupby(level=0).sum(min_count=1))
    h = pd.concat(frames).sort_index()
    return h.groupby(level=0).first()


def clean_daily(h):
    """Daily totals, with counter faults removed.

    A day is dropped when it has fewer than 22 hours of data, a total of zero,
    or a total under a quarter of that counter's median over the surrounding
    four weeks.
    """
    day = h.resample("D").sum(min_count=22)
    ref = day.rolling(28, center=True, min_periods=7).median()
    return day.where((day > 0) & (day >= 0.25 * ref))
