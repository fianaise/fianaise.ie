"""Summarise the daily scans in data/daily/ into data/daily-summary.csv and
data/aircraft.csv (government and business jets that used an Irish airport),
and write data/hexes.txt for tracks.py. Run from the repository root:
python3 -I analysis/airspace/summarise.py"""
import glob, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
BIZ = set("""GLF2 GLF3 GLF4 GLF5 GLF6 GL5T GL6T GL7T GL8T GLEX GA5C GA6C GA7C GA8C CL30 CL35 CL60 CL65
FA10 FA20 FA50 FA7X FA8X FA6X F900 F2TH C25A C25B C25C C25M C500 C501 C510 C525 C526 C550 C551 C55B C560 C56X
C650 C680 C68A C700 C750 E50P E55P E545 E550 E35L LJ31 LJ35 LJ40 LJ45 LJ55 LJ60 LJ70 LJ75 LJ85 H25A H25B H25C
HA4T PRM1 BE40 PC24 SF50 HDJT EA50 ASTR G150 G280 WW24 GALX BBJ1 BBJ2""".split())
INCOMPLETE = {"2026-11-06": "archive incomplete (about 70% of a usual day)"}

files = [f for f in sorted(glob.glob(os.path.join(DATA, "daily", "*.csv"))) if os.path.getsize(f) > 10]
d = pd.concat([pd.read_csv(f) for f in files]).reset_index(drop=True)
d["date"] = pd.to_datetime(d.day, format="%Y.%m.%d").dt.strftime("%Y-%m-%d")
d["mil"] = (d.dbFlags.fillna(0).astype(int) & 1) == 1
d["biz"] = d.type.isin(BIZ)
both = d.airports_ground.fillna("") + "|" + d.airports_low.fillna("")
d["ie_ap"] = both.apply(lambda s: "|".join(sorted({a for a in s.split("|") if a.startswith("EI")})))
irish_air_corps = d.reg.astype(str).str.match(r"^(2\d\d|TWR)$")
d["foreign_state"] = d.mil & ~irish_air_corps & (d.ie_ap != "")
d["bizjet"] = d.biz & (d.ie_ap != "") & ~d.mil

t = d.groupby("date").agg(
    aircraft_in_irish_box=("hex", "count"),
    aircraft_using_irish_airport=("ie_ap", lambda s: (s != "").sum()),
    bizjets_using_irish_airport=("bizjet", "sum"),
    foreign_military_state_aircraft=("foreign_state", "sum"))
t["note"] = [INCOMPLETE.get(i, "") for i in t.index]
t.to_csv(os.path.join(DATA, "daily-summary.csv"))

keep = d[d.foreign_state | d.bizjet]
keep[["date", "hex", "reg", "type", "desc", "ownOp", "callsigns", "ie_ap", "first_in_box_utc",
      "last_in_box_utc", "mil", "biz"]].to_csv(os.path.join(DATA, "aircraft.csv"), index=False)
open(os.path.join(DATA, "hexes.txt"), "w").write("\n".join(sorted(set(keep.hex.str.lower()))))
print(t.to_string())
