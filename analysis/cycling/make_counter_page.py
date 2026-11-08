"""Draw the charts, map and table on the DLR cycle counters page.

Reads the hourly counts in analysis/cycling/data/raw/ (see dlr_counts.py) and
writes:
  figures/cycling_dlr_counter_map.html      map of counters, sized by use
  figures/cycling_dlr_counter_ranking.html  average cyclists a day, last 12 months
  figures/cycling_dlr_counter_trends.html   monthly averages, one counter at a time
  figures/cycling_dlr_counter_seasons.html  average by month of the year
  figures/cycling_dlr_counter_weekdays.html average by day of the week
  cycling/_dlr-counter-patterns.md          sentences on the weekly and yearly patterns
  cycling/_dlr-counter-stats.md             data date and the summary table
  analysis/cycling/data/dlr_counter_*.csv   the numbers behind them

Usage (from the repo root):
    pip install plotly pandas
    python3 analysis/cycling/make_counter_page.py
    python3 -I tools/slim_plotly.py figures/cycling_*.html
"""
import html
import json
import os
import sys

import pandas as pd
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dlr_counts import COUNTERS, ROOT, clean_daily, load_hourly  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "analysis", "charts"))
from make_charts import BLUE, GRID, ORANGE, INK, INK_2, INK_3, axis, base_layout, save, title  # noqa: E402

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


def picker_script(order):
    """A native <select> that shows one trace at a time.

    Used rather than a Plotly dropdown, whose menu is clipped inside the
    page's iframe and hard to use on phones."""
    options = "".join(f'<option value="{i}">{html.escape(COUNTERS[k][0])}</option>'
                      for i, k in enumerate(order))
    return f"""
var gd = document.getElementById('{{plot_id}}');
var sel = document.createElement('select');
sel.setAttribute('aria-label', 'Pick a counter');
sel.innerHTML = {json.dumps(options)};
sel.style.cssText = 'position:absolute;left:60px;top:78px;z-index:10;font:14px Inter,system-ui,sans-serif;' +
  'color:{INK};background:#fff;border:1px solid #c9c8c3;border-radius:6px;padding:6px 8px;max-width:calc(100% - 90px);';
gd.parentNode.style.position = 'relative';
gd.parentNode.appendChild(sel);
sel.addEventListener('change', function () {{
  var n = gd.data.length, v = +sel.value, vis = [];
  for (var i = 0; i < n; i++) vis.push(i === v);
  Plotly.restyle(gd, {{visible: vis}});
}});
"""


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
    fig.update_layout(**base_layout(
        title=title("Cyclists a day, by month", "Average per day. Gaps are counter faults."),
        xaxis=axis(), yaxis=axis(showgrid=True, gridcolor=GRID, rangemode="tozero", tickformat=","),
        margin=dict(l=60, r=30, t=130, b=40),
    ))
    save(fig, "cycling_dlr_counter_trends.html", post_script=picker_script(order))


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SEASON_YEARS = 3  # years of data averaged in the time-of-year chart


def busiest_first(table):
    """Counters with data in every column, busiest overall first."""
    table = table[[k for k in table.columns if table[k].notna().all()]]
    return table, table.mean().sort_values(ascending=False).index.tolist()


def bar_picker(table, labels, colours, name, chart_title, subtitle, hover):
    table, order = busiest_first(table)
    fig = go.Figure()
    for i, key in enumerate(order):
        label = COUNTERS[key][0]
        fig.add_trace(go.Bar(
            x=labels, y=table[key].values, name=label, visible=(i == 0), marker_color=colours,
            hovertemplate=f"{label}<br>{hover}: <b>%{{y:,.0f}}</b> a day<extra></extra>",
        ))
    fig.update_layout(**base_layout(
        title=title(chart_title, subtitle),
        xaxis=axis(type="category"), yaxis=axis(showgrid=True, gridcolor=GRID, rangemode="tozero", tickformat=","),
        margin=dict(l=60, r=30, t=130, b=40), bargap=0.25, showlegend=False,
    ))
    save(fig, name, post_script=picker_script(order))
    return table, order


def seasons(day):
    end = day.index.max()
    window = day[end - pd.DateOffset(years=SEASON_YEARS) + pd.Timedelta(days=1):end]
    good = window.groupby(window.index.month).count()
    table = window.groupby(window.index.month).mean().where(good >= MIN_MONTH * SEASON_YEARS // 2).round()
    table = table.reindex(range(1, 13))
    start = end - pd.DateOffset(years=SEASON_YEARS) + pd.Timedelta(days=1)
    table, order = bar_picker(
        table, MONTHS, BLUE, "cycling_dlr_counter_seasons.html", "Cyclists a day, by time of year",
        f"Average per day, {start:%b %Y} to {end:%b %Y}.", "%{x}")
    out = table[order].rename(columns={k: COUNTERS[k][0] for k in order})
    out.index = MONTHS
    out.to_csv(os.path.join(OUT, "dlr_counter_by_month_of_year.csv"), index_label="month")
    return out


def weekdays(day):
    end = day.index.max()
    last = day[end - pd.Timedelta(days=364):end]
    good = last.groupby(last.index.dayofweek).count()
    table = last.groupby(last.index.dayofweek).mean().where(good >= MIN_DAYS // 7).round()
    table = table.reindex(range(7))
    colours = [BLUE] * 5 + [ORANGE] * 2
    table, order = bar_picker(
        table, DAYS, colours, "cycling_dlr_counter_weekdays.html", "Cyclists a day, by day of the week",
        f"Average per day, 12 months to {end:%-d %B %Y}. Weekends in orange.", "%{x}")
    out = table[order].rename(columns={k: COUNTERS[k][0] for k in order})
    out.index = DAYS
    out.to_csv(os.path.join(OUT, "dlr_counter_by_day_of_week.csv"), index_label="day")
    return out


def patterns_md(season, week):
    """A few sentences on the patterns, regenerated with the data."""
    keep = [c for c in week.columns if c not in {COUNTERS[k][0] for k in NOTES}]
    week, season = week[keep], season[[c for c in season.columns if c not in {COUNTERS[k][0] for k in NOTES}]]
    full = dict(zip(DAYS, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]))
    wk = week.loc[DAYS[:5]] / week.loc[DAYS[:5]].mean()
    typical = wk.median(axis=1)
    order = typical.sort_values(ascending=False).index

    def vs(d):
        p = round((typical[d] - 1) * 100)
        return "about average" if p == 0 else (f"{p}% above" if p > 0 else f"{-p}% below")

    weekend = week.loc[["Sat", "Sun"]].mean() / week.loc[DAYS[:5]].mean() - 1
    busier = weekend[weekend > 0].sort_values(ascending=False)
    quieter = weekend.sort_values().head(2)
    peak = season.idxmax()
    low = season.idxmin()
    winter = int(low.isin(["Dec", "Jan"]).sum())
    ratio = (season.max() / season.min()).median()
    n = week.shape[1]

    def names_month(peaks, months):
        hit = peaks[peaks.isin(months)]
        return ", ".join(f"{c} ({m})" for c, m in hit.items()) or "none this year"

    def names(series):
        return " and ".join(f"{c} ({v:+.0%})" for c, v in series.items())

    lines = [
        f"**Days of the week.** On a typical counter the busiest weekdays are {full[order[0]]} and "
        f"{full[order[1]]}. Compared with the weekday average, Tuesday is {vs('Tue')}, Thursday is "
        f"{vs('Thu')} and Friday is {vs('Fri')}.",
        "",
        f"Weekends are quieter at most counters, most of all on commuter routes: {names(quieter)} "
        f"compared with weekdays. "
        + (f"The exception{'s are' if len(busier) > 1 else ' is'} {names(busier)}, "
           f"which {'are' if len(busier) > 1 else 'is'} busier at weekends." if len(busier) else ""),
        "",
        f"**Time of year.** {f'All {n} counters are' if winter == n else f'{winter} of the {n} counters are'} "
        f"quietest in December or January. Routes along the coast and through parks are busiest in July or "
        f"August: {names_month(peak, ['Jul', 'Aug'])}. The commuter routes peak in September, when college "
        f"and school are back: {names_month(peak, ['Sep'])}. "
        f"On a typical counter the busiest month has about {ratio:.1f} times as many cyclists a day "
        f"as the quietest.",
        "",
    ]
    with open(os.path.join(ROOT, "cycling", "_dlr-counter-patterns.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


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
    patterns_md(seasons(day), weekdays(day))
    stats_md(df, end)
    print(df[["counter", "avg_last_12m", "avg_prev_12m", "change_pct", "good_days_last_12m"]].to_string(index=False))


if __name__ == "__main__":
    main()
