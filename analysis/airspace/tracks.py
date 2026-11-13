"""Pull the full tracks of the aircraft in data/hexes.txt for one day.
Usage: python3 -I tracks.py 2026.11.12 data/tracks/2026.11.12.json data/hexes.txt"""
import sys, tarfile, gzip, json, subprocess
day, out = sys.argv[1], sys.argv[2]
want = set(open(sys.argv[3]).read().split())
tag = f"v{day}-planes-readsb-prod-0"
base = f"https://github.com/adsblol/globe_history_2026/releases/download/{tag}/{tag}.tar."
cat = subprocess.Popen(["curl", "-sSL", "--retry", "4", base + "aa", base + "ab", base + "ac"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
res = {}
try:
  with tarfile.open(fileobj=cat.stdout, mode="r|") as t:
    for m in t:
        if not m.isfile() or "/traces/" not in m.name: continue
        h = m.name.rsplit("trace_full_", 1)[-1].split(".")[0].lower().lstrip("~")
        if h not in want: continue
        raw = t.extractfile(m).read()
        try: raw = gzip.decompress(raw)
        except Exception: pass
        j = json.loads(raw); ts = j["timestamp"]; pts = []; last = -999
        for p in j["trace"]:
            if p[1] is None: continue
            if p[0] - last < 60: continue
            last = p[0]
            pts.append([int(ts + p[0]), round(p[1], 3), round(p[2], 3), 0 if p[3] == "ground" else p[3]])
        res[h] = {"r": j.get("r"), "t": j.get("t"), "desc": j.get("desc"), "ownOp": j.get("ownOp"), "dbFlags": j.get("dbFlags"), "pts": pts}
except Exception as e:
    print("err", e, file=sys.stderr)
json.dump(res, open(out, "w"))
print(day, len(res), file=sys.stderr)
