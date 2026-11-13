"""Stream one day of adsb.lol globe_history and extract aircraft that used Irish airports
or flew through Irish airspace. Usage: python3 -I scan_day.py 2026.11.12 out.csv"""
import sys, tarfile, gzip, json, math, csv, subprocess

day, out = sys.argv[1], sys.argv[2]
tag = f"v{day}-planes-readsb-prod-0"
base = f"https://github.com/adsblol/globe_history_2026/releases/download/{tag}/{tag}.tar."

AIRPORTS = {
    "EIDW Dublin": (53.4213, -6.2701), "EIWT Weston": (53.3522, -6.4886),
    "EIME Baldonnel": (53.3017, -6.4511), "EINN Shannon": (52.7020, -8.9248),
    "EICK Cork": (51.8413, -8.4911), "EIKN Knock": (53.9103, -8.8185),
    "EIKY Kerry": (52.1809, -9.5238), "EIWF Waterford": (52.1872, -7.0869),
    "EIDL Donegal": (55.0443, -8.3410), "EISG Sligo": (54.2802, -8.5992),
    "EGAA Belfast Intl": (54.6575, -6.2158), "EGAC Belfast City": (54.6181, -5.8725),
}
# Rough box over the island of Ireland and its coast
LAT0, LAT1, LON0, LON1 = 51.3, 55.45, -10.7, -5.4

def km(a, b, c, d):
    p = math.pi / 180
    x = (d - b) * p * math.cos((a + c) / 2 * p); y = (c - a) * p
    return 6371 * math.hypot(x, y)

def parts():
    for suf in ["aa", "ab", "ac", "ad", "ae"]:
        r = subprocess.run(["curl", "-sSLI", "-o", "/dev/null", "-w", "%{http_code}", base + suf], capture_output=True, text=True)
        if r.stdout.strip() != "200":
            break
        yield base + suf

urls = list(parts())
cat = subprocess.Popen(["curl", "-sSL", "--retry", "4"] + [x for u in urls for x in (u,)], stdout=subprocess.PIPE)
# curl with multiple URLs writes them sequentially to stdout -> concatenated tar
fields = ["day", "hex", "reg", "type", "desc", "ownOp", "dbFlags", "callsigns", "in_box_points",
          "min_alt_in_box", "first_in_box_utc", "last_in_box_utc", "airports_ground", "airports_low"]
w = csv.DictWriter(open(out, "w", newline=""), fieldnames=fields)
w.writeheader()
n = 0
with tarfile.open(fileobj=cat.stdout, mode="r|") as t:
    for m in t:
        if not m.isfile() or "/traces/" not in m.name:
            continue
        n += 1
        raw = t.extractfile(m).read()
        try:
            raw = gzip.decompress(raw)
        except EOFError:
            continue
        except OSError:
            pass
        try:
            j = json.loads(raw)
        except ValueError:
            continue
        ts = j.get("timestamp", 0)
        inbox = 0; minalt = None; first = last = None
        ground, low = set(), set()
        calls = set()
        for p in j.get("trace", []):
            lat, lon, alt = p[1], p[2], p[3]
            if lat is None or not (LAT0 - 1 < lat < LAT1 + 1 and LON0 - 1 < lon < LON1 + 1):
                continue
            if len(p) > 8 and isinstance(p[8], dict) and p[8].get("flight"):
                calls.add(p[8]["flight"].strip())
            if LAT0 < lat < LAT1 and LON0 < lon < LON1:
                inbox += 1
                a = 0 if alt == "ground" else alt
                if isinstance(a, (int, float)):
                    minalt = a if minalt is None else min(minalt, a)
                tt = ts + p[0]
                first = tt if first is None else first; last = tt
                if alt == "ground" or (isinstance(alt, (int, float)) and alt < 2500):
                    for name, (alat, alon) in AIRPORTS.items():
                        dd = km(lat, lon, alat, alon)
                        if alt == "ground" and dd < 4:
                            ground.add(name)
                        elif dd < 10 and isinstance(alt, (int, float)) and alt < 2500:
                            low.add(name)
        if inbox == 0:
            continue
        import datetime as dt
        f = lambda x: dt.datetime.utcfromtimestamp(x).strftime("%Y-%m-%d %H:%M")
        w.writerow({"day": day, "hex": j.get("icao"), "reg": j.get("r"), "type": j.get("t"),
                    "desc": j.get("desc"), "ownOp": j.get("ownOp"), "dbFlags": j.get("dbFlags"),
                    "callsigns": "|".join(sorted(calls)), "in_box_points": inbox, "min_alt_in_box": minalt,
                    "first_in_box_utc": f(first), "last_in_box_utc": f(last),
                    "airports_ground": "|".join(sorted(ground)), "airports_low": "|".join(sorted(low))})
print(day, "traces scanned:", n, file=sys.stderr)
