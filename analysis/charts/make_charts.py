"""Draw the census, marriage and survey charts in the Fianaise house style.

Restyles the charts first made in analysis/education_equality (plot_CSO.py,
plot_survey_summary.py). The numbers come from the same CSO files in
analysis/education_equality/data and the same survey counts in
staff_board_data.py; only the presentation changes.

Usage (from the repo root):
    pip install plotly pandas
    python3 analysis/charts/make_charts.py
    python3 -I tools/slim_plotly.py figures/*.html
"""
import os
import sys

import pandas as pd
import plotly.graph_objects as go

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "analysis", "education_equality", "data")
FIGURES = os.path.join(ROOT, "figures")
sys.path.insert(0, os.path.join(ROOT, "analysis", "education_equality"))
import staff_board_data as report  # noqa: E402
from staff_board_data import INTEND_TO_ENROL_MULTIDENOM  # noqa: E402

# House style. Categorical slots in fixed order, an ordinal blue ramp for
# census years, recessive greys for context and chrome.
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#8a8984"
GRID = "#e8e7e3"
SURFACE = "#ffffff"
CONTEXT = "#c9c7c0"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
YEAR_RAMP = {"2011": "#86b6ef", "2016": "#2a78d6", "2022": "#104281"}
MULTI_D, DENOM = "#2f855a", "#a3aab3"   # the survey pages' green / grey

CONFIG = {"displayModeBar": False, "responsive": True}


def base_layout(**kw):
    layout = dict(
        font=dict(family=FONT, size=14, color=INK_2),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT, size=13, color=INK)),
        margin=dict(l=60, r=30, t=70, b=50),
        showlegend=False,
    )
    layout.update(kw)
    return layout


def title(text, sub):
    return dict(
        text=f"<b>{text}</b><br><span style='font-size:13px;color:{INK_2}'>{sub}</span>",
        x=0.02, xref="container", xanchor="left", y=0.97, yanchor="top",
        font=dict(size=18, color=INK),
    )


def axis(**kw):
    a = dict(showgrid=False, zeroline=False, linecolor=GRID, ticks="", tickfont=dict(color=INK_3, size=12))
    a.update(kw)
    return a


def save(fig, name):
    path = os.path.join(FIGURES, name)
    fig.write_html(path, config=CONFIG, include_plotlyjs=True, full_html=True,
                   default_width="100%", default_height="100%")
    print("wrote", path)


def marriages():
    df = pd.read_csv(os.path.join(DATA, "ireland_marriage_data_agg.csv"))
    df = df[["Year", "Form of Ceremony", "Percentage"]]
    highlight = {
        "Roman Catholic": ("Roman Catholic", BLUE),
        "Civil marriages": ("Civil", ORANGE),
        "The Humanist Association": ("Humanist", AQUA),
    }
    fig = go.Figure()
    # Context lines first, so the highlighted three sit on top.
    for ceremony, g in df.groupby("Form of Ceremony"):
        if ceremony in highlight:
            continue
        g = g.sort_values("Year")
        fig.add_trace(go.Scatter(
            x=g["Year"], y=g["Percentage"], mode="lines", name=ceremony,
            line=dict(color=CONTEXT, width=1.5),
            hovertemplate=f"{ceremony}: %{{y:.1f}}%<extra></extra>",
        ))
    for ceremony, (label, colour) in highlight.items():
        g = df[df["Form of Ceremony"] == ceremony].sort_values("Year")
        g = g[g["Percentage"].notna()]
        fig.add_trace(go.Scatter(
            x=g["Year"], y=g["Percentage"], mode="lines", name=label,
            line=dict(color=colour, width=2.5),
            hovertemplate=f"<b>{label}</b>: %{{y:.1f}}%<extra></extra>",
        ))
        last = g.iloc[-1]
        fig.add_trace(go.Scatter(
            x=[last["Year"]], y=[last["Percentage"]], mode="markers",
            marker=dict(color=colour, size=9, line=dict(color=SURFACE, width=2)),
            hoverinfo="skip",
        ))
        fig.add_annotation(
            x=last["Year"], y=last["Percentage"], xanchor="left", xshift=10,
            text=f"<b>{label}</b> {last['Percentage']:.0f}%", showarrow=False,
            font=dict(color=INK, size=13),
            yshift={"Roman Catholic": 9, "Civil marriages": -9}.get(ceremony, 0),
        )
    other = df[df["Form of Ceremony"] == "Other religious denominations"].sort_values("Year").iloc[-1]
    fig.add_annotation(x=other["Year"], y=other["Percentage"], xanchor="left", xshift=10, showarrow=False,
                       text=f"Other religious {other['Percentage']:.0f}%", font=dict(color=INK_3, size=12))
    first = df[(df["Form of Ceremony"] == "Roman Catholic") & (df["Year"] == df["Year"].min())].iloc[0]
    fig.add_annotation(x=first["Year"], y=first["Percentage"], yshift=14, xanchor="left",
                       text=f"{first['Percentage']:.0f}% in {first['Year']}", showarrow=False,
                       font=dict(color=INK_2, size=12))
    fig.add_annotation(x=1, xref="paper", y=-0.13, yref="paper", xanchor="right", showarrow=False,
                       text="Grey: Church of Ireland, Presbyterian, Spiritualist Union and other religious denominations",
                       font=dict(color=INK_3, size=11))
    fig.update_layout(base_layout(
        title=title("Civil ceremonies have caught up with Catholic weddings",
                    "Share of opposite-sex marriages by form of ceremony, 2000 to 2024"),
        hovermode="x unified",
        margin=dict(l=50, r=150, t=80, b=70),
        xaxis=axis(range=[1999.6, 2024.4], tick0=2000, dtick=4, showline=True, showspikes=True, spikecolor=INK_3, spikethickness=1, spikedash="solid"),
        yaxis=axis(range=[0, 85], dtick=20, showgrid=True, gridcolor=GRID, ticksuffix="%"),
    ))
    save(fig, "marriage_stats.html")


AGE_ORDER = ["0 - 4", "5 - 9", "10 - 14", "15 - 19", "20 - 24", "25 - 29", "30 - 34", "35 - 39",
             "40 - 44", "45 - 49", "50 - 54", "55 - 59", "60 - 64", "65 - 69", "70 - 74",
             "75 - 79", "80 - 84", "85+"]


def census(religion, out, headline, sub, xmax):
    df = pd.read_csv(os.path.join(DATA, "ireland_religion_census_data_ages.csv"))
    df = df[df["Religion"] == religion].copy()
    df["age"] = (df["Age Group"].str.replace(" years and over", "+", regex=False)
                 .str.replace(" years", "", regex=False))
    df["Census Year"] = df["Census Year"].astype(str)
    wide = df.pivot_table(index="age", columns="Census Year", values="Percentage").reindex(AGE_ORDER)
    labels = [a.replace(" - ", "–") for a in AGE_ORDER]

    fig = go.Figure()
    # One grey hairline per age group from its lowest to highest census value.
    for label, (_, row) in zip(labels, wide.iterrows()):
        fig.add_trace(go.Scatter(
            x=[row.min(), row.max()], y=[label, label], mode="lines",
            line=dict(color=CONTEXT, width=2), hoverinfo="skip", showlegend=False,
        ))
    for year, colour in YEAR_RAMP.items():
        fig.add_trace(go.Scatter(
            x=wide[year], y=labels, mode="markers", name=year,
            marker=dict(color=colour, size=11, line=dict(color=SURFACE, width=1.5)),
            hovertemplate=f"<b>%{{y}}</b> · {year}: %{{x:.1f}}%<extra></extra>",
        ))
    fig.update_layout(base_layout(
        title=title(headline, f"{sub}. {religion} as a share of each age group, census 2011, 2016 and 2022"),
        showlegend=True,
        legend=dict(orientation="h", x=0, xanchor="left", y=1.01, yanchor="bottom",
                    font=dict(color=INK, size=13), itemclick=False, itemdoubleclick=False),
        margin=dict(l=70, r=30, t=105, b=50),
        height=640,
        xaxis=axis(range=[0, xmax], showgrid=True, gridcolor=GRID, ticksuffix="%"),
        yaxis=axis(autorange="reversed", tickfont=dict(color=INK_2, size=12),
                   title=dict(text="Age", font=dict(color=INK_3, size=12))),
    ))
    save(fig, out)


def survey_intend_vs_preference():
    d = INTEND_TO_ENROL_MULTIDENOM
    base = d["not_yet_in_school_base"]
    rows = [
        ("Intend a <b>denominational</b> school", d["intend_denom_school"], d["intend_denom_want_change_to_multi"]),
        ("Intend a <b>multi-denominational</b> school", d["intend_multidenom_school"], d["intend_multidenom_want_multi"]),
    ]
    ylab = [f"{name}<br><span style='color:{INK_3}'>{n:,} households · {n / base * 100:.1f}%</span>"
            for name, n, _ in rows]
    multi = [m / n * 100 for _, n, m in rows]
    denom = [100 - p for p in multi]
    multi_n = [m for _, _, m in rows]
    denom_n = [n - m for _, n, m in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=ylab, x=multi, orientation="h", name="Prefer multi-denominational",
        marker=dict(color=MULTI_D, line=dict(color=SURFACE, width=2)),
        text=[f"<b>{p:.0f}%</b>  {n:,}" for p, n in zip(multi, multi_n)],
        textposition="inside", insidetextanchor="start", textfont=dict(color="white", size=14),
        customdata=multi_n,
        hovertemplate="Prefer multi-denominational<br><b>%{x:.1f}%</b> · %{customdata:,} households<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=ylab, x=denom, orientation="h", name="Prefer denominational",
        marker=dict(color=DENOM, line=dict(color=SURFACE, width=2)),
        text=[f"<b>{p:.0f}%</b>  {n:,}" for p, n in zip(denom, denom_n)],
        textposition="inside", insidetextanchor="end", textfont=dict(color=INK, size=14),
        customdata=denom_n,
        hovertemplate="Prefer denominational<br><b>%{x:.1f}%</b> · %{customdata:,} households<extra></extra>",
    ))
    fig.update_layout(base_layout(
        title=title("4 in 10 parents heading for a denominational school<br>would prefer a multi-denominational one",
                    f"Households with a child not yet in school (n = {base:,}), by intended school and preferred ethos"),
        barmode="stack",
        bargap=0.45,
        showlegend=True,
        legend=dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom",
                    font=dict(color=INK, size=13), traceorder="normal", itemclick=False, itemdoubleclick=False),
        margin=dict(l=20, r=20, t=140, b=30),
        height=400,
        xaxis=axis(range=[0, 100], showticklabels=False),
        yaxis=axis(autorange="reversed", tickfont=dict(color=INK, size=13), ticklabelstandoff=10, automargin=True),
    ))
    save(fig, "vis2_intend_vs_preference.html")


def survey_numbers():
    """Eligible, received and valid responses, parents beside staff and boards."""
    from plotly.subplots import make_subplots
    groups = [
        ("Parents and guardians", report.PARENT_ELIGIBLE, report.PARENT_SUBMITTED_RESPONSES,
         report.PARENT_VALID_RESPONSES),
        ("Staff and boards of management", report.STAFF_BOARD_TARGET_POPULATION,
         report.STAFF_BOARD_SUBMITTED_RESPONSES, report.STAFF_BOARD_VALID_RESPONSES),
    ]
    # Stacked rather than side by side, so it still reads on a phone.
    fig = make_subplots(rows=2, cols=1, subplot_titles=[f"<b>{g[0]}</b>" for g in groups],
                        vertical_spacing=0.16)
    colours = [CONTEXT, "#8f9aa0", ORANGE]
    for i, (name, eligible, received, valid) in enumerate(groups, start=1):
        labels = ["Eligible",
                  f"Responses received<br><span style='color:{INK_3};font-size:12px'>{received / eligible * 100:.1f}% of eligible</span>",
                  f"Valid responses<br><span style='color:{INK_3};font-size:12px'>{valid / eligible * 100:.1f}% of eligible</span>"]
        values = [eligible, received, valid]
        fig.add_trace(go.Bar(
            y=labels, x=values, orientation="h", marker=dict(color=colours),
            text=[f"{v:,}" for v in values], textposition="outside", cliponaxis=False,
            textfont=dict(color=INK, size=15),
            hovertemplate=f"{name}<br>%{{y}}: <b>%{{x:,}}</b><extra></extra>",
        ), row=i, col=1)
        fig.update_xaxes(axis(range=[0, eligible * 1.3], showticklabels=False), row=i, col=1)
        fig.update_yaxes(axis(autorange="reversed", tickfont=dict(color=INK_2, size=13)), row=i, col=1)
    fig.update_layout(base_layout(
        bargap=0.3, margin=dict(l=10, r=20, t=40, b=10), height=470,
    ))
    for a in fig.layout.annotations:
        a.font = dict(color=INK, size=14, family=FONT)
        a.x, a.xanchor = 0, "left"
    save(fig, "survey_numbers.html")


def parents_vs_staff_by_county():
    """Slide 8: parents (two groups) against staff and boards, county by county."""
    parent = report.TABLE_3_PARENT_MULTIDENOM_BY_COUNTY.set_index("County")
    staff = report.TABLE_8_STAFF_BOARD_BY_COUNTY.set_index("County")["MultiDenom_pref_pct"]
    df = parent.join(staff).sort_values("MultiDenom_pref_pct", ascending=False)
    counties = list(df.index)
    top = df[["Children_in_school_pct", "Not_yet_in_school_pct"]].max(axis=1)
    LIGHT_ORANGE, STAFF = "#f4a582", "#22343c"

    fig = go.Figure()
    # Grey area up to staff and boards, a peach band from there to the higher parent group.
    fig.add_trace(go.Scatter(x=counties, y=df["MultiDenom_pref_pct"], mode="lines", line=dict(width=0),
                             fill="tozeroy", fillcolor="rgba(34,52,60,0.08)", hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=counties, y=top, mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor="rgba(235,104,52,0.15)", hoverinfo="skip", showlegend=False))
    for c in counties:
        r = df.loc[c]
        fig.add_trace(go.Scatter(x=[c, c], y=[r["MultiDenom_pref_pct"], max(r["Children_in_school_pct"], r["Not_yet_in_school_pct"])],
                                 mode="lines", line=dict(color=INK_3, width=1, dash="dot"), hoverinfo="skip", showlegend=False))
    series = [
        ("Parents, child not yet in school", "Not_yet_in_school_pct", ORANGE),
        ("Parents, child in school", "Children_in_school_pct", LIGHT_ORANGE),
        ("School staff and boards", "MultiDenom_pref_pct", STAFF),
    ]
    for name, col, colour in series:
        fig.add_trace(go.Scatter(
            x=counties, y=df[col], mode="markers", name=name, showlegend=True,
            marker=dict(color=colour, size=11, line=dict(color=SURFACE, width=1.5)),
            hovertemplate=f"<b>%{{x}}</b><br>{name}: %{{y:.1f}}%<extra></extra>",
        ))
    staff_nat = float(report.TABLE_7_STAFF_BOARD_NATIONAL.set_index("preference").loc["MULTI-DENOMINATIONAL", "percentage"])
    parent_nat = float(report.TABLE_2A_NATIONAL_PROPORTIONS.set_index("household_type").loc["ALL", "multidenom_pct"])
    fig.update_layout(base_layout(
        title=title("Parents want multi-denominational schools more than staff and boards do",
                    f"Share preferring a multi-denominational school, by county. Nationally: parents {parent_nat:.0f}%, staff and boards {staff_nat:.1f}%"),
        showlegend=True, hovermode="closest",
        legend=dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom",
                    font=dict(color=INK, size=13), itemclick=False, itemdoubleclick=False),
        margin=dict(l=60, r=20, t=120, b=90), height=560,
        xaxis=axis(tickangle=-45, tickfont=dict(color=INK_2, size=12)),
        yaxis=axis(range=[0, 65], dtick=10, showgrid=True, gridcolor=GRID, ticksuffix="%",
                   title=dict(text="Prefer a multi-denominational school", font=dict(color=INK_3, size=12))),
    ))
    save(fig, "parents_vs_staff_by_county.html")


if __name__ == "__main__":
    marriages()
    census("Roman Catholic", "catholic_religion_stats.html",
           "Catholic affiliation fell in every age group", "Steepest among 25- to 34-year-olds", 100)
    census("No religion", "no_religion_stats.html",
           "No religion rose in every age group", "Most among people in their twenties and thirties", 40)
    survey_intend_vs_preference()
    survey_numbers()
    parents_vs_staff_by_county()
