"""Draw the timelapse of government planes and save it to figures/airspace_government_timelapse.mp4,
with a still frame for the project tile. Needs matplotlib and ffmpeg. Run after build.py."""
import json, math, bisect, os, subprocess, tempfile, glob, shutil, datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data", "viz_data.json")))
W = json.load(open(os.path.join(HERE, "data", "countries-50m.json")))

# --- decode topojson
sx, sy = W["transform"]["scale"]; tx, ty = W["transform"]["translate"]
arcs = []
for a in W["arcs"]:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)
def ring(idx):
    out = []
    for i in idx:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        out.extend(a if not out else a[1:])
    return out
polys = []
for g in W["objects"]["countries"]["geometries"]:
    if g["type"] == "Polygon":
        polys += [ring(r) for r in g["arcs"][:1]]
    elif g["type"] == "MultiPolygon":
        for p in g["arcs"]:
            polys.append(ring(p[0]))

LON0, LON1, LAT0, LAT1 = -13.5, 9.0, 45.4, 59.1
K = math.cos(math.radians(52.5))
def P(lon, lat): return (lon * K, lat)
polys = [[P(*p) for p in r] for r in polys if any(LON0 - 15 < p[0] < LON1 + 15 and LAT0 - 10 < p[1] < LAT1 + 10 for p in r)]

AP = {k: v for k, v in D["airports"].items() if k in ("Dublin", "Baldonnel/Weston", "Shannon", "Cork")}
def km(a, b, c, d):
    p = math.pi / 180
    return 6371 * math.hypot((d - b) * p * math.cos((a + c) / 2 * p), (c - a) * p)
ALL_AP = D["airports"]
def at_irish_ap(lat, lon):
    return any(km(lat, lon, a, b) < 9 for a, b in ALL_AP.values())

gov = [a for a in D["aircraft"] if a["cat"] == "gov"]
for a in gov:
    a["ts"] = [p[0] for p in a["p"]]

BG = "#0b1620"; LAND = "#1b2a36"; COAST = "#2c3e4c"; GOV = "#ff8a3d"; TXT = "#e6edf2"; MUTED = "#8aa0b0"
T0 = int(dt.datetime(2026, 11, 11, 6, tzinfo=dt.timezone.utc).timestamp())
LAST = max(os.path.basename(f)[:10] for f in glob.glob(os.path.join(HERE, "data", "tracks", "*.json")))
LAST_DAY = dt.datetime.strptime(LAST, "%Y.%m.%d").replace(tzinfo=dt.timezone.utc)
T1 = int((LAST_DAY + dt.timedelta(days=1)).timestamp())
DAYS = f"11–{LAST_DAY.day} November 2026"
STEP = 240  # 4 minutes per frame
TRAIL = 75 * 60

fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG); fig.patch.set_facecolor(BG)
ax.add_collection(PolyCollection(polys, facecolors=LAND, edgecolors=COAST, linewidths=0.6))
ax.set_xlim(LON0 * K, LON1 * K); ax.set_ylim(LAT0, LAT1); ax.set_aspect("auto"); ax.axis("off")
for n, (la, lo) in AP.items():
    x, y = P(lo, la)
    ax.plot([x], [y], marker="s", ms=3.5, color=MUTED, zorder=3)
    ax.text(x - 0.12, y - 0.22 if n != "Baldonnel/Weston" else y - 0.35, n.replace("/Weston", ""), color=MUTED, fontsize=9, ha="right", family="DejaVu Sans Mono", zorder=3)
title = ax.text(0.035, 0.955, "Government planes flying into Ireland", transform=ax.transAxes, color=TXT, fontsize=19, weight="bold", family="DejaVu Sans")
sub = ax.text(0.035, 0.925, "EPC and EU leaders' meetings, Dublin · " + DAYS, transform=ax.transAxes, color=MUTED, fontsize=11.5, family="DejaVu Sans")
clock = ax.text(0.035, 0.865, "", transform=ax.transAxes, color=TXT, fontsize=24, family="DejaVu Sans Mono", weight="bold")
count = ax.text(0.035, 0.832, "", transform=ax.transAxes, color=GOV, fontsize=12, family="DejaVu Sans")
ax.text(0.035, 0.02, "Data: adsb.lol (ODbL) · positions from volunteer ADS-B receivers · Irish Air Corps excluded", transform=ax.transAxes, color=MUTED, fontsize=8.5, family="DejaVu Sans")
trails = LineCollection([], colors=GOV, linewidths=1.6, alpha=0.55, zorder=4); ax.add_collection(trails)
dots = ax.scatter([], [], s=34, c=GOV, edgecolors=BG, linewidths=1, zorder=6)
parked = ax.scatter([], [], s=20, facecolors="none", edgecolors=GOV, linewidths=1, zorder=5, alpha=0.8)
labels = []
seen_ie = set()

def state(a, t):
    i = bisect.bisect_right(a["ts"], t) - 1
    if i < 0: return None
    p = a["p"][i]
    if t - p[0] <= 1200 and i + 1 < len(a["p"]) and a["p"][i + 1][0] - p[0] <= 1200:
        q = a["p"][i + 1]; f = (t - p[0]) / max(1, q[0] - p[0])
        return ("fly", p[2] + (q[2] - p[2]) * f, p[1] + (q[1] - p[1]) * f, i)
    if t - p[0] <= 1200:
        return ("fly", p[2], p[1], i)
    if (p[3] or 0) < 1500 and at_irish_ap(p[1], p[2]):
        return ("park", p[2], p[1], i)
    return None

FR = tempfile.mkdtemp()
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STILL = int((dt.datetime(2026, 11, 12, 10, tzinfo=dt.timezone.utc).timestamp() - T0) / STEP)
fr = 0
for t in range(T0, T1 + 1, STEP):
    segs = []; fx = []; px = []; want = []
    for l in labels: l.remove()
    labels = []
    for a in gov:
        s = state(a, t)
        if not s: continue
        k, lo, la, i = s
        if at_irish_ap(la, lo): seen_ie.add(a["h"])
        x, y = P(lo, la)
        if k == "fly":
            tr = [P(p[2], p[1]) for p in a["p"] if t - TRAIL <= p[0] <= t] + [(x, y)]
            if len(tr) > 1: segs.append(tr)
            fx.append((x, y))
            if LON0 < lo < LON1 and LAT0 < la < LAT1:
                want.append((x, y, a["country"]))
        else:
            px.append((x, y))
    placed = []
    LH, CW = 0.22, 0.083  # label height (deg lat) and char width (x units)
    dotsxy = fx[:]
    for x, y, name in sorted(want, key=lambda w: -w[1]):
        w = len(name) * CW
        cands = [(x + 0.15, y + 0.08), (x + 0.15, y - 0.3), (x - 0.15 - w, y + 0.08), (x - 0.15 - w, y - 0.3)]
        cands += [(x + 0.15, y + 0.08 + k * LH * s) for k in range(2, 7) for s in (1, -1)]
        for cx, cy in cands:
            box = (cx, cy, cx + w, cy + LH)
            if all(box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3] for b in placed):
                placed.append(box)
                labels.append(ax.text(cx, cy, name, color=TXT, fontsize=10, family="DejaVu Sans", zorder=7))
                if abs(cy - y) > 0.35:
                    labels.append(ax.plot([x, cx], [y, cy + LH / 3], color=MUTED, lw=0.5, zorder=5)[0])
                break
    trails.set_segments(segs)
    dots.set_offsets(fx if fx else [[None, None]][:0] or [[float("nan"), float("nan")]])
    parked.set_offsets(px if px else [[float("nan"), float("nan")]])
    clock.set_text(dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%a %d %b  %H:%M"))
    count.set_text(f"{len(seen_ie)} government planes so far  ·  ○ parked")
    fig.savefig(os.path.join(FR, f"f{fr:04d}.png"), facecolor=BG)
    if fr == STILL:
        shutil.copy(os.path.join(FR, f"f{fr:04d}.png"), os.path.join(ROOT, "images", "airspace.png"))
    fr += 1
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", os.path.join(FR, "f%04d.png"),
                "-vf", "tpad=stop_mode=clone:stop_duration=2,format=yuv420p", "-c:v", "libx264", "-crf", "22",
                "-movflags", "+faststart", os.path.join(ROOT, "figures", "airspace_government_timelapse.mp4")], check=True)
MP4 = os.path.join(ROOT, "figures", "airspace_government_timelapse.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", MP4, "-vf",
                "fps=12,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=48:stats_mode=diff[p];"
                "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
                os.path.join(ROOT, "figures", "airspace_government_timelapse.gif")], check=True)
shutil.rmtree(FR)
print("frames", fr)
