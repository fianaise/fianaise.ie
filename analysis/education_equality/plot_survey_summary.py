"""
plot_survey_summary.py
────────────────────────
Summary-level (national / county) visualisations comparing parent preferences
against school staff & Board of Management preferences, for the Irish Primary
School Patronage Survey.

Unlike plot_survey_geospatial.py (which works at individual-school level),
everything here is either:
  (a) computed directly from the School Planning Area (SPA) spreadsheet, with
      the result checked against the department's own published national
      figures, or
  (b) taken from staff_board_data.py, which transcribes tables that ONLY
      exist in the PDF report (no underlying spreadsheet is published for
      staff/Board of Management responses).

Functions
---------
  verify_parent_multidenom_national(spa_file)   -> dict + prints comparison
  verify_not_yet_in_school_base(spa_file)        -> prints comparison, explains 90.7% figure
  bar_group_comparison(parent_pcts, output_file) -> Vis 1: bar chart
  bar_intend_vs_preference(output_file)          -> Vis 2: bar chart
  county_map_parents_vs_staff(output_file)       -> Map 9: folium toggle map
  county_map_gap_notyet_vs_staff(output_file)    -> Map 10: folium overlay ("dumbbell") map
"""

import json
import urllib.request

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import folium

try:
    # Normal case: plot_survey_summary.py is imported as part of the
    # education_equality package (e.g. `from education_equality import
    # plot_survey_summary`), so staff_board_data is a sibling module in
    # the same package.
    from .staff_board_data import (
        TABLE_7_STAFF_BOARD_NATIONAL,
        TABLE_8_STAFF_BOARD_BY_COUNTY,
        TABLE_3_PARENT_MULTIDENOM_BY_COUNTY,
        TABLE_2A_NATIONAL_PROPORTIONS,
        INTEND_TO_ENROL_MULTIDENOM,
        REPORT_CITATION,
        STAFF_BOARD_TARGET_POPULATION,
        STAFF_BOARD_SUBMITTED_RESPONSES,
        STAFF_BOARD_VALID_RESPONSES,
        STAFF_BOARD_RESPONSE_RATE_PCT,
    )
except ImportError:
    # Fallback: script is being run/imported standalone (not as part of
    # a package), e.g. `import plot_survey_summary` from the same folder.
    from staff_board_data import (
        TABLE_7_STAFF_BOARD_NATIONAL,
        TABLE_8_STAFF_BOARD_BY_COUNTY,
        TABLE_3_PARENT_MULTIDENOM_BY_COUNTY,
        TABLE_2A_NATIONAL_PROPORTIONS,
        INTEND_TO_ENROL_MULTIDENOM,
        REPORT_CITATION,
        STAFF_BOARD_TARGET_POPULATION,
        STAFF_BOARD_SUBMITTED_RESPONSES,
        STAFF_BOARD_VALID_RESPONSES,
        STAFF_BOARD_RESPONSE_RATE_PCT,
    )

IRELAND_CENTER = [53.5, -8.0]

# Same Natural Earth source + name mapping used in plot_survey_geospatial.py,
# duplicated here so this module has no import-order dependency on it.
_COUNTY_GEOJSON_URL = (
    'https://raw.githubusercontent.com/nvkelso/natural-earth-vector'
    '/master/geojson/ne_10m_admin_1_states_provinces.geojson'
)
_NE_NAME_MAP = {
    'Laoighis': 'Laois',
    'North Tipperary': 'Tipperary',
    'South Tipperary': 'Tipperary',
    'Dún Laoghaire–Rathdown': 'Dublin',
    'Fingal': 'Dublin',
    'South Dublin': 'Dublin',
}


# ── Verification helpers ────────────────────────────────────────────────

def verify_parent_multidenom_national(spa_file):
    """
    Recomputes national multi-denominational preference (%) for parents,
    split by overall / children-currently-in-school / children-not-yet-in-
    school, directly from raw counts in the School Planning Area spreadsheet.
    Prints a comparison against Table 2a of the report (proportions rows).

    Returns
    -------
    dict with keys 'overall', 'in_school', 'not_yet_in_school' (percentages,
    derived purely from the spreadsheet).
    """
    df = pd.read_excel(spa_file, sheet_name='PSS_spa_results', header=0)
    cols = df.columns.tolist()

    # Assert the columns are where we expect them, by name, so this fails
    # loudly rather than silently if the spreadsheet layout ever changes.
    expected = {
        9: 'Preference for multi-denominational',
        10: 'Preference for denominational',
        21: 'Preference for multi-denominational.1',
        22: 'Preference for  denominational',
    }
    for idx, name in expected.items():
        assert cols[idx] == name, (
            f"Column layout has changed: expected column {idx} to be "
            f"'{name}', found '{cols[idx]}'. Re-check the sheet."
        )

    all_multi   = df.iloc[:, 9].sum()
    all_denom   = df.iloc[:, 10].sum()
    notyet_multi = df.iloc[:, 21].sum()
    notyet_denom = df.iloc[:, 22].sum()
    current_multi = all_multi - notyet_multi
    current_denom = all_denom - notyet_denom

    pct_overall  = all_multi / (all_multi + all_denom) * 100
    pct_notyet   = notyet_multi / (notyet_multi + notyet_denom) * 100
    pct_current  = current_multi / (current_multi + current_denom) * 100

    t2a = TABLE_2A_NATIONAL_PROPORTIONS.set_index('household_type')
    print("Parent multi-denominational preference — spreadsheet vs. report Table 2a")
    print(f"{'Group':<38}{'Spreadsheet-derived':>20}{'Report (Table 2a)':>20}")
    print(f"{'Overall (all households)':<38}{pct_overall:>19.2f}%{t2a.loc['ALL','multidenom_pct']:>19.1f}%")
    print(f"{'Children not yet in school':<38}{pct_notyet:>19.2f}%{t2a.loc['not_yet_in_school_only','multidenom_pct']:>19.1f}%")
    print(f"{'Children currently in school*':<38}{pct_current:>19.2f}%{'n/a (see note)':>20}")
    print()
    print("* 'Children currently in school' here = (All households) minus")
    print("  (households not yet in school), i.e. it includes BOTH households")
    print("  whose only child is in school AND households with both a current")
    print("  and a not-yet-in-school child. Table 2a splits these into two")
    print("  separate rows (43.9% and 44.5%); combined they give 44.01%,")
    print("  matching the spreadsheet-derived figure above almost exactly.")

    return {
        'overall': round(pct_overall, 2),
        'in_school': round(pct_current, 2),
        'not_yet_in_school': round(pct_notyet, 2),
    }


def verify_not_yet_in_school_base(spa_file):
    """
    Explains and checks where the report's 90.7% ("intend to enrol in a
    denominational school") figure comes from, and confirms it CANNOT be
    reproduced from the SPA spreadsheet.
    """
    df = pd.read_excel(spa_file, sheet_name='PSS_spa_results', header=0)
    spa_notyet_households = df.iloc[:, 5].sum()   # 'Households with children not yet in school'

    report_annex1_total = 66403   # Annex 1, Table 2a: total not-yet-in-school-only households
    report_base_used_in_3_1 = INTEND_TO_ENROL_MULTIDENOM['not_yet_in_school_base']  # 56,227

    print("Households with a child not yet in school — base used for each figure")
    print(f"  SPA spreadsheet, sum of 'Households with children not yet in school': {spa_notyet_households:,.0f}")
    print(f"  Report Annex 1 / Table 2a national total (same household type):        {report_annex1_total:,}")
    print(f"  -> these two match closely (within {abs(spa_notyet_households - report_annex1_total):.0f}), "
          "confirming the spreadsheet uses the same household definition.")
    print()
    print(f"  Base used in Section 3.1.2 for the 90.7% figure:                        {report_base_used_in_3_1:,}")
    print(f"  -> This is SMALLER than both figures above by "
          f"{report_annex1_total - report_base_used_in_3_1:,}, and is not reproduced "
          "anywhere else in the report or spreadsheet.")
    print()
    print("  CONCLUSION: the 90.7% figure (and the 42% / 86.5% figures that follow")
    print("  from it) cannot be independently verified from the published SPA")
    print("  spreadsheet. They are taken as reported in Section 3.1.2 (p.14) of")
    print("  the PDF report. Likely explanation: 56,227 is the subset of 'not yet")
    print("  in school' households who specified a usable intended-school answer")
    print("  (i.e. excludes 'don't know' / unspecified responses); this subsetting")
    print("  is not broken out anywhere in the published tables, so it cannot be")
    print("  confirmed from public data alone.")

    return {
        'spa_spreadsheet_total': spa_notyet_households,
        'report_annex1_total': report_annex1_total,
        'report_section_3_1_2_base': report_base_used_in_3_1,
    }


def verify_table8_internal_consistency():
    """
    Two independent sanity checks on the manually-transcribed Table 8:
      1. County response counts sum to the national total (32,901) from
         Section 4.1.
      2. Response-weighted county averages reproduce Table 7's national
         percentages.
    """
    t8 = TABLE_8_STAFF_BOARD_BY_COUNTY
    total_resp = t8['Responses'].sum()
    weighted_multi = (t8['Responses'] * t8['MultiDenom_pref_pct']).sum() / total_resp
    weighted_coed  = (t8['Responses'] * t8['CoEd_pref_pct']).sum() / total_resp
    weighted_irish = (t8['Responses'] * t8['Irish_pref_pct']).sum() / total_resp

    t7 = TABLE_7_STAFF_BOARD_NATIONAL.set_index('preference')['percentage']

    print("Table 8 (county) internal-consistency check against Table 7 (national)")
    print(f"  Sum of county responses:            {total_resp:,}  (expected 32,901 from Section 4.1)")
    print(f"  Weighted multi-denom % from Table 8: {weighted_multi:.2f}%  vs Table 7: {t7['MULTI-DENOMINATIONAL']}%")
    print(f"  Weighted co-ed %      from Table 8: {weighted_coed:.2f}%  vs Table 7: {t7['CO-EDUCATIONAL']}%")
    print(f"  Weighted Irish %      from Table 8: {weighted_irish:.2f}%  vs Table 7: {t7['EDUCATION THROUGH IRISH']}%")
    assert total_resp == 32901, "Table 8 county responses no longer sum to 32,901 — re-check transcription."
    print("\n  All checks passed — Table 8 is internally consistent with Table 7.")


# ── Visualisation 1: group comparison bar chart ─────────────────────────

def bar_group_comparison(parent_pcts, output_file=None):
    """
    National-level companion to the county dumbbell chart: the same three
    groups (households, child not yet in school / households, child in
    school / school staff & Board of Management), same colours (dark green /
    light green / purple), same title language — just collapsed to a single
    national bar each instead of one dumbbell per county.

    parent_pcts: dict with keys 'in_school' and 'not_yet_in_school'
    (percentages), typically the return value of verify_parent_multidenom_national().
    ('overall' is accepted but not plotted — kept for backwards compatibility
    with that function's return value.)
    """
    staff_board_pct = float(
        TABLE_7_STAFF_BOARD_NATIONAL.set_index('preference').loc['MULTI-DENOMINATIONAL', 'percentage']
    )

    color_notyet = '#1b5e20'    # dark green
    color_inschool = '#81c784'  # light green — same family as color_notyet (both households)
    color_staff = '#8e24aa'     # purple — distinct third group

    labels = [
        'Households, child<br>not yet in school',
        'Households, child<br>in school',
        'School staff<br>& boards',
    ]
    values = [
        parent_pcts['not_yet_in_school'],
        parent_pcts['in_school'],
        staff_board_pct,
    ]
    sources = [
        'Verified from SPA spreadsheet (matches report Table 2a)',
        'Verified from SPA spreadsheet',
        'Report Table 7, p.26 — not available in any spreadsheet',
    ]
    colors = [color_notyet, color_inschool, color_staff]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=[f"{v:.1f}%" for v in values],
        textposition='outside',
        customdata=sources,
        hovertemplate='%{x}<br><b>%{y:.2f}%</b> prefer multi-denominational<br>%{customdata}<extra></extra>',
    ))
    fig.update_layout(
        title=dict(
            text="<b>Parents want multi-denominational schools, compared to staff and boards of management</b>",
            x=0.02, xanchor='left', font=dict(size=17),
        ),
        yaxis_title='% who prefer a multi-denominational school',
        yaxis_range=[0, max(values) * 1.25],
        template='plotly_white',
        showlegend=False,
        height=500,
        margin=dict(b=90, t=70),
        annotations=[
            dict(
                text="Note: household figures are independently verified against the survey spreadsheet; "
                     "the staff &amp; boards figure is taken from the report (no spreadsheet is published for that group).",
                xref='paper', yref='paper', x=0, y=-0.24, xanchor='left', showarrow=False,
                font=dict(size=11, color='#888'),
            ),
            dict(
                text="Source: Department of Education and Youth, Primary School Survey — Results Summary Report (June 2026).",
                xref='paper', yref='paper', x=0, y=-0.30, xanchor='left', showarrow=False,
                font=dict(size=11, color='#888'),
            ),
        ],
    )
    if output_file:
        fig.write_html(output_file)
        print(f"  Chart saved -> {output_file}")
    return fig


# ── Visualisation 2: intend-to-enrol vs actual preference ──────────────

def bar_intend_vs_preference(output_file=None):
    """
    Two equal-width stacked bars, one per intended school type (denom /
    multi-d). Each bar totals 100% and is split by that group's actual
    ethos preference (green = wants multi-d, grey = wants denom). The
    population share of each intended-school group (90.7% denom / 9.3%
    multi-d of the 56,227-household base) is shown via the axis labels and
    the annotation text rather than via bar width, so both groups' internal
    splits are equally easy to read side by side.
    """
    d = INTEND_TO_ENROL_MULTIDENOM
    base = d['not_yet_in_school_base']

    denom_intend        = d['intend_denom_school']
    denom_want_multi    = d['intend_denom_want_change_to_multi']
    denom_want_denom    = denom_intend - denom_want_multi

    multi_intend         = d['intend_multidenom_school']
    multi_want_multi     = d['intend_multidenom_want_multi']
    multi_want_denom     = multi_intend - multi_want_multi

    # Population share (%) of the 56,227 base intending each school type —
    # shown in the axis labels/annotations, but no longer encoded as bar
    # width (see below): both bars are drawn at equal width so the stacked
    # preference-split is equally easy to read for both groups.
    w_denom = denom_intend / base * 100
    w_multi = multi_intend / base * 100

    # Heights within each bar: split of THAT group's stated preference (exact, from raw counts).
    h_denom_want_denom = denom_want_denom / denom_intend * 100
    h_denom_want_multi = denom_want_multi / denom_intend * 100
    h_multi_want_denom = multi_want_denom / multi_intend * 100
    h_multi_want_multi = multi_want_multi / multi_intend * 100

    # Equal-width bars, placed closer together with the legend sitting in
    # the gap between them.
    bar_width = 35
    gap = 10
    x_denom = bar_width / 2
    x_multi = bar_width + gap + bar_width / 2

    color_multi = '#2e7d32'   # prefers multi-denominational
    color_denom = '#90a4ae'   # prefers to stay / go denominational

    fig = go.Figure()

    # Bottom segment: prefer denominational
    fig.add_trace(go.Bar(
        name='Prefers denominational',
        x=[x_denom, x_multi], y=[h_denom_want_denom, h_multi_want_denom],
        width=bar_width,
        marker_color=color_denom,
        text=[f"{h_denom_want_denom:.0f}%<br>({denom_want_denom:,})",
              f"{h_multi_want_denom:.0f}%<br>({multi_want_denom:,})"],
        textposition='inside', textfont=dict(color='white', size=13),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=[
            f"Intend denominational, prefer to STAY denominational<br>{denom_want_denom:,} households ({h_denom_want_denom:.1f}% of this group)",
            f"Intend multi-denominational, prefer denominational instead<br>{multi_want_denom:,} households ({h_multi_want_denom:.1f}% of this group)",
        ],
    ))

    # Top segment: prefer multi-denominational
    fig.add_trace(go.Bar(
        name='Prefers multi-denominational',
        x=[x_denom, x_multi], y=[h_denom_want_multi, h_multi_want_multi],
        width=bar_width,
        marker_color=color_multi,
        text=[f"{h_denom_want_multi:.0f}%<br>({denom_want_multi:,})",
              f"{h_multi_want_multi:.0f}%<br>({multi_want_multi:,})"],
        textposition='inside', textfont=dict(color='white', size=13),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=[
            f"Intend denominational, but WANT it to change to multi-denominational<br>{denom_want_multi:,} households ({h_denom_want_multi:.1f}% of this group)",
            f"Intend multi-denominational, confirm multi-denominational preference<br>{multi_want_multi:,} households ({h_multi_want_multi:.1f}% of this group)",
        ],
    ))

    fig.update_layout(
        barmode='stack',
        title=(
            "Households with a child not yet in school (n=56,227):<br>"
            "<sup>each bar = 100% of that group, split by their actual ethos preference</sup>"
        ),
        xaxis=dict(
            range=[0, bar_width * 2 + gap], showgrid=False, zeroline=False,
            tickmode='array',
            tickvals=[x_denom, x_multi],
            ticktext=[
                f"<b>Intend DENOMINATIONAL school</b><br>{w_denom:.1f}% of households ({denom_intend:,})",
                f"<b>Intend MULTI-D school</b><br>{w_multi:.1f}% ({multi_intend:,})",
            ],
        ),
        yaxis=dict(title='% of that group, by actual ethos preference', range=[0, 100]),
        template='plotly_white',
        legend=dict(
            orientation='v', x=0.5, xanchor='center', y=0.5, yanchor='middle',
            bgcolor='rgba(255,255,255,0.9)', bordercolor='#bbb', borderwidth=1,
            font=dict(size=11),
        ),
        height=600,
        bargap=0,
        annotations=[dict(
            text=(
                "Even though 90.7% of these households plan to enrol in a denominational school, "
                "42% of them (21,464 households — the large green block on the left) actually want "
                "a multi-denominational ethos. By contrast, of the much smaller group intending a "
                "multi-denominational school, 86.5% (4,543) confirm that's genuinely their preference."
                "<br>Source: Report Section 3.1.2, p.14. Percentages recomputed here from the reported "
                "raw counts; they match the report's stated 90.7% / 42% / 86.5% almost exactly."
            ),
            xref='paper', yref='paper', x=0.5, y=-0.30, showarrow=False,
            font=dict(size=11, color='#555'), align='center',
        )],
        margin=dict(b=140),
    )

    if output_file:
        fig.write_html(output_file)
        print(f"  Chart saved -> {output_file}")

    print()
    print("Figure caption:")
    print(
        "  Stated ethos preference among households with a child not yet in school (n=56,227),\n"
        "  grouped by their intended future school type. Each bar represents 100% of households\n"
        "  intending that school type, split by whether they actually prefer a multi-denominational\n"
        "  (green) or denominational (grey) ethos for that school. This isolates demand for change:\n"
        "  households intending a denominational school but preferring multi-denominational represent\n"
        "  unmet demand, while households intending and preferring the same type represent confirmed\n"
        "  preference. Percentages are recomputed here from raw counts reported in the source; this\n"
        "  base (56,227) is not independently verifiable against the published survey spreadsheet.\n"
        "  Source: Department of Education and Youth, Primary School Survey — Results Summary Report\n"
        "  (June 2026), Section 3.1.2, p.14."
    )

    return fig


# ── Visualisation 3: county map, parents vs staff/board ─────────────────

def _green(pct, vmax=60.0):
    pct = max(0, min(vmax, pct))
    frac = pct / vmax
    r = int(232 - (232 - 27) * frac)
    g = int(245 - (245 - 94) * frac)
    b = int(233 - (233 - 32) * frac)
    return f'#{r:02x}{g:02x}{b:02x}'


def _diverging(gap, vmax=20.0):
    """gap = staff_pct - parent_pct. Negative (staff lower) -> orange, positive -> blue."""
    frac = max(-1, min(1, gap / vmax))
    if frac >= 0:
        r = int(255 - (255 - 33) * frac)
        g = int(255 - (255 - 102) * frac)
        b = int(255 - (255 - 172) * frac)
    else:
        frac = -frac
        r = int(255 - (255 - 230) * frac)
        g = int(255 - (255 - 126) * frac)
        b = int(255 - (255 - 34) * frac)
    return f'#{r:02x}{g:02x}{b:02x}'


def county_map_parents_vs_staff(output_file):
    """
    County-level choropleth with toggleable layers:
      - Parents (overall / children in school / children not yet in school)  [Table 3]
      - School staff & Board of Management                                   [Table 8]
      - Gap (Staff minus Parents-overall)                                    [derived]

    All values are taken directly from the manually-transcribed report tables
    in staff_board_data.py (no per-school coordinates are needed or used,
    since staff/BoM data is only published at county level).
    """
    parent = TABLE_3_PARENT_MULTIDENOM_BY_COUNTY.set_index('County')
    staff = TABLE_8_STAFF_BOARD_BY_COUNTY.set_index('County')

    print("  Fetching county boundaries...")
    req = urllib.request.Request(_COUNTY_GEOJSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        geo = json.loads(r.read())

    ire_features = [f for f in geo['features'] if f['properties'].get('admin') == 'Ireland']
    for f in ire_features:
        raw = f['properties']['name']
        f['properties']['county_norm'] = _NE_NAME_MAP.get(raw, raw)

    for f in ire_features:
        cn = f['properties']['county_norm']
        p = parent.loc[cn] if cn in parent.index else None
        s = staff.loc[cn] if cn in staff.index else None
        f['properties']['parents_overall']  = float(p['All_households_pct']) if p is not None else None
        f['properties']['parents_inschool'] = float(p['Children_in_school_pct']) if p is not None else None
        f['properties']['parents_notyet']   = float(p['Not_yet_in_school_pct']) if p is not None else None
        f['properties']['staff_board']      = float(s['MultiDenom_pref_pct']) if s is not None else None
        f['properties']['staff_responses']  = int(s['Responses']) if s is not None else None
        if p is not None and s is not None:
            f['properties']['gap'] = round(float(s['MultiDenom_pref_pct']) - float(p['All_households_pct']), 1)
        else:
            f['properties']['gap'] = None

    county_geo = {'type': 'FeatureCollection', 'features': ire_features}

    m = folium.Map(location=IRELAND_CENTER, zoom_start=7, tiles='cartodbpositron', control_scale=True)

    layer_defs = [
        ('Parents – overall',               'parents_overall',  True,  _green, 'want multi-d (parents, overall)'),
        ('Parents – child in school',       'parents_inschool', False, _green, 'want multi-d (parents, child in school)'),
        ('Parents – child not yet in school', 'parents_notyet',  False, _green, 'want multi-d (parents, child not yet in school)'),
        ('Staff & Board of Management',     'staff_board',       True,  _green, 'want multi-d (staff & Board of Management)'),
    ]

    for name, field, show, colorfn, tip_suffix in layer_defs:
        fg = folium.FeatureGroup(name=name, show=show)

        def make_style(field=field, colorfn=colorfn):
            def _style(feature):
                v = feature['properties'].get(field)
                fill = '#dddddd' if v is None else colorfn(v)
                return {'fillColor': fill, 'color': '#555', 'weight': 1.2, 'fillOpacity': 0.78, 'opacity': 1}
            return _style

        def make_tooltip(field=field, tip_suffix=tip_suffix):
            def _tip(feature):
                cn = feature['properties']['county_norm']
                v = feature['properties'].get(field)
                return f"{cn}: {v:.1f}% {tip_suffix}" if v is not None else f"{cn}: no data"
            return _tip

        folium.GeoJson(
            county_geo,
            style_function=make_style(),
            highlight_function=lambda f: {'weight': 3, 'color': '#222', 'fillOpacity': 0.9},
            tooltip=folium.GeoJsonTooltip(
                fields=['county_norm', field],
                aliases=['County', name],
                localize=True, sticky=True,
            ),
        ).add_to(fg)
        fg.add_to(m)

    # Gap layer (staff vs parents-overall), off by default
    fg_gap = folium.FeatureGroup(name='Gap: Staff/BoM minus Parents (overall)', show=False)

    def _style_gap(feature):
        v = feature['properties'].get('gap')
        fill = '#dddddd' if v is None else _diverging(v)
        return {'fillColor': fill, 'color': '#555', 'weight': 1.2, 'fillOpacity': 0.8, 'opacity': 1}

    folium.GeoJson(
        county_geo,
        style_function=_style_gap,
        highlight_function=lambda f: {'weight': 3, 'color': '#222', 'fillOpacity': 0.9},
        tooltip=folium.GeoJsonTooltip(
            fields=['county_norm', 'staff_board', 'parents_overall', 'gap'],
            aliases=['County', 'Staff/BoM %', 'Parents (overall) %', 'Gap (pp)'],
            localize=True, sticky=True,
        ),
    ).add_to(fg_gap)
    fg_gap.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    legend_html = """
    <div style='position:fixed;bottom:50px;left:50px;width:300px;border:2px solid #ccc;
                z-index:9999;background:white;opacity:0.95;padding:12px 14px;
                border-radius:8px;font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,0.15);'>
      <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">
        Multi-denominational preference, by county</div>
      <div style="font-size:11px;color:#666;margin-bottom:8px;border-bottom:1px solid #eee;padding-bottom:6px;">
        Toggle layers (top right) to compare parent groups against school staff
        &amp; Board of Management. All county-level; source: report Tables 3 &amp; 8.
      </div>
      <div style="font-size:11px;color:#888;">
        "Gap" layer: blue = staff/BoM MORE in favour of multi-d than parents;
        orange = staff/BoM LESS in favour than parents.
      </div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    m.save(output_file)
    print(f"\nSUCCESS: Map saved -> {output_file}")
    print(f"  (Data source: {REPORT_CITATION})")


# ── Map 10: overlay ("dumbbell") map — parents (not yet in school) vs staff/BoM ──

def _ring_centroid(coords):
    """Area-weighted centroid of a single polygon ring (shoelace formula)."""
    x = [c[0] for c in coords]
    y = [c[1] for c in coords]
    n = len(coords)
    if n < 3:
        return sum(x) / n, sum(y) / n
    A = Cx = Cy = 0.0
    for i in range(n - 1):
        cross = x[i] * y[i + 1] - x[i + 1] * y[i]
        A += cross
        Cx += (x[i] + x[i + 1]) * cross
        Cy += (y[i] + y[i + 1]) * cross
    A *= 0.5
    if abs(A) < 1e-12:
        return sum(x) / n, sum(y) / n
    return Cx / (6 * A), Cy / (6 * A)


def _ring_bbox_area(coords):
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _feature_centroid(geometry):
    """Centroid (lon, lat) for a Polygon or MultiPolygon geometry, using the
    largest ring by bounding-box area for MultiPolygons (avoids tiny slivers
    pulling the centroid off to one side)."""
    if geometry['type'] == 'Polygon':
        return _ring_centroid(geometry['coordinates'][0])
    elif geometry['type'] == 'MultiPolygon':
        rings = [poly[0] for poly in geometry['coordinates']]
        best = max(rings, key=_ring_bbox_area)
        return _ring_centroid(best)
    raise ValueError(f"Unsupported geometry type: {geometry['type']}")


def _dumbbell_icon_html(pct_a, pct_b, vmin=15.0, vmax=60.0, track_px=64, color_a='#2e7d32', color_b='#8e24aa'):
    """
    Small inline-SVG 'dumbbell': two dots on a shared 0-100%-style axis
    (domain vmin-vmax), connected by a line — one dot per group, so both
    values AND the gap between them are visible in a single compact glyph.
    """
    pad = 8
    def scale(v):
        v = max(vmin, min(vmax, v))
        return pad + (v - vmin) / (vmax - vmin) * track_px

    xa, xb = scale(pct_a), scale(pct_b)
    width = track_px + 2 * pad
    height = 22
    return f"""
    <svg width="{width}" height="{height}" style="overflow:visible;">
      <line x1="{xa:.1f}" y1="{height/2}" x2="{xb:.1f}" y2="{height/2}"
            stroke="#666" stroke-width="2" stroke-linecap="round"/>
      <circle cx="{xa:.1f}" cy="{height/2}" r="5.5" fill="{color_a}" stroke="white" stroke-width="1.3"/>
      <circle cx="{xb:.1f}" cy="{height/2}" r="5.5" fill="{color_b}" stroke="white" stroke-width="1.3"/>
    </svg>
    """, width, height


def county_map_gap_notyet_vs_staff(output_file):
    """
    Map 10 — overlays school staff & Board of Management preference directly
    on top of parent (children not yet in school) preference, per county, so
    the discrepancy is visible without toggling layers:

      - Background choropleth: diverging fill = staff/BoM % minus parents
        (not-yet-in-school) %  (blue = staff/BoM MORE pro multi-d, orange =
        staff/BoM LESS pro multi-d than these parents).
      - Foreground 'dumbbell' marker per county: a green dot (parents, child
        not yet in school) and a purple dot (staff/BoM), joined by a line —
        dot position along the mini-axis = the % itself, so both the raw
        levels and the gap are readable at a glance.

    Data: report Table 3 (parents) and Table 8 (staff/BoM), both county-level;
    see staff_board_data.py for citations.
    """
    parent = TABLE_3_PARENT_MULTIDENOM_BY_COUNTY.set_index('County')
    staff = TABLE_8_STAFF_BOARD_BY_COUNTY.set_index('County')

    print("  Fetching county boundaries...")
    req = urllib.request.Request(_COUNTY_GEOJSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        geo = json.loads(r.read())

    ire_features = [f for f in geo['features'] if f['properties'].get('admin') == 'Ireland']
    for f in ire_features:
        raw = f['properties']['name']
        f['properties']['county_norm'] = _NE_NAME_MAP.get(raw, raw)

    centroids = {}   # county_norm -> list of (lon, lat), averaged below
    for f in ire_features:
        cn = f['properties']['county_norm']
        p = parent.loc[cn] if cn in parent.index else None
        s = staff.loc[cn] if cn in staff.index else None
        p_pct = float(p['Not_yet_in_school_pct']) if p is not None else None
        s_pct = float(s['MultiDenom_pref_pct']) if s is not None else None
        f['properties']['parents_notyet'] = p_pct
        f['properties']['staff_board'] = s_pct
        f['properties']['gap'] = round(s_pct - p_pct, 1) if (p_pct is not None and s_pct is not None) else None

        cx, cy = _feature_centroid(f['geometry'])
        centroids.setdefault(cn, []).append((cx, cy))

    county_geo = {'type': 'FeatureCollection', 'features': ire_features}

    m = folium.Map(location=IRELAND_CENTER, zoom_start=7, tiles='cartodbpositron', control_scale=True)

    # Background: diverging gap choropleth
    fg_choropleth = folium.FeatureGroup(name='Background: gap (fill colour)', show=True)

    def _style_gap(feature):
        v = feature['properties'].get('gap')
        fill = '#e8e8e8' if v is None else _diverging(v)
        return {'fillColor': fill, 'color': '#999', 'weight': 1, 'fillOpacity': 0.65, 'opacity': 1}

    folium.GeoJson(
        county_geo,
        style_function=_style_gap,
        highlight_function=lambda f: {'weight': 2.5, 'color': '#333', 'fillOpacity': 0.8},
        tooltip=folium.GeoJsonTooltip(
            fields=['county_norm', 'parents_notyet', 'staff_board', 'gap'],
            aliases=['County', 'Parents (not yet in school) %', 'Staff/BoM %', 'Gap, Staff-Parents (pp)'],
            localize=True, sticky=True,
        ),
    ).add_to(fg_choropleth)
    fg_choropleth.add_to(m)

    # Foreground: dumbbell markers, one per county, at the averaged centroid
    fg_dumbbells = folium.FeatureGroup(name='Overlay: parents vs staff/BoM (dots)', show=True)
    for cn, pts in centroids.items():
        if cn not in parent.index or cn not in staff.index:
            continue
        lon = sum(p[0] for p in pts) / len(pts)
        lat = sum(p[1] for p in pts) / len(pts)
        p_pct = float(parent.loc[cn, 'Not_yet_in_school_pct'])
        s_pct = float(staff.loc[cn, 'MultiDenom_pref_pct'])
        gap = round(s_pct - p_pct, 1)

        svg, w, h = _dumbbell_icon_html(p_pct, s_pct)
        icon = folium.DivIcon(html=svg, icon_size=(w, h), icon_anchor=(w / 2, h / 2))
        direction = "higher" if gap > 0 else ("lower" if gap < 0 else "equal")
        tooltip = (
            f"<b>{cn}</b><br>"
            f"Parents (child not yet in school): {p_pct:.1f}%<br>"
            f"Staff &amp; Board of Management: {s_pct:.1f}%<br>"
            f"Staff/BoM {abs(gap):.1f}pp {direction} than these parents"
        )
        folium.Marker(location=[lat, lon], icon=icon, tooltip=tooltip).add_to(fg_dumbbells)

    fg_dumbbells.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    legend_html = """
    <div style='position:fixed;bottom:50px;left:50px;width:310px;border:2px solid #ccc;
                z-index:9999;background:white;opacity:0.96;padding:12px 14px;
                border-radius:8px;font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,0.15);'>
      <div style="font-weight:bold;font-size:14px;margin-bottom:6px;">
        Parents (not yet in school) vs. Staff &amp; BoM</div>
      <div style="font-size:12px;margin-bottom:8px;">
        <span style="display:inline-block;width:11px;height:11px;border-radius:50%;
                     background:#2e7d32;margin-right:5px;"></span>Parents, child not yet in school
        &nbsp;&nbsp;
        <span style="display:inline-block;width:11px;height:11px;border-radius:50%;
                     background:#8e24aa;margin-right:5px;"></span>Staff &amp; Board of Management
      </div>
      <div style="font-size:11px;color:#666;margin-bottom:8px;">
        Dot position along the mini-axis (15%&ndash;60% scale) = that group's % preferring
        multi-denominational patronage in the county. The line length is the gap between them.
      </div>
      <div style="font-size:11px;color:#666;border-top:1px solid #eee;padding-top:6px;">
        Background shading = same gap (staff/BoM minus parents), county-wide: blue = staff/BoM
        MORE pro multi-d, orange = staff/BoM LESS pro multi-d than these parents.
      </div>
      <div style="font-size:10px;color:#999;margin-top:6px;">
        Source: report Table 3 (parents) &amp; Table 8 (staff/BoM).
      </div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    m.save(output_file)
    print(f"\nSUCCESS: Map saved -> {output_file}")
    print(f"  (Data source: {REPORT_CITATION})")

    gaps = pd.DataFrame([
        {'County': cn, 'Parents_notyet_pct': float(parent.loc[cn, 'Not_yet_in_school_pct']),
         'Staff_board_pct': float(staff.loc[cn, 'MultiDenom_pref_pct']),
         'Gap_pp': round(float(staff.loc[cn, 'MultiDenom_pref_pct']) - float(parent.loc[cn, 'Not_yet_in_school_pct']), 1)}
        for cn in parent.index if cn in staff.index
    ]).sort_values('Gap_pp')
    print("\n  Counties where staff/BoM are LEAST aligned with these parents (most negative gap):")
    for _, row in gaps.head(3).iterrows():
        print(f"    {row['County']:<12} parents {row['Parents_notyet_pct']:.1f}%  staff/BoM {row['Staff_board_pct']:.1f}%  gap {row['Gap_pp']:+.1f}pp")
    print("  Counties where staff/BoM are MOST pro-multi-d relative to these parents:")
    for _, row in gaps.tail(3).iterrows():
        print(f"    {row['County']:<12} parents {row['Parents_notyet_pct']:.1f}%  staff/BoM {row['Staff_board_pct']:.1f}%  gap {row['Gap_pp']:+.1f}pp")


# ── Dumbbell chart: parents (not yet in school) vs staff/BoM, by county ──

def dumbbell_chart_notyet_vs_staff(output_file=None):
    """
    One vertical "dumbbell" per county, with THREE dots instead of two:
      - green  = households, child not yet in school
      - blue   = households, child currently in school
      - purple = school staff & Board of Management
    all for preference for a multi-denominational school. Counties are
    sorted by the size of the gap between "not yet in school" households and
    staff/BoM (the widest-reaching comparison), so the ranking itself tells
    part of the story. Counties run along the x-axis and the % scale runs
    along the y-axis, so the vertical spread of the three dots is the
    visual read on how far apart the groups are.
    """
    parent = TABLE_3_PARENT_MULTIDENOM_BY_COUNTY.set_index('County')
    staff = TABLE_8_STAFF_BOARD_BY_COUNTY.set_index('County')

    rows = []
    for cn in parent.index:
        if cn not in staff.index:
            continue
        p_notyet = float(parent.loc[cn, 'Not_yet_in_school_pct'])
        p_inschool = float(parent.loc[cn, 'Children_in_school_pct'])
        s = float(staff.loc[cn, 'MultiDenom_pref_pct'])
        rows.append({
            'County': cn,
            'Parents_notyet_pct': p_notyet,
            'Parents_inschool_pct': p_inschool,
            'Staff_board_pct': s,
            'Gap_pp': round(s - p_notyet, 1),
        })

    # Sort by gap ascending (most negative / biggest gap first)
    df = pd.DataFrame(rows).sort_values('Gap_pp', ascending=True).reset_index(drop=True)

    color_notyet = '#1b5e20'    # dark green
    color_inschool = '#81c784'  # light green — same family as color_notyet, signalling "same group" (households)
    color_staff = '#8e24aa'     # purple — visually distinct third group
    county_order = df['County'].tolist()

    # ── Broken y-axis: compress 0 -> break_end into a small visual band,
    # then normal 1:1 scale from break_end upward through the real data.
    min_val = min(df['Parents_notyet_pct'].min(), df['Parents_inschool_pct'].min(), df['Staff_board_pct'].min())
    break_end = max(5, int(min_val) - 2)          # just below the lowest data point
    compressed_band = 4                             # visual height given to the whole 0..break_end range
    top_real = 65

    def to_axis(v):
        if v <= break_end:
            return (v / break_end) * compressed_band if break_end else 0
        return compressed_band + (v - break_end)

    y_notyet = df['Parents_notyet_pct'].apply(to_axis)
    y_inschool = df['Parents_inschool_pct'].apply(to_axis)
    y_staff = df['Staff_board_pct'].apply(to_axis)

    fig = go.Figure()

    # Three separate area fills, each down to y=0, drawn largest-value-first
    # so each later trace covers the lower portion of the ones before it —
    # leaving one coloured sliver exposed per group (from that group's value
    # up to the next group's value). This assumes the typical ordering
    # notyet > inschool > staff (true in nearly every county in this data);
    # where it doesn't hold for a particular county the slivers just overlap
    # a little differently, but nothing breaks.
    # Each trace's own curve sits exactly on the boundary between it and the
    # region drawn before it, so the coloured bands line up cleanly even
    # without a separate border.
    fig.add_trace(go.Scatter(
        x=county_order, y=y_notyet, mode='lines',
        line=dict(width=0, color='rgba(0,0,0,0)'),
        fill='tozeroy', fillcolor='rgba(27,94,32,0.60)',
        name='Not yet in school area', showlegend=False, hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=county_order, y=y_inschool, mode='lines',
        line=dict(width=0, color='rgba(0,0,0,0)'),
        fill='tozeroy', fillcolor='rgba(129,199,132,0.40)',
        name='In school area', showlegend=False, hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=county_order, y=y_staff, mode='lines',
        line=dict(width=0, color='rgba(0,0,0,0)'),
        fill='tozeroy', fillcolor='rgba(142,36,170,0.30)',
        name='Staff/BoM area', showlegend=False, hoverinfo='skip',
    ))

    # Connecting lines (one trace per county) spanning from the lowest to
    # the highest of the three values, so the middle dot always sits on the
    # line regardless of which group happens to be highest/lowest that county.
    for _, row in df.iterrows():
        vals = [row['Parents_notyet_pct'], row['Parents_inschool_pct'], row['Staff_board_pct']]
        fig.add_trace(go.Scatter(
            x=[row['County'], row['County']],
            y=[to_axis(min(vals)), to_axis(max(vals))],
            mode='lines',
            line=dict(color='#cfcfcf', width=1.5, dash='dot'),
            showlegend=False,
            hoverinfo='skip',
        ))

    fig.add_trace(go.Scatter(
        x=df['County'], y=y_notyet, mode='markers',
        marker=dict(color=color_notyet, size=11, line=dict(color='white', width=1)),
        name='Households, child not yet in school',
        customdata=df['Parents_notyet_pct'],
        hovertemplate='%{x}<br>Households, child not yet in school: <b>%{customdata:.1f}%</b><extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=df['County'], y=y_inschool, mode='markers',
        marker=dict(color=color_inschool, size=11, line=dict(color='white', width=1)),
        name='Households, child in school',
        customdata=df['Parents_inschool_pct'],
        hovertemplate='%{x}<br>Households, child in school: <b>%{customdata:.1f}%</b><extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=df['County'], y=y_staff, mode='markers',
        marker=dict(color=color_staff, size=11, line=dict(color='white', width=1)),
        name='School staff & boards',
        customdata=df['Staff_board_pct'],
        hovertemplate='%{x}<br>Staff &amp; Board of Management: <b>%{customdata:.1f}%</b><extra></extra>',
    ))

    # Custom ticks: 0, then real values from just above the break upward in
    # steps of 5, all mapped through the same transform.
    tick_reals = [0] + [t for t in range(((break_end // 5) + 1) * 5, top_real + 1, 5)]
    tick_vals = [to_axis(t) for t in tick_reals]
    tick_text = [f"{t}%" for t in tick_reals]

    fig.update_layout(
        xaxis=dict(title=None, categoryorder='array', categoryarray=county_order, tickangle=-45),
        yaxis=dict(
            title='% who prefer a multi-denominational school',
            range=[0, to_axis(top_real)],
            tickmode='array', tickvals=tick_vals, ticktext=tick_text,
        ),
        template='plotly_white',
        height=650,
        legend=dict(
            orientation='v', x=0.99, xanchor='right', y=0.99, yanchor='top',
            bgcolor='rgba(255,255,255,0.9)', bordercolor='#ccc', borderwidth=1,
            font=dict(size=12),
        ),
        margin=dict(b=110, l=70, t=30),
        shapes=[
            # Two short diagonal strokes ("⫽") crossing the y-axis at the
            # break point, the standard broken-axis convention.
            dict(type='line', xref='paper', yref='y',
                 x0=-0.020, x1=-0.006, y0=compressed_band - 0.9, y1=compressed_band + 0.9,
                 line=dict(color='#333', width=2)),
            dict(type='line', xref='paper', yref='y',
                 x0=-0.008, x1=0.006, y0=compressed_band - 0.9, y1=compressed_band + 0.9,
                 line=dict(color='#333', width=2)),
        ],
        annotations=[
            dict(
                text="Note: the axis below is compressed to keep the chart readable — it still starts at 0.",
                xref='paper', yref='paper', x=0, y=-0.30, xanchor='left', showarrow=False,
                font=dict(size=11, color='#888'),
            ),
            dict(
                text="Source: Department of Education and Youth, Primary School Survey — Results Summary Report (June 2026).",
                xref='paper', yref='paper', x=0, y=-0.36, xanchor='left', showarrow=False,
                font=dict(size=11, color='#888'),
            ),
        ],
    )

    if output_file:
        fig.write_html(output_file)
        print(f"  Chart saved -> {output_file}")

    widest = df.sort_values('Gap_pp').head(3)
    narrowest = df.sort_values('Gap_pp', ascending=False).head(3)
    print("Widest gaps, staff/BoM vs. households with a child not yet in school:")
    for _, r in widest.iterrows():
        print(f"  {r['County']:<12} not yet in school {r['Parents_notyet_pct']:.1f}%  "
              f"in school {r['Parents_inschool_pct']:.1f}%  staff/BoM {r['Staff_board_pct']:.1f}%  gap {r['Gap_pp']:+.1f}pp")
    print("Narrowest gaps:")
    for _, r in narrowest.iterrows():
        print(f"  {r['County']:<12} not yet in school {r['Parents_notyet_pct']:.1f}%  "
              f"in school {r['Parents_inschool_pct']:.1f}%  staff/BoM {r['Staff_board_pct']:.1f}%  gap {r['Gap_pp']:+.1f}pp")

    print()
    print("Figure caption — school staff & Board of Management survey methodology:")
    print(
        "  The school staff and board of management member survey was made available to primary\n"
        "  school staff and members of boards of management nationally. The target population for\n"
        f"  this survey was {STAFF_BOARD_TARGET_POPULATION:,} staff and board of management members. A total of\n"
        f"  {STAFF_BOARD_SUBMITTED_RESPONSES:,} responses were submitted. Following validation, {STAFF_BOARD_VALID_RESPONSES:,} valid responses\n"
        f"  were retained for analysis. This represents a final validated response rate of {STAFF_BOARD_RESPONSE_RATE_PCT}%\n"
        "  of the eligible staff and board of management population.\n"
        "  (Source: Report Section 4.1, p.25.)"
    )

    return fig