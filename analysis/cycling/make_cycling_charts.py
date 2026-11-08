"""Draw the cycle counter charts on the Blackrock DART laneway page.

Inputs are DLR's hourly bicycle counts from Smart Dublin, saved in
analysis/cycling/data/raw/ by tools/fetch_cycle_counts.py, and the council's
own pedestrian and cyclist survey of the laneway route (Part 8 report,
Table 4-3, 8 to 10 November 2022, 07:00 to 19:00).

Counters used (names as DLR publishes them):
  Rock Road Totem Inbound / Rock Road Totem (2 way cycle track)  -> cycle track
  Rock Road Bus Lane                                             -> bus lane
  Rock Road Park / Rock Road Park - Ped's & Cyclists Cyclist     -> park path
  Dun Laoghaire @ Seapoint Beach Cyclist                         -> Seapoint

Counter faults show up as days of zero or near zero. A day is dropped when it
has fewer than 22 hours of data, a total of zero, or a total under a quarter of
that counter's median over the surrounding four weeks. A month needs 10 good
days to be plotted.

Usage (from the repo root):
    pip install plotly pandas
    python3 analysis/cycling/make_cycling_charts.py
    python3 -I tools/slim_plotly.py figures/cycling_*.html
"""
import glob
import os
import sys

import pandas as pd
import plotly.graph_objects as go

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "analysis", "cycling", "data", "raw")
OUT = os.path.join(ROOT, "analysis", "cycling", "data")
FIGURES = os.path.join(ROOT, "figures")
sys.path.insert(0, os.path.join(ROOT, "analysis", "charts"))
from make_charts import (AQUA, BLUE, CONTEXT, GRID, INK, INK_2, INK_3, ORANGE,  # noqa: E402
                         axis, base_layout, save, title)

NAMES = {
    "rock road totem inbound": "Cycle track",
    "rock road totem (2 way cycle track) cyclist": "Cycle track",
    "rock road bus lane": "Bus lane",
    "rock road park": "Park path",
    "rock road park - ped's & cyclists cyclist": "Park path",
}

# Council survey of the laneway route, Part 8 report Table 4-3: average
# cyclists per day, both directions, 07:00 to 19:00, 8 to 10 November 2022.
SURVEY = {"Location 1": 406, "Location 2": 476, "Location 3": 68}
SURVEY_DAYS = ("2022-11-08", "2022-11-10")


def column(name):
    n = name.lower().strip()
    if n.endswith("seapoint beach cyclist"):
        return "Seapoint"
    return NAMES.get(n)


def load_hourly():
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW, "bicycle-traffic-counts-dlr__*.csv"))):
        d = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
        t = d.columns[0]
        dayfirst = d[t].astype(str).str.match(r"\d\d/\d\d/\d{4}").all()
        fmt = "%d/%m/%Y %H:%M" if dayfirst else "%b %d, %Y %I:%M %p"
        keep = {c: column(c) for c in d.columns if column(c)}
        x = d[list(keep)].rename(columns=keep).apply(pd.to_numeric, errors="coerce")
        x.index = pd.to_datetime(d[t], format=fmt, errors="coerce")
        x = x[x.index.notna()]
        frames.append(x.groupby(level=0).sum(min_count=1))
    h = pd.concat(frames).sort_index()
    return h.groupby(level=0).first()


def clean_daily(h):
    day = h.resample("D").sum(min_count=22)
    ref = day.rolling(28, center=True, min_periods=7).median()
    return day.where((day > 0) & (day >= 0.25 * ref))


def survey_comparison(h):
    a, b = SURVEY_DAYS
    w = h.loc[a:f"{b} 23:00"]
    w = w[(w.index.hour >= 7) & (w.index.hour < 19)]
    per_day = w.groupby(w.index.date).sum(min_count=12).mean().round()
    rows = [
        ("Rock Road cycle track", per_day["Cycle track"], BLUE),
        ("Rock Road bus lane", per_day["Bus lane"], BLUE),
        ("Rock Road park path", per_day["Park path"], BLUE),
        ("Seapoint coastal route", per_day["Seapoint"], BLUE),
        ("Laneway, survey point 2", SURVEY["Location 2"], ORANGE),
        ("Laneway, survey point 1", SURVEY["Location 1"], ORANGE),
    ]
    df = pd.DataFrame(rows, columns=["place", "cyclists", "colour"])
    df[["place", "cyclists"]].to_csv(os.path.join(OUT, "survey_days_comparison.csv"), index=False)
    fig = go.Figure(go.Bar(
        x=df["cyclists"], y=df["place"], orientation="h",
        marker=dict(color=df["colour"], line=dict(width=0)),
        text=[f"{v:,.0f}" for v in df["cyclists"]], textposition="outside",
        textfont=dict(color=INK, size=13), cliponaxis=False,
        hovertemplate="%{y}<br><b>%{x:,.0f}</b> cyclists a day, 7am to 7pm<extra></extra>",
    ))
    fig.update_layout(**base_layout(
        title=title("Cyclists a day near Blackrock",
                    "8 to 10 Nov 2022, weekdays, 7am to 7pm"),
        xaxis=axis(showticklabels=False, range=[0, df["cyclists"].max() * 1.15]),
        yaxis=axis(autorange="reversed", tickfont=dict(color=INK_2, size=13)),
        margin=dict(l=20, r=40, t=80, b=20), bargap=0.35,
    ))
    fig.update_yaxes(automargin=True)
    save(fig, "cycling_blackrock_survey_days.html")
    return df


def monthly_trend(day):
    road = day[["Cycle track", "Bus lane"]].sum(axis=1, min_count=2)
    series = pd.DataFrame({
        "Rock Road, cycle track and bus lane": road,
        "Rock Road park path": day["Park path"],
        "Seapoint, Coastal Mobility Route": day["Seapoint"],
    })["2019":]
    good = series.resample("MS").count()
    m = series.resample("MS").mean().where(good >= 10).round()
    m.to_csv(os.path.join(OUT, "monthly_average_daily_cyclists.csv"), index_label="month")
    colours = [BLUE, AQUA, ORANGE]
    fig = go.Figure()
    for (name, s), c in zip(m.items(), colours):
        fig.add_trace(go.Scatter(
            x=s.index, y=s, name=name, mode="lines", connectgaps=False,
            line=dict(color=c, width=2),
            hovertemplate=f"{name}<br>%{{x|%B %Y}}: <b>%{{y:,.0f}}</b> a day<extra></extra>",
        ))
        last = s.dropna()
        fig.add_annotation(x=last.index[-1], y=last.iloc[-1], text={"Rock Road park path": "Park path"}.get(name, name.split(",")[0]),
                           xanchor="left", xshift=6, showarrow=False, font=dict(color=INK_2, size=12))
    fig.update_layout(**base_layout(
        title=title("Cyclists a day, by month",
                    "Rock Road and Seapoint. Gaps are counter faults."),
        xaxis=axis(range=[m.index.min(), m.index.max() + pd.Timedelta(days=20)]), yaxis=axis(showgrid=True, gridcolor=GRID, rangemode="tozero", tickformat=","),
        showlegend=True, legend=dict(orientation="h", y=-0.12, x=0, font=dict(color=INK_2, size=12)),
        hovermode="x unified", margin=dict(l=60, r=90, t=80, b=70),
    ))
    save(fig, "cycling_blackrock_trend.html")
    return m


def main():
    h = load_hourly()
    day = clean_daily(h)
    print(survey_comparison(h)[["place", "cyclists"]].to_string(index=False))
    m = monthly_trend(day)
    print(m.tail(14).to_string())
    print(m.groupby(m.index.year).mean().round().to_string())


if __name__ == "__main__":
    main()
