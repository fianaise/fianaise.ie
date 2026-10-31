"""Draw the school ethos and Primary School Survey maps in the Fianaise house style.

Restyles the folium maps first made in analysis/education_equality
(plot_ethos_geospatial.py, plot_survey_geospatial.py, plot_survey_summary.py).
The school selection, categories and numbers follow those scripts exactly;
only the presentation changes. Maps draw on simplified county outlines
(data/ireland_counties.geojson, from make_geography.py) instead of map
tiles, so they need no tile service.

Inputs in analysis/charts/data/raw/:
  Data_on_Individual_Schools_Mainstream_*.xlsx   Department of Education school lists
                                                 (refreshed by tools/fetch_school_lists.py)
  Primary_School_Results_For_All_Primary_Schools.xlsx   2025-26 Primary School Survey

Usage (from the repo root):
    pip install plotly pandas openpyxl numpy folium
    python3 analysis/charts/make_maps.py
    python3 -I tools/slim_plotly.py figures/*.html
"""
import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RAW = os.path.join(HERE, "data", "raw")
FIGURES = os.path.join(ROOT, "figures")
sys.path.insert(0, os.path.join(ROOT, "analysis", "education_equality"))
sys.path.insert(0, HERE)
from make_charts import FONT, GRID, INK, INK_2, INK_3, SURFACE, CONFIG, base_layout, title, save  # noqa: E402

# Plotly geo fetches a world outline even when the base map is hidden; serve
# the copy in figures/lib/topojson (sane-topojson 4.0.0) instead of its CDN.
CONFIG["topojsonURL"] = "lib/topojson/"
import plot_survey_geospatial as survey  # noqa: E402

GEO = json.load(open(os.path.join(HERE, "data", "ireland_counties.geojson"), encoding="utf-8"))
COUNTIES = [f["id"] for f in GEO["features"] if f["id"] != "Northern Ireland"]
LAND = "#f3f2ee"
BORDER = "#c9c7c0"


def school_list_year(path):
    """'Data_on_Individual_Schools_Mainstream_2024_25.xlsx' -> '2024-25'."""
    m = re.search(r"(20\d\d)[-_ ]?(20)?(\d\d)", os.path.basename(path))
    return f"{m.group(1)}-{m.group(3)}" if m else "?"


def latest_school_list():
    """Newest school list; a final list beats a preliminary one for the same year."""
    files = glob.glob(os.path.join(RAW, "Data_on_Individual_Schools_Mainstream*.xlsx"))
    return max(files, key=lambda f: (school_list_year(f), "preliminary" not in f.lower()))


def read_school_list(path):
    """Read the mainstream sheet of a school list, whatever that year's layout.

    The sheet is "Mainstream Schools" in some years and "Mainstream" in others,
    the header row moves, and latitude/longitude change names.
    """
    xl = pd.ExcelFile(path)
    sheet = next(s for s in xl.sheet_names if s.strip().lower() in ("mainstream schools", "mainstream"))
    raw = pd.read_excel(xl, sheet_name=sheet, header=None, nrows=10)
    header = next(i for i, row in raw.iterrows() if row.astype(str).str.strip().eq("Roll Number").any())
    df = pd.read_excel(xl, sheet_name=sheet, header=header)
    df.columns = df.columns.astype(str).str.strip()
    return df.rename(columns={"Latitude": "School Latitude", "Longitude": "School Longitude"})


def base_geo(fig, row=None, col=None, lonaxis=(-10.7, -5.4), lataxis=(51.35, 55.45)):
    """County outlines as a quiet base layer, Northern Ireland a shade lighter."""
    kw = dict(row=row, col=col) if row else {}
    fig.add_trace(go.Choropleth(
        geojson=GEO, locations=[f["id"] for f in GEO["features"]],
        z=[0 if f["id"] == "Northern Ireland" else 1 for f in GEO["features"]],
        colorscale=[[0, "#fafaf8"], [1, LAND]], zmin=0, zmax=1, showscale=False,
        marker_line=dict(color=BORDER, width=0.6), hoverinfo="skip",
    ), **kw)
    fig.update_geos(
        visible=False, projection_type="mercator",
        lonaxis_range=list(lonaxis), lataxis_range=list(lataxis),
        bgcolor=SURFACE, **kw,
    )


def legend_top():
    return dict(orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom",
                font=dict(color=INK, size=13), itemsizing="constant",
                bgcolor="rgba(255,255,255,0)")


# ── School ethos ─────────────────────────────────────────────────────────────

ETHOS_GROUPS = [
    # (label, ethos values, colour, symbol). Hues in fixed slot order; the two
    # small groups add a symbol so they don't rely on colour alone.
    ("Catholic", ["Catholic"], "#2a78d6", "circle"),
    ("Church of Ireland", ["Church Of Ireland"], "#eb6834", "circle"),
    ("Multi-denominational", ["Multi Denominational"], "#1baf7a", "circle"),
    ("Inter-denominational", ["Inter Denominational"], "#1baf7a", "diamond"),
    ("Other faiths", ["Presbyterian", "Methodist", "Quaker", "Jewish", "Muslim"], "#52514e", "square"),
]


def ethos_map():
    path = latest_school_list()
    year = school_list_year(path)
    df = read_school_list(path)
    for c in ("School Latitude", "School Longitude"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["School Latitude", "School Longitude"])
    df = df.drop_duplicates(subset=["Official Name", "School Latitude", "School Longitude"])
    df["ethos"] = df["Ethos Description"].fillna("Unknown/Missing").astype(str).str.strip()
    total = len(df)
    catholic_share = (df["ethos"] == "Catholic").mean() * 100

    fig = go.Figure()
    base_geo(fig)
    shown = set()
    for label, values, colour, symbol in ETHOS_GROUPS:
        g = df[df["ethos"].isin(values)]
        shown.update(values)
        fig.add_trace(go.Scattergeo(
            lon=g["School Longitude"], lat=g["School Latitude"], mode="markers",
            name=f"{label} ({len(g):,})",
            marker=dict(color=colour, size=5 if label == "Catholic" else 8, symbol=symbol,
                        opacity=0.75 if label == "Catholic" else 0.95,
                        line=dict(color=SURFACE, width=0.6)),
            customdata=np.stack([g["Official Name"], g["County Description"], g["ethos"]], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<extra></extra>",
        ))
    missing = df[~df["ethos"].isin(shown)]
    assert missing.empty, f"ethos values with no group: {sorted(missing['ethos'].unique())}"
    fig.update_layout(base_layout(
        title=title(f"{catholic_share:.0f}% of primary schools have a Catholic ethos",
                    f"Mainstream primary schools by ethos, {year} ({total:,} schools).<br>Click the legend to show or hide a group"),
        showlegend=True, legend=legend_top(),
        margin=dict(l=10, r=10, t=132, b=10), height=740,
        geo=dict(bgcolor=SURFACE),
    ))
    save(fig, "ethos_current_config.html")


# ── Survey: current configuration vs preference ─────────────────────────────

def survey_school_map():
    results = os.path.join(RAW, "Primary_School_Results_For_All_Primary_Schools.xlsx")
    coords = os.path.join(RAW, "Data_on_Individual_Schools_Mainstream_2024_25.xlsx")
    df = survey._load_and_merge(results, coords)

    # Same categories as survey.current_vs_preference_multid.
    def cat(row):
        if row["_data_status"] == "low_response":
            return "low_response"
        if row["_data_status"] == "no_survey":
            return "no_survey"
        if "multi" in survey._clean_str(row.get(survey.ETHOS_COL, "")).lower():
            return "currently_multid"
        m = row["multid_pct"]
        return "wants_multid" if (not pd.isna(m)) and m >= 50 else "exclude"

    df["category"] = df.apply(cat, axis=1)
    df = df[df["category"] != "exclude"]

    groups = [
        ("wants_multid", "Denominational, but most parents want multi-denominational", "#eb6834", "circle", 7),
        ("currently_multid", "Already multi-denominational", "#1baf7a", "circle", 7),
        ("low_response", "Too few responses to report", "#a3aab3", "circle", 5),
        ("no_survey", "Not in the survey", "#52514e", "circle-open", 6),
    ]
    fig = go.Figure()
    base_geo(fig)
    for key, label, colour, symbol, size in groups:
        g = df[df["category"] == key]
        pct = g["multid_pct"].map(lambda v: "" if pd.isna(v) else f"<br>Parents preferring multi-denominational: <b>{v:.0f}%</b>")
        n = g["_total_valid"].map(lambda v: "" if pd.isna(v) else f" ({int(v):,} responses)")
        fig.add_trace(go.Scattergeo(
            lon=g[survey.LON_COL], lat=g[survey.LAT_COL], mode="markers",
            name=f"{label} ({len(g):,})",
            marker=dict(color=colour, size=size, symbol=symbol, opacity=0.9,
                        line=dict(color=SURFACE if symbol == "circle" else colour, width=0.8 if symbol == "circle" else 1.2)),
            customdata=np.stack([g[survey.NAME_COL].fillna("Unknown"), g[survey.COUNTY_COL].fillna(""),
                                 g[survey.ETHOS_COL].fillna(""), pct + n], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}%{customdata[3]}<extra></extra>",
        ))
    wants = (df["category"] == "wants_multid").sum()
    has = (df["category"] == "currently_multid").sum()
    fig.update_layout(base_layout(
        title=title(f"{wants:,} denominational schools where most parents want multi-denominational",
                    f"Against {has:,} schools that are already multi-denominational.<br>Preference combines parents of children in school and not yet in school"),
        showlegend=True, legend=legend_top(),
        margin=dict(l=10, r=10, t=172, b=10), height=780,
    ))
    save(fig, "map2_current_vs_preference.html")


# ── Patronage landscape (Schools page) ──────────────────────────────────────

# The three patronage groups on the Schools page. Inter-denominational schools
# are jointly run by two or more churches, so they count as denominational.
PATRON_GROUPS = [
    ("catholic", "Catholic", "#2a78d6"),
    ("other", "Church of Ireland and other faiths", "#eb6834"),
    ("multi", "Multi-denominational", "#1baf7a"),
]
OTHER_FAITHS = ["Church Of Ireland", "Inter Denominational", "Presbyterian", "Methodist", "Quaker", "Jewish", "Muslim"]
STATS_INCLUDE = os.path.join(ROOT, "religion", "_patronage-stats.md")


def pupils_column(df):
    """Enrolment is 'Enrolment per Return' in some years and 'Total' in others."""
    col = next(c for c in ("Total", "Enrolment per Return", "Enrolment") if c in df.columns)
    return pd.to_numeric(df[col], errors="coerce").fillna(0)


def patronage_table():
    """Schools and pupils in each patronage group, from the latest school list."""
    path = latest_school_list()
    df = read_school_list(path)
    df = df[df["Ethos Description"].notna()].copy()
    df["ethos"] = df["Ethos Description"].astype(str).str.strip()
    df["pupils"] = pupils_column(df)

    def group(e):
        if e == "Catholic":
            return "catholic"
        if e == "Multi Denominational":
            return "multi"
        if e in OTHER_FAITHS:
            return "other"
        raise ValueError(f"ethos with no patronage group: {e}")

    df["group"] = df["ethos"].map(group)
    for c in ("School Latitude", "School Longitude"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    t = df.groupby("group").agg(schools=("ethos", "size"), pupils=("pupils", "sum"))
    t["schools_pct"] = t["schools"] / t["schools"].sum() * 100
    t["pupils_pct"] = t["pupils"] / t["pupils"].sum() * 100
    return df, t, school_list_year(path)


def patronage():
    """Two maps (denominational, multi-denominational) and the headline numbers."""
    df, t, year = patronage_table()
    pts = df.dropna(subset=["School Latitude", "School Longitude"])
    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "geo"}, {"type": "geo"}]],
                        subplot_titles=["<b>Denominational</b>", "<b>Multi-denominational</b>"],
                        horizontal_spacing=0.02)
    panels = {1: ["catholic", "other"], 2: ["multi"]}
    for col, keys in panels.items():
        base_geo(fig, row=1, col=col)
        for key, label, colour in PATRON_GROUPS:
            if key not in keys:
                continue
            g = pts[pts["group"] == key]
            fig.add_trace(go.Scattergeo(
                lon=g["School Longitude"], lat=g["School Latitude"], mode="markers",
                name=label,
                marker=dict(color=colour, size=4 if key == "catholic" else 6,
                            opacity=0.7 if key == "catholic" else 0.95,
                            line=dict(color=SURFACE, width=0.5)),
                customdata=np.stack([g["Official Name"], g["County Description"], g["ethos"]], axis=-1),
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}<extra></extra>",
            ), row=1, col=col)
    fig.update_layout(base_layout(
        title=title(f"{t.loc['catholic', 'schools_pct']:.1f}% of primary schools have a Catholic patron",
                    f"Mainstream primary schools by patronage, {year} ({int(t['schools'].sum()):,} schools)"),
        showlegend=True, legend=legend_top() | dict(y=1.02),
        margin=dict(l=10, r=10, t=130, b=10), height=640,
    ))
    for a in fig.layout.annotations:
        a.font = dict(color=INK, size=14, family=FONT)
        a.y = 0.97
    save(fig, "patronage_maps.html")

    def card(key, headline, detail, cls):
        r = t.loc[key]
        return (f'<div class="stat-card {cls}"><div class="stat-number">{r.schools_pct:.1f}%</div>'
                f'<div class="stat-text"><strong>{headline}</strong><br>'
                f'<span>{detail.format(n=int(r.schools), p=int(r.pupils), pp=r.pupils_pct)}</span></div></div>')

    cards = [
        card("catholic", "of schools have a Catholic patron",
             "{n:,} schools · {p:,} pupils ({pp:.1f}% of pupils)", "is-catholic"),
        card("other", "Church of Ireland and other faiths",
             "Presbyterian, Methodist, Jewish, Muslim, Quaker and inter-denominational · {n:,} schools · {pp:.1f}% of pupils",
             "is-other"),
        card("multi", "are multi-denominational",
             "{n:,} schools · {p:,} pupils ({pp:.1f}% of pupils)", "is-multi"),
    ]
    with open(STATS_INCLUDE, "w", encoding="utf-8") as f:
        f.write("<!-- Written by analysis/charts/make_maps.py from the "
                f"{year} school list. Don't edit by hand. -->\n")
        f.write('<div class="stat-cards">\n' + "\n".join(cards) + "\n</div>\n")
    print("wrote", STATS_INCLUDE)
    return t


def preference_vs_provision(t):
    """Slide 17: what parents prefer against what exists today."""
    from staff_board_data import TABLE_2A_NATIONAL_PROPORTIONS as T2A
    prefer = float(T2A.set_index("household_type").loc["ALL", "multidenom_pct"])
    rows = [
        ("Households that prefer a multi-denominational school", prefer, "#eb6834"),
        ("Pupils in multi-denominational schools today", t.loc["multi", "pupils_pct"], "#1baf7a"),
        ("Schools that are multi-denominational today", t.loc["multi", "schools_pct"], "#1baf7a"),
    ]
    fig = go.Figure()
    labels = [r[0] for r in rows]
    fig.add_trace(go.Bar(y=labels, x=[100] * 3, orientation="h", marker=dict(color="#f3f2ee"),
                         hoverinfo="skip"))
    fig.add_trace(go.Bar(
        y=labels, x=[r[1] for r in rows], orientation="h", marker=dict(color=[r[2] for r in rows]),
        hovertemplate="%{y}: <b>%{x:.1f}%</b><extra></extra>",
    ))
    # Labels sit above each bar rather than beside it, so they fit on a phone.
    for label, value, colour in rows:
        fig.add_annotation(x=0, y=label, xanchor="left", yanchor="bottom", yshift=16, showarrow=False,
                           text=label, font=dict(size=14, color=INK))
        fig.add_annotation(x=100, y=label, xanchor="left", xshift=10, showarrow=False,
                           text=f"<b>{value:.1f}%</b>", font=dict(size=20, color=colour))
    fig.update_layout(base_layout(
        barmode="overlay", bargap=0.6,
        margin=dict(l=10, r=80, t=30, b=10), height=260,
        xaxis=axis_plain(range=[0, 100]),
        yaxis=dict(autorange="reversed", showticklabels=False, showgrid=False, zeroline=False,
                   showline=False, ticks=""),
    ))
    save(fig, "preference_vs_provision.html")


def axis_plain(**kw):
    a = dict(showgrid=False, zeroline=False, showline=False, ticks="", showticklabels=False)
    a.update(kw)
    return a


if __name__ == "__main__":
    ethos_map()
    survey_school_map()
    preference_vs_provision(patronage())
