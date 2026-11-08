"""Draw the charts, map and table on the DLR cycle counters page.

Reads the hourly counts in analysis/cycling/data/raw/ (see dlr_counts.py) and
writes:
  figures/cycling_dlr_counter_map.html      map of counters, sized by use
  figures/cycling_dlr_counter_ranking.html  average cyclists a day, last 12 months
  figures/cycling_dlr_counter_trends.html   monthly averages, one counter at a time
  cycling/_dlr-counter-stats.md             data date and the summary table
  analysis/cycling/data/dlr_counter_*.csv   the numbers behind them

Usage (from the repo root):
    pip install plotly pandas
    python3 analysis/cycling/make_counter_page.py
    python3 -I tools/slim_plotly.py figures/cycling_*.html
"""
import os
import sys

import pandas as pd
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dlr_counts import COUNTERS, ROOT, clean_daily, load_hourly  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "analysis", "charts"))
from make_charts import BLUE, GRID, INK, INK_2, INK_3, axis, base_layout, save, title  # noqa: E402

OUT = os.path.join(ROOT, "analysis", "cycling", "data")
STATS = os.path.join(ROOT, "cycling", "_dlr-counter-stats.md")
MIN_DAYS = 180   # good days needed in a 12-month window to report an average
MIN_MONTH = 10   # good days needed to plot a month

# Counters whose readings look wrong, shown under the table. Review when the
# data is refreshed.
NOTES = {
    "glenageary": "Readings at The Metals jump between about 100 and 900 a day from one "
                  "month to the next since late 2024, which looks like a counter fault. "
                  "Treat its numbers with caution.",
}


def summarise(day):
    end = day.index.max()
    last = day[end - pd.Timedelta(days=364):end]
    prev = day[end - pd.Timedelta(days=729):end - pd.Timedelta(days=365)]
    rows = []
    for key, (label, area, site, lat, lon, kind) in COUNTERS.items():
        s = day[key].dropna()
        if s.empty:
            continue
        a, b = last[key].dropna(), prev[key].dropna()
        avg = a.mean() if len(a) >= MIN_DAYS else None
        before = b.mean() if len(b) >= MIN_DAYS else None
        rows.append(dict(key=key, counter=label, area=area, site=site, lat=lat, lon=lon, counts=kind,
                         first_day=s.index.min().date(), last_day=s.index.max().date(),
                         avg_last_12m=round(avg) if avg is not None else None,
                         avg_prev_12m=round(before) if before is not None else None,
                         good_days_last_12m=len(a)))
    df = pd.DataFrame(rows)
    df["change_pct"] = ((df["avg_last_12m"] / df["avg_prev_12m"] - 1) * 100).round()
    df.to_csv(os.path.join(OUT, "dlr_counter_summary.csv"), index=False)
    return df, end


def ranking(df, end):
    d = df.dropna(subset=["avg_last_12m"]).sort_values("avg_last_12m", ascending=False)
    fig = go.Figure(go.Bar(
        x=d["avg_last_12m"], y=d["counter"], orientation="h",
        marker=dict(color=BLUE, line=dict(width=0)),
        text=[f"{v:,.0f}" for v in d["avg_last_12m"]], textposition="outside",
        textfont=dict(color=INK, size=12), cliponaxis=False,
        customdata=d[["area", "counts"]],
        hovertemplate="%{y}, %{customdata[0]}<br><b>%{x:,.0f}</b> cyclists a day<br>%{customdata[1]}<extra></extra>",
    ))
    fig.update_layout(**base_layout(
        title=title("Cyclists a day at each DLR counter",
                    f"Average per day, 12 months to {end:%-d %B %Y}"),
        xaxis=axis(showticklabels=False, range=[0, d["avg_last_12m"].max() * 1.15]),
        yaxis=axis(autorange="reversed", tickfont=dict(color=INK_2, size=12)),
        margin=dict(l=20, r=40, t=80, b=20), bargap=0.3,
    ))
    fig.update_yaxes(automargin=True)
    save(fig, "cycling_dlr_counter_ranking.html")


LABEL_POS = {"N11": "top left", "Clonskeagh": "bottom center", "Rock Road": "top right",
             "Wyattville Road": "bottom right"}


def counter_map(df, end):
    sites = (df.dropna(subset=["avg_last_12m"]).groupby("site")
             .agg(lat=("lat", "mean"), lon=("lon", "mean"), total=("avg_last_12m", "sum"),
                  detail=("counter", lambda s: s.tolist()), values=("avg_last_12m", list)).reset_index())
    sites["hover"] = [
        f"<b>{r.site}</b><br>" + "<br>".join(f"{c}: {v:,.0f} a day" for c, v in zip(r.detail, r.values))
        for r in sites.itertuples()]
    fig = go.Figure(go.Scattermap(
        lat=sites["lat"], lon=sites["lon"], mode="markers",
        marker=dict(size=(sites["total"] ** 0.5) * 0.9 + 8, color=BLUE, opacity=0.8),
        hovertext=sites["hover"], hoverinfo="text",
    ))
    # Labels go in their own traces: a map trace takes one text position.
    for r in sites.itertuples():
        fig.add_trace(go.Scattermap(
            lat=[r.lat], lon=[r.lon], mode="markers+text", text=[r.site], hoverinfo="skip",
            marker=dict(size=1, opacity=0),
            textposition=LABEL_POS.get(r.site, "top right"), textfont=dict(size=12, color=INK),
        ))
    fig.update_layout(**base_layout(
        title=title("Where DLR counts cyclists",
                    f"Circle size: average cyclists a day, 12 months to {end:%-d %B %Y}"),
        map=dict(style="carto-positron", center=dict(lat=53.282, lon=-6.18), zoom=11.2),
        margin=dict(l=0, r=0, t=80, b=0),
    ))
    save(fig, "cycling_dlr_counter_map.html")


def trends(day):
    m = day.resample("MS").mean().where(day.resample("MS").count() >= MIN_MONTH).round()
    m = m[[k for k in COUNTERS if m[k].notna().any()]]
    m.rename(columns={k: COUNTERS[k][0] for k in m.columns}).to_csv(
        os.path.join(OUT, "dlr_counter_monthly.csv"), index_label="month")
    order = m.iloc[-12:].mean().sort_values(ascending=False).index.tolist()
    fig = go.Figure()
    for i, key in enumerate(order):
        label = COUNTERS[key][0]
        fig.add_trace(go.Scatter(
            x=m.index, y=m[key], name=label, visible=(i == 0), mode="lines",
            line=dict(color=BLUE, width=2), connectgaps=False,
            hovertemplate=f"{label}<br>%{{x|%B %Y}}: <b>%{{y:,.0f}}</b> a day<extra></extra>",
        ))
    buttons = [dict(label=COUNTERS[k][0], method="update",
                    args=[{"visible": [j == i for j in range(len(order))]}])
               for i, k in enumerate(order)]
    fig.update_layout(**base_layout(
        title=title("Cyclists a day, by month", "Average per day. Pick a counter. Gaps are counter faults."),
        xaxis=axis(), yaxis=axis(showgrid=True, gridcolor=GRID, rangemode="tozero", tickformat=","),
        updatemenus=[dict(buttons=buttons, direction="down", x=0, xanchor="left", y=1.02, yanchor="bottom",
                          bgcolor="white", bordercolor=GRID, font=dict(color=INK, size=13), showactive=True)],
        margin=dict(l=60, r=30, t=130, b=40),
    ))
    save(fig, "cycling_dlr_counter_trends.html")


def stats_md(df, end):
    def fmt(v):
        return "–" if pd.isna(v) else f"{v:,.0f}"

    def change(v):
        return "–" if pd.isna(v) else ("0%" if v == 0 else f"{v:+.0f}%")

    d = df.sort_values("avg_last_12m", ascending=False, na_position="last")
    lines = [
        f"Data to **{end:%-d %B %Y}**, from {len(d)} counters. "
        f"Counting started in {d['first_day'].min():%Y}.",
        "",
        "| Counter | Area | Counts | Cyclists a day, last 12 months | Previous 12 months | Change |",
        "|---|---|---|--:|--:|--:|",
    ]
    for r in d.itertuples():
        mark = "\\*" if r.key in NOTES else ""
        lines.append(f"| {r.counter}{mark} | {r.area} | {r.counts} | {fmt(r.avg_last_12m)} | "
                     f"{fmt(r.avg_prev_12m)} | {change(r.change_pct)} |")
    lines += ["", ": Average cyclists a day at each DLR counter. A dash means the counter "
              f"had fewer than {MIN_DAYS} working days in that period. {{.striped .hover}}", ""]
    for key, note in NOTES.items():
        lines += [f"\\* {note}", ""]
    with open(STATS, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote", STATS)


def main():
    day = clean_daily(load_hourly())
    df, end = summarise(day)
    ranking(df, end)
    counter_map(df, end)
    trends(day)
    stats_md(df, end)
    print(df[["counter", "avg_last_12m", "avg_prev_12m", "change_pct", "good_days_last_12m"]].to_string(index=False))


if __name__ == "__main__":
    main()
