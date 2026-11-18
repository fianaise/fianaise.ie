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
from make_charts import FONT, GRID, INK, INK_2, INK_3, SURFACE, CONFIG, REPORT_PDF, base_layout, title, save, save_csv  # noqa: E402

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
    save_csv(df[["Roll Number", "Official Name", "County Description", "ethos", "School Latitude", "School Longitude"]]
             .rename(columns={"Official Name": "School", "County Description": "County", "ethos": "Ethos",
                              "School Latitude": "Latitude", "School Longitude": "Longitude"})
             .assign(Source=f"Department of Education, Data on Individual Schools, mainstream primary {year}, {SCHOOL_LISTS}"),
             "ethos_current_config.csv")

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

SURVEY_RESULTS = os.path.join(RAW, "Primary_School_Results_For_All_Primary_Schools.xlsx")
SURVEY_COORDS = os.path.join(RAW, "Data_on_Individual_Schools_Mainstream_2024_25.xlsx")
SCHOOL_LISTS = "https://www.gov.ie/en/department-of-education/collections/data-on-individual-schools/"
SURVEY_PAGE = "https://www.gov.ie/en/department-of-education/campaigns/primary-school-survey/"
COUNTY_TABLE_INCLUDE = os.path.join(ROOT, "religion", "_county-multid-table.md")


def school_results():
    """The school-level survey results, one row per mainstream school, with each
    school's ethos and location from the Department's school lists.

    A school "wants multi-denominational" when more than half of the parents of
    children in the school who answered prefer a multi-denominational ethos
    (more than 50% of votes cast). This is the school-specific result the
    Department sent each school, and it counts 485 of the 2,731 mainstream
    denominational schools with a reportable result. Parents of children not yet
    in school are reported by school too, but they named a school they might
    use, so they are left out of the count and shown only in the hover text.
    Results are blank ("-") where too few parents answered to report. Special
    schools are left out: the school lists that give ethos cover mainstream
    schools only.
    """
    df = pd.read_excel(SURVEY_RESULTS, sheet_name=0)
    df = df[df[survey.ROLL_COL].notna()].copy()
    df["rn"] = df[survey.ROLL_COL].astype(str).str.strip().str.upper()
    df = df[df["School Type"].astype(str).str.strip() == "Mainstream"].copy()

    def school_list(path):
        sl = read_school_list(path)
        sl["rn"] = sl["Roll Number"].astype(str).str.strip().str.upper()
        for c in ("School Latitude", "School Longitude"):
            sl[c] = pd.to_numeric(sl[c], errors="coerce")
        return sl.drop_duplicates("rn").set_index("rn")

    # Locations and ethos from the 2024-25 list (the school year before the
    # survey), falling back to the latest list for schools not in it.
    lists = [school_list(SURVEY_COORDS), school_list(latest_school_list())]
    for col, out in (("School Latitude", survey.LAT_COL), ("School Longitude", survey.LON_COL),
                     ("Ethos Description", "ethos_detail")):
        df[out] = df["rn"].map(lists[0][col]).fillna(df["rn"].map(lists[1][col]))

    num = lambda c: pd.to_numeric(df[c], errors="coerce")  # noqa: E731
    df["in_valid"] = num(survey.VALIDATED_IN)
    df["in_multi"] = num(survey.MULTI_IN_N)
    df["in_pct"] = df["in_multi"] / df["in_valid"] * 100
    df["not_valid"] = num(survey.VALIDATED_NOT)
    df["not_pct"] = num(survey.MULTI_NOT_N) / df["not_valid"] * 100
    ethos = df[survey.ETHOS_COL].map(survey._clean_str).str.lower()
    df["is_multi"] = ethos.str.contains("multi")
    df["is_denominational"] = ~df["is_multi"]
    df["reportable"] = df["in_valid"].notna()
    df["wants_multid"] = df["is_denominational"] & (df["in_pct"] > 50)
    # The looser count: 50% or more of all parent responses for the school,
    # pooling parents of children not yet in school (preschool) with current
    # parents. 573 mainstream denominational schools; the old map showed 572
    # because it left out the one with no location.
    df["all_valid"] = df["in_valid"] + df["not_valid"].fillna(0)
    df["all_pct"] = (df["in_multi"] + num(survey.MULTI_NOT_N).fillna(0)) / df["all_valid"] * 100
    df["wants_with_preschool"] = df["is_denominational"] & (df["all_pct"] >= 50)
    df["ethos_detail"] = df["ethos_detail"].fillna("").astype(str).str.strip()
    df["faith"] = np.where(df["ethos_detail"] == "Catholic", "Catholic",
                           np.where(df["is_denominational"], "Other faith", ""))
    df["category"] = np.select(
        [df["is_multi"], ~df["reportable"], df["wants_multid"], df["wants_with_preschool"]],
        ["currently_multid", "low_response", "wants_multid", "preschool_only"], "other_denominational")
    return df


def survey_school_map():
    df = school_results()
    wants = int(df["wants_multid"].sum())
    wants_pooled = int(df["wants_with_preschool"].sum())
    has = int(df["is_multi"].sum())
    unmapped = df[survey.LAT_COL].isna() | df[survey.LON_COL].isna()
    # Counts in the legend include every school; a school with no location in
    # either school list can't be drawn. The survey page names any such school.
    for _, r in df[unmapped & (df["category"] != "other_denominational")].iterrows():
        print(f"  not on the map (no location): {r[survey.NAME_COL]}, {r[survey.COUNTY_COL]}, {r['category']}")
    groups = [
        ("wants_multid", "Denominational: more than 50% of current parents want multi-denominational", "#eb6834", "circle", 7),
        ("preschool_only", "Denominational: 50% or more only when preschool parents are included", "#f4b183", "circle", 6),
        ("currently_multid", "Already multi-denominational", "#1baf7a", "circle", 7),
        ("low_response", "Denominational, too few responses to report", "#a3aab3", "circle", 5),
    ]
    labels = {k: lab for k, lab, *_ in groups}
    labels["other_denominational"] = "Denominational: below both thresholds"
    yes = {True: "yes", False: "no"}
    out = df.assign(category=df["category"].map(labels),
                    wants_multid=df["wants_multid"].map(yes),
                    wants_with_preschool=df["wants_with_preschool"].map(yes))
    save_csv(out[[survey.ROLL_COL, survey.NAME_COL, survey.COUNTY_COL, survey.ETHOS_COL, "ethos_detail",
                  "category", "in_valid", "in_pct", "not_valid", "not_pct", "all_valid", "all_pct",
                  "wants_multid", "wants_with_preschool", survey.LAT_COL, survey.LON_COL]]
             .rename(columns={survey.NAME_COL: "School", survey.COUNTY_COL: "County", survey.ETHOS_COL: "Ethos (survey)",
                              "ethos_detail": "Ethos (school list)", "category": "Group",
                              "in_valid": "Valid responses, parents of children in school",
                              "in_pct": "Prefer multi-denominational, parents of children in school (%)",
                              "not_valid": "Valid responses, parents of children not yet in school",
                              "not_pct": "Prefer multi-denominational, parents of children not yet in school (%)",
                              "all_valid": "Valid responses, all parents",
                              "all_pct": "Prefer multi-denominational, all parents (%)",
                              "wants_multid": "More than 50% of current parents prefer multi-denominational",
                              "wants_with_preschool": "50% or more of all parents (incl. preschool) prefer multi-denominational",
                              survey.LAT_COL: "Latitude", survey.LON_COL: "Longitude"})
             .assign(Source=f"Primary School Survey, results for all primary schools ({SURVEY_PAGE}); "
                            f"locations from Data on Individual Schools 2024-25 ({SCHOOL_LISTS})"),
             "map2_current_vs_preference.csv")

    fig = go.Figure()
    base_geo(fig)
    for key, label, colour, symbol, size in groups:
        g = df[(df["category"] == key) & ~unmapped]
        pct = g["in_pct"].map(lambda v: "" if pd.isna(v) else f"<br>Current parents preferring multi-denominational: <b>{v:.1f}%</b>")
        n = g["in_valid"].map(lambda v: "" if pd.isna(v) else f" ({int(v):,} responses)")
        def more(r):
            t = "" if pd.isna(r["not_pct"]) else f"<br>Preschool parents: {r['not_pct']:.1f}% ({int(r['not_valid']):,} responses)"
            if not pd.isna(r["all_pct"]) and not pd.isna(r["not_pct"]):
                t += f"<br>All parents: {r['all_pct']:.1f}% ({int(r['all_valid']):,} responses)"
            return t
        nyet = g.apply(more, axis=1).astype(str) if len(g) else g["in_pct"].astype(str)
        fig.add_trace(go.Scattergeo(
            lon=g[survey.LON_COL], lat=g[survey.LAT_COL], mode="markers",
            name=f"{label} ({(df['category'] == key).sum():,})",
            marker=dict(color=colour, size=size, symbol=symbol, opacity=0.9,
                        line=dict(color=SURFACE if symbol == "circle" else colour, width=0.8 if symbol == "circle" else 1.2)),
            customdata=np.stack([g[survey.NAME_COL].fillna("Unknown"), g[survey.COUNTY_COL].fillna(""),
                                 g[survey.ETHOS_COL].fillna(""), pct + n + nyet], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}%{customdata[3]}<extra></extra>",
        ))
    fig.update_layout(base_layout(
        title=title(f"{wants:,} mainstream denominational schools where<br>most current parents want multi-denominational",
                    f"More than 50% of parents of current pupils prefer a multi-denominational ethos.<br>"
                    f"{wants_pooled:,} schools reach 50% or more when parents of preschool children are included.<br>"
                    f"{has:,} mainstream schools are already multi-denominational"),
        showlegend=True, legend=legend_top(),
        margin=dict(l=10, r=10, t=240, b=10), height=860,
    ))
    save(fig, "map2_current_vs_preference.html")
    return wants


def county_table():
    """Denominational mainstream schools in each county, and how many have
    parents wanting a multi-denominational ethos, on both definitions:

      current parents   more than 50% of parents of children in the school
      with preschool    50% or more of all parent responses for the school,
                        including parents of children not yet in school

    Shares are of the schools with a reportable result (enough responses).
    Writes religion/_county-multid-table.md (included on the survey page),
    figures/data/county_denominational_multid.csv and the county map
    figures/county_multid_map.html.
    """
    df = school_results()
    d = df[df["is_denominational"]].copy()
    d["catholic"] = d["faith"] == "Catholic"
    d["other"] = d["faith"] == "Other faith"
    assert (d["catholic"] | d["other"]).all(), "denominational school with no ethos in the school list"
    for key in ("wants_multid", "wants_with_preschool"):
        d[key + "_cath"] = d[key] & d["catholic"]
        d[key + "_other"] = d[key] & d["other"]
    agg = dict(schools=("catholic", "size"), catholic=("catholic", "sum"), other=("other", "sum"),
               reportable=("reportable", "sum"),
               cur=("wants_multid", "sum"), cur_cath=("wants_multid_cath", "sum"), cur_other=("wants_multid_other", "sum"),
               pre=("wants_with_preschool", "sum"), pre_cath=("wants_with_preschool_cath", "sum"),
               pre_other=("wants_with_preschool_other", "sum"))
    t = d.groupby(survey.COUNTY_COL).agg(**agg)
    total = d.assign(c="Ireland").groupby("c").agg(**agg)
    for x in (t, total):
        x["cur_pct"] = x["cur"] / x["reportable"] * 100
        x["pre_pct"] = x["pre"] / x["reportable"] * 100
    t = t.sort_values(["cur_pct", "cur"], ascending=False)

    out = pd.concat([t, total]).reset_index(names="County")
    save_csv(out.rename(columns={
        "schools": "Denominational schools", "catholic": "Catholic", "other": "Church of Ireland and other faiths",
        "reportable": "Schools with reportable results",
        "cur": "Current parents: schools where more than 50% prefer multi-denominational",
        "cur_cath": "Current parents: of which Catholic",
        "cur_other": "Current parents: of which Church of Ireland and other faiths",
        "cur_pct": "Current parents: share of schools with reportable results (%)",
        "pre": "Current and preschool parents: schools where 50% or more prefer multi-denominational",
        "pre_cath": "Current and preschool parents: of which Catholic",
        "pre_other": "Current and preschool parents: of which Church of Ireland and other faiths",
        "pre_pct": "Current and preschool parents: share of schools with reportable results (%)",
    }).assign(Source=f"Primary School Survey, results for all primary schools ({SURVEY_PAGE}); "
                     f"ethos from Data on Individual Schools 2024-25 ({SCHOOL_LISTS})"),
        "county_denominational_multid.csv")

    def row(name, r, cls=""):
        return (f'<tr{cls}><th scope="row">{name}</th><td>{int(r.schools):,}</td><td>{int(r.catholic):,}</td>'
                f'<td>{int(r.other):,}</td><td>{int(r.reportable):,}</td>'
                f'<td class="grp">{int(r.cur):,}</td>'
                f'<td data-value="{r.cur_pct:.2f}"><span class="pct-bar" style="--pct:{r.cur_pct:.1f}%"></span>{r.cur_pct:.1f}%</td>'
                f'<td class="grp">{int(r.pre):,}</td>'
                f'<td data-value="{r.pre_pct:.2f}"><span class="pct-bar is-pre" style="--pct:{r.pre_pct:.1f}%"></span>{r.pre_pct:.1f}%</td></tr>')

    head = ('<thead><tr class="group-row"><td colspan="5"></td>'
            '<th scope="colgroup" colspan="2" class="grp">Current parents<br><span>more than 50% want multi-den.</span></th>'
            '<th scope="colgroup" colspan="2" class="grp">Current and preschool parents<br><span>50% or more want multi-den.</span></th></tr>\n'
            '<tr><th scope="col">County</th><th scope="col">Denominational schools</th>'
            '<th scope="col">Catholic</th><th scope="col">Other faiths</th><th scope="col">With results</th>'
            '<th scope="col" class="grp">Schools</th><th scope="col">Share</th>'
            '<th scope="col" class="grp">Schools</th><th scope="col">Share</th></tr></thead>')
    body = "\n".join(row(c, r) for c, r in t.iterrows())
    foot = row("Ireland", total.iloc[0], ' class="total"')
    with open(COUNTY_TABLE_INCLUDE, "w", encoding="utf-8") as f:
        f.write("<!-- Written by analysis/charts/make_maps.py from the school-level survey results. "
                "Don't edit by hand. -->\n")
        f.write('<div class="data-table-wrap" data-figure="county_denominational_multid">\n'
                '<table class="data-table sortable" id="county-table">\n'
                f"{head}\n<tbody>\n{body}\n</tbody>\n<tfoot>\n{foot}\n</tfoot>\n</table>\n</div>\n")
    print("wrote", COUNTY_TABLE_INCLUDE)
    county_multid_map(t, total.iloc[0])
    return total.iloc[0]


def county_multid_map(t, nat):
    """Counties shaded by the share of denominational schools where parents want
    multi-denominational. Current parents by default; a menu switches to
    current and preschool parents. Both use the same colour scale."""
    t = t.reindex(COUNTIES)
    save_csv(pd.concat([t, nat.to_frame("Ireland").T])[["reportable", "cur", "cur_pct", "pre", "pre_pct"]]
             .astype({"reportable": int, "cur": int, "pre": int})
             .reset_index(names="County").rename(columns={
                 "reportable": "Denominational schools with reportable results",
                 "cur": "Current parents: schools where more than 50% prefer multi-denominational",
                 "cur_pct": "Current parents: share of schools (%)",
                 "pre": "Current and preschool parents: schools where 50% or more prefer multi-denominational",
                 "pre_pct": "Current and preschool parents: share of schools (%)",
             }).assign(Source=f"Primary School Survey, results for all primary schools ({SURVEY_PAGE}); "
                              f"ethos from Data on Individual Schools 2024-25 ({SCHOOL_LISTS})"),
             "county_multid_map.csv")
    zmax = float(np.ceil(max(t["cur_pct"].max(), t["pre_pct"].max()) / 10) * 10)
    scale = [[0, "#fdf1ea"], [0.35, "#f6b48f"], [0.7, "#eb6834"], [1, "#8f3410"]]
    views = [
        ("cur", "Current parents (more than 50%)", "more than 50% of current parents"),
        ("pre", "Current and preschool parents (50% or more)", "50% or more of current and preschool parents"),
    ]
    fig = go.Figure()
    base_geo(fig)
    for i, (key, label, how) in enumerate(views):
        hover = [f"<b>{c}</b><br>{int(r[key]):,} of {int(r.reportable):,} denominational schools: <b>{r[key + '_pct']:.1f}%</b>"
                 f"<br>{how} want multi-denominational" for c, r in t.iterrows()]
        fig.add_trace(go.Choropleth(
            geojson=GEO, locations=list(t.index), z=t[key + "_pct"].round(1), text=hover,
            hovertemplate="%{text}<extra></extra>", visible=(i == 0), name=label,
            colorscale=scale, zmin=0, zmax=zmax, marker_line=dict(color="#ffffff", width=0.8),
            colorbar=dict(title=dict(text="Share of<br>schools", font=dict(size=12, color=INK_2)),
                          ticksuffix="%", len=0.5, thickness=12, x=0.98, y=0.45,
                          tickfont=dict(size=11, color=INK_3), outlinewidth=0),
        ))

    def subtitle(key, how):
        return (f"Share of mainstream denominational schools where {how}<br>prefer a multi-denominational ethos. "
                f"Ireland: {int(nat[key]):,} of {int(nat.reportable):,} schools with results ({nat[key + '_pct']:.1f}%)")

    head = "Where parents want multi-denominational schools, county by county"
    buttons = [dict(label=label, method="update",
                    args=[{"visible": [True] + [j == i for j in range(len(views))]},
                          {"title": title(head, subtitle(key, how))}])
               for i, (key, label, how) in enumerate(views)]
    fig.update_layout(base_layout(
        title=title(head, subtitle("cur", views[0][2])),
        margin=dict(l=10, r=10, t=170, b=10), height=740,
        updatemenus=[dict(buttons=buttons, direction="down", x=0.02, xanchor="left", y=1.0, yanchor="bottom",
                          bgcolor="#ffffff", bordercolor=GRID, font=dict(size=13, color=INK), showactive=True)],
    ))
    save(fig, "county_multid_map.html")


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
    save_csv(df[["Roll Number", "Official Name", "County Description", "ethos", "group", "pupils",
                 "School Latitude", "School Longitude"]]
             .assign(group=df["group"].map({k: lab for k, lab, _ in PATRON_GROUPS}))
             .rename(columns={"Official Name": "School", "County Description": "County", "ethos": "Ethos",
                              "group": "Patronage group", "pupils": "Pupils",
                              "School Latitude": "Latitude", "School Longitude": "Longitude"})
             .assign(Source=f"Department of Education, Data on Individual Schools, mainstream primary "
                            f"{school_list_year(path)}, {SCHOOL_LISTS}"),
             "patronage_maps.csv")
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
        card("catholic", "of mainstream primary schools have a Catholic patron",
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
    return t, year


def preference_vs_provision(t, year):
    """Slide 17: what parents prefer against what exists today."""
    from staff_board_data import TABLE_2A_NATIONAL_PROPORTIONS as T2A
    prefer = float(T2A.set_index("household_type").loc["ALL", "multidenom_pct"])
    rows = [
        ("Households that prefer a multi-denominational school (all primary schools)", prefer, "#eb6834"),
        ("Pupils in multi-denominational mainstream schools today", t.loc["multi", "pupils_pct"], "#1baf7a"),
        ("Mainstream schools that are multi-denominational today", t.loc["multi", "schools_pct"], "#1baf7a"),
    ]
    save_csv(pd.DataFrame({"Measure": [r[0] for r in rows], "Percent": [r[1] for r in rows],
                           "Source": ["Primary School Survey results summary report (June 2026), Table 2a, p. 16, "
                                      f"{REPORT_PDF}#page=16",
                                      f"Department of Education, Data on Individual Schools, mainstream primary {year}, {SCHOOL_LISTS}",
                                      f"Department of Education, Data on Individual Schools, mainstream primary {year}, {SCHOOL_LISTS}"]}),
             "preference_vs_provision.csv")
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
    county_table()
    preference_vs_provision(*patronage())
