"""
plot_survey_geospatial.py
─────────────────────────
Geospatial visualisation functions for the Irish Primary School Patronage Survey.

Functions
---------
  patronage_multid_preference       – green/blue split: multi-d vs denom majority
  current_vs_preference_multid      – red/blue: current config vs majority preference
  multid_preference_gradient        – continuous green gradient by % wanting multi-d
  gap_map                           – how far multi-d demand exceeds current reality
  proportional_circle_map           – dot SIZE = number of parents wanting multi-d
  county_choropleth                 – county shading by avg % wanting multi-d
  demand_heatmap                    – heatmap of multi-d demand intensity

All functions share the same signature:
    fn(input_file, output_file, coords_file=None)

The coordinates dataset (Data_on_Individual_Schools_Mainstream_2024_25.xlsx) is
expected in the same folder as input_file. Override with coords_file= if needed.
"""

import os
import json
import urllib.request
import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap

# ── Shared constants ──────────────────────────────────────────────────────────

IRELAND_CENTER  = [53.5, -8.0]
MAP_ZOOM        = 7
COORDS_FILENAME = 'Data_on_Individual_Schools_Mainstream_2024_25.xlsx'

ROLL_COL      = 'Roll Number'
NAME_COL      = 'Official School Name'
COUNTY_COL    = 'County'
ETHOS_COL     = 'Ethos'
PATRON_COL    = 'Patron'
LANGUAGE_COL  = 'Language'
LAT_COL       = 'School Latitude'
LON_COL       = 'School Longitude'

VALIDATED_IN  = 'Validated responses from parents with children in primary school'
VALIDATED_NOT = 'Validated responses from parents of children not yet in school'
HOUSEHOLDS    = 'Households associated with the current pupils'
RESP_RATE     = 'Response rate from parents with children in primary school'
MARGIN_ERR    = 'Overall margin of error associated with the current pupils'

MULTI_IN_N    = 'Preference for multi-denominational from parents with children in primary school'
MULTI_NOT_N   = 'Preference for multi-denominational from parents of children not yet in school'
MULTI_IN_PCT  = 'Preference for multi-denominational from parents with children in primary school (%)'
MULTI_NOT_PCT = 'Preference for multi-denominational from parents of children not yet in school (%)'

DENOM_IN_N    = 'Preference for denominational from parents with children in primary school'
DENOM_NOT_N   = 'Preference for denominational from parents of children not yet in school'
DENOM_IN_PCT  = 'Preference for denominational from parents with children in primary school (%)'
DENOM_NOT_PCT = 'Preference for denominational from parents of children not yet in school (%)'

COED_IN_PCT   = 'Preference for co-educational from parents with children in primary school (%)'
IRISH_IN_PCT  = 'Preference for Irish from parents with children in primary school (%)'

# Name mapping from Natural Earth -> survey county names
_NE_NAME_MAP = {
    'Laoighis':                  'Laois',
    'North Tipperary':           'Tipperary',
    'South Tipperary':           'Tipperary',
    'Dún Laoghaire–Rathdown':   'Dublin',
    'Fingal':                    'Dublin',
    'South Dublin':              'Dublin',
}

_COUNTY_GEOJSON_URL = (
    'https://raw.githubusercontent.com/nvkelso/natural-earth-vector'
    '/master/geojson/ne_10m_admin_1_states_provinces.geojson'
)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _safe_num(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return np.nan


def _fmt_pct(val, scale=1.0):
    v = _safe_num(val)
    return 'N/A' if np.isnan(v) else f"{v * scale:.1f}%"


def _fmt_int(val):
    v = _safe_num(val)
    return 'N/A' if np.isnan(v) else str(int(v))


def _clean_str(val):
    s = str(val).strip()
    return '' if s in ('nan', 'None', '-') else s


def _green(pct):
    """0% -> very light green, 100% -> dark green."""
    pct = max(0, min(100, pct))
    r = int(232 - (232 - 27)  * pct / 100)
    g = int(245 - (245 - 94)  * pct / 100)
    b = int(233 - (233 - 32)  * pct / 100)
    return f'#{r:02x}{g:02x}{b:02x}'


def _load_and_merge(input_file, coords_file=None):
    """
    Full outer join of survey results + coordinates datasets.
    Adds '_data_status': 'ok' | 'low_response' | 'no_survey' | 'no_coords'
    and pre-computes multid_pct, denom_pct, _multi_votes, _denom_votes, _total_valid.
    Rows with no coordinates are dropped.
    """
    results = pd.read_excel(input_file, sheet_name=0)
    results = results[results[ROLL_COL].notna()].copy()
    results[ROLL_COL] = results[ROLL_COL].astype(str).str.strip().str.upper()
    results['_in_survey'] = True

    if coords_file is None:
        coords_file = os.path.join(os.path.dirname(os.path.abspath(input_file)),
                                   COORDS_FILENAME)
    coords = pd.read_excel(coords_file, sheet_name='Mainstream Schools', header=1)
    coords.columns = coords.columns.str.strip()
    coords = coords[coords[ROLL_COL].notna()].copy()
    coords[ROLL_COL] = coords[ROLL_COL].astype(str).str.strip().str.upper()
    coords['_in_coords'] = True
    coords = coords.rename(columns={
        'Official Name':      '_c_name',
        'County Description': '_c_county',
        'Ethos Description':  '_c_ethos',
        'Patron':             '_c_patron',
    })

    df = results.merge(
        coords[[ROLL_COL, '_in_coords', LAT_COL, LON_COL,
                '_c_name', '_c_county', '_c_ethos', '_c_patron']],
        on=ROLL_COL, how='outer'
    )
    df['_in_survey'] = df['_in_survey'].fillna(False)
    df['_in_coords'] = df['_in_coords'].fillna(False)

    df[NAME_COL]   = df[NAME_COL].fillna(df['_c_name'])
    df[COUNTY_COL] = df[COUNTY_COL].fillna(df['_c_county'])
    df[ETHOS_COL]  = df[ETHOS_COL].fillna(df['_c_ethos'])
    df[PATRON_COL] = df[PATRON_COL].fillna(df['_c_patron'])

    def _status(row):
        if not row['_in_coords']:  return 'no_coords'
        if not row['_in_survey']:  return 'no_survey'
        return 'ok' if not np.isnan(_safe_num(row.get(VALIDATED_IN))) else 'low_response'

    df['_data_status'] = df.apply(_status, axis=1)

    no_coords_n = (df['_data_status'] == 'no_coords').sum()
    if no_coords_n:
        print(f"  i  {no_coords_n} schools excluded from map (no coordinates)")
    df = df[df['_data_status'] != 'no_coords'].dropna(subset=[LAT_COL, LON_COL]).copy()

    # Pre-compute combined vote totals
    for col in [MULTI_IN_N, MULTI_NOT_N, DENOM_IN_N, DENOM_NOT_N, VALIDATED_IN, VALIDATED_NOT]:
        df[f'_{col}'] = df[col].apply(_safe_num) if col in df.columns else np.nan

    df['_total_valid'] = df[[f'_{VALIDATED_IN}', f'_{VALIDATED_NOT}']].sum(axis=1, min_count=1)
    df['_multi_votes'] = df[[f'_{MULTI_IN_N}',   f'_{MULTI_NOT_N}']].sum(axis=1, min_count=1)
    df['_denom_votes'] = df[[f'_{DENOM_IN_N}',   f'_{DENOM_NOT_N}']].sum(axis=1, min_count=1)
    df['multid_pct']   = (df['_multi_votes'] / df['_total_valid'] * 100).round(1)
    df['denom_pct']    = (df['_denom_votes'] / df['_total_valid'] * 100).round(1)

    return df


def _save(m, output_file):
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    m.save(output_file)
    print(f"  Map saved -> {output_file}")


def _popup_full(row, color, df):
    """Build the full-detail HTML popup for a school with survey data."""
    school_name   = _clean_str(row.get(NAME_COL, '')) or 'Unknown'
    county        = _clean_str(row.get(COUNTY_COL, ''))
    ethos         = _clean_str(row.get(ETHOS_COL, ''))
    patron        = _clean_str(row.get(PATRON_COL, ''))
    language      = _clean_str(row.get(LANGUAGE_COL, '')) if LANGUAGE_COL in df.columns else ''
    households    = _fmt_int(row.get(HOUSEHOLDS))
    resp_rate_str = _fmt_pct(row.get(RESP_RATE),     scale=100)
    margin_str    = _fmt_pct(row.get(MARGIN_ERR),    scale=100)
    multi_in_pct  = _fmt_pct(row.get(MULTI_IN_PCT),  scale=100)
    multi_not_pct = _fmt_pct(row.get(MULTI_NOT_PCT), scale=100)
    denom_in_pct  = _fmt_pct(row.get(DENOM_IN_PCT),  scale=100)
    denom_not_pct = _fmt_pct(row.get(DENOM_NOT_PCT), scale=100)
    coed_in_pct   = _fmt_pct(row.get(COED_IN_PCT),   scale=100)
    irish_in_pct  = _fmt_pct(row.get(IRISH_IN_PCT),  scale=100)
    multi_in_n    = _fmt_int(row.get(MULTI_IN_N))
    multi_not_n   = _fmt_int(row.get(MULTI_NOT_N))
    denom_in_n    = _fmt_int(row.get(DENOM_IN_N))
    denom_not_n   = _fmt_int(row.get(DENOM_NOT_N))
    valid_in_n    = _fmt_int(row.get(VALIDATED_IN))
    valid_not_n   = _fmt_int(row.get(VALIDATED_NOT))
    multid_c      = f"{row['multid_pct']:.1f}%" if not pd.isna(row['multid_pct']) else 'N/A'
    denom_c       = f"{row['denom_pct']:.1f}%"  if not pd.isna(row['denom_pct'])  else 'N/A'

    def sec(t):
        return f'<tr style="background:#f0f0f0"><td colspan="3" style="padding:5px 6px;font-weight:bold;color:#333;">{t}</td></tr>'
    def dr(label, val, extra='', bg=''):
        s = f'background:{bg};' if bg else ''
        return (f'<tr style="{s}"><td style="padding:2px 6px;color:#555;">{label}</td>'
                f'<td style="padding:2px 6px;text-align:right;">{val}</td>'
                f'<td style="padding:2px 6px;text-align:right;color:#888;font-size:11px;">{extra}</td></tr>')

    return f"""
    <div style="font-family:sans-serif;font-size:13px;min-width:290px;max-width:350px;">
      <div style="background:{color};color:white;padding:8px 10px;border-radius:4px 4px 0 0;margin:-1px -1px 8px -1px;">
        <strong style="font-size:14px;">{school_name}</strong><br>
        <span style="font-size:12px;opacity:0.9;">{county}{' · ' + ethos if ethos else ''}</span>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        {sec("Combined preference (in-school + not-yet-in-school)")}
        {dr("Multi-denominational", f"<strong style='color:#27ae60'>{multid_c}</strong>",
            f"{_fmt_int(row['_multi_votes'])} / {_fmt_int(row['_total_valid'])} responses")}
        {dr("Denominational", f"<strong style='color:#2980b9'>{denom_c}</strong>",
            f"{_fmt_int(row['_denom_votes'])} / {_fmt_int(row['_total_valid'])} responses", '#f9f9f9')}
        {sec(f"Parents with children currently in school ({valid_in_n} responses)")}
        {dr("Multi-denominational", multi_in_pct, f"{multi_in_n} votes")}
        {dr("Denominational",       denom_in_pct, f"{denom_in_n} votes", '#f9f9f9')}
        {dr("Co-educational",        coed_in_pct)}
        {dr("Irish medium",           irish_in_pct, bg='#f9f9f9')}
        {sec(f"Parents with children not yet in school ({valid_not_n} responses)")}
        {dr("Multi-denominational", multi_not_pct, f"{multi_not_n} votes")}
        {dr("Denominational",       denom_not_pct, f"{denom_not_n} votes", '#f9f9f9')}
        {sec("Survey quality")}
        {dr("Households surveyed", households)}
        {dr("Response rate",       resp_rate_str, bg='#f9f9f9')}
        {dr("Margin of error",     f"+/-{margin_str}")}
        {sec("School info")}
        {dr("Current ethos", ethos)}
        {dr("Patron", f"<span style='font-size:11px'>{patron}</span>", bg='#f9f9f9')}
        {dr("Language", language)}
      </table>
    </div>"""


def _popup_nodata(row, color, reason_title, reason_body):
    """Popup for schools with no reportable data."""
    school_name = _clean_str(row.get(NAME_COL, '')) or 'Unknown'
    county      = _clean_str(row.get(COUNTY_COL, ''))
    ethos       = _clean_str(row.get(ETHOS_COL, ''))
    patron      = _clean_str(row.get(PATRON_COL, ''))
    households  = _fmt_int(row.get(HOUSEHOLDS))
    return f"""
    <div style="font-family:sans-serif;font-size:13px;min-width:260px;max-width:340px;">
      <div style="background:{color};color:white;padding:8px 10px;border-radius:4px 4px 0 0;margin:-1px -1px 8px -1px;">
        <strong style="font-size:14px;">{school_name}</strong><br>
        <span style="font-size:12px;opacity:0.9;">{county}{' · ' + ethos if ethos else ''}</span>
      </div>
      <div style="background:#f5f5f5;border-left:4px solid {color};padding:8px 10px;margin-bottom:8px;font-size:12px;color:#555;">
        <strong>{reason_title}</strong><br>{reason_body}
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <tr><td style="padding:3px 6px;color:#555;">Households surveyed</td>
            <td style="padding:3px 6px;text-align:right;">{households}</td></tr>
        <tr style="background:#f8f8f8;">
            <td style="padding:3px 6px;color:#555;">Current ethos</td>
            <td style="padding:3px 6px;text-align:right;">{ethos}</td></tr>
        <tr><td style="padding:3px 6px;color:#555;">Patron</td>
            <td style="padding:3px 6px;text-align:right;font-size:11px;">{patron}</td></tr>
        <tr style="background:#f8f8f8;">
            <td style="padding:3px 6px;color:#555;">County</td>
            <td style="padding:3px 6px;text-align:right;">{county}</td></tr>
      </table>
    </div>"""


def _add_legend(m, title, subtitle, rows, extra_items=None):
    """Add a fixed-position legend to a folium map.
    rows: list of (color, label, count) tuples.
    extra_items: list of (color, label) for non-count items.
    """
    row_html = ''.join(
        f'<div style="display:flex;align-items:flex-start;margin-bottom:5px;">'
        f'<div style="width:14px;height:14px;min-width:14px;background:{c};border-radius:50%;'
        f'border:1px solid #999;margin-right:8px;margin-top:2px;"></div>'
        f'<span style="font-size:12px;">{l}'
        f'{"<span style=color:#888;font-size:11px> (" + str(n) + ")</span>" if n is not None else ""}'
        f'</span></div>'
        for c, l, n in rows
    )
    extra_html = ''
    if extra_items:
        extra_html = ''.join(
            f'<div style="display:flex;align-items:center;margin-bottom:4px;">'
            f'<div style="width:14px;height:14px;min-width:14px;background:{c};'
            f'border-radius:50%;border:1px solid #999;margin-right:8px;"></div>'
            f'<span style="font-size:12px;">{l}</span></div>'
            for c, l in extra_items
        )
    legend_html = f"""
    <div style='position:fixed;bottom:50px;left:50px;width:310px;border:2px solid #ccc;
                z-index:9999;background:white;opacity:0.95;padding:12px 14px;
                border-radius:8px;font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,0.15);'>
      <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">{title}</div>
      <div style="font-size:11px;color:#666;margin-bottom:10px;border-bottom:1px solid #eee;padding-bottom:6px;">{subtitle}</div>
      {row_html}{extra_html}
      <div style="margin-top:8px;font-size:11px;color:#888;border-top:1px solid #eee;padding-top:6px;">
        Click a dot for full detail &nbsp;|&nbsp; Layer control (top right) to toggle
      </div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))


# ── Visualisation 1 ──────────────────────────────────────────────────────────

def patronage_multid_preference(input_file, output_file, coords_file=None):
    """Green/blue split: schools where multi-d vs denominational has majority preference."""
    df = _load_and_merge(input_file, coords_file)

    COLORS = {'multid':'#2ecc71','denom':'#3498db','tied':'#9b59b6',
              'low_response':'#95a5a6','no_survey':'#e67e22'}
    LABELS = {'multid':'Multi-d majority (>50%)','denom':'Denominational majority (>50%)',
              'tied':'Tied (50%/50%)','low_response':'Response rate too low to report',
              'no_survey':'Not included in survey'}

    def _cat(row):
        if row['_data_status'] == 'low_response': return 'low_response'
        if row['_data_status'] == 'no_survey':    return 'no_survey'
        m, d = row['multid_pct'], row['denom_pct']
        if pd.isna(m) or pd.isna(d): return 'low_response'
        if m > 50: return 'multid'
        if d > 50: return 'denom'
        return 'tied'
    df['category'] = df.apply(_cat, axis=1)

    m = folium.Map(location=IRELAND_CENTER, zoom_start=MAP_ZOOM, tiles='cartodbpositron', control_scale=True)
    layers = {c: folium.FeatureGroup(name=LABELS[c], show=True).add_to(m) for c in COLORS}

    for _, row in df.iterrows():
        cat, color = row['category'], COLORS[row['category']]
        sn = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        pct = f"{row['multid_pct']:.1f}%" if not pd.isna(row['multid_pct']) else 'N/A'
        dp  = f"{row['denom_pct']:.1f}%"  if not pd.isna(row['denom_pct'])  else 'N/A'
        if cat == 'low_response':
            html = _popup_nodata(row, color, 'Response rate too low to report',
                'Responses were insufficient to report reliable figures without risking '
                'disproportionate distortion. Still included in county and national totals.')
            tip = f"{sn} | Response rate too low to report"
        elif cat == 'no_survey':
            html = _popup_nodata(row, color, 'Not included in this survey',
                'This school appears in the register but was not part of the patronage '
                'preference survey — it may have opened, closed, or merged between datasets.')
            tip = f"{sn} | Not included in survey"
        else:
            html = _popup_full(row, color, df)
            tip  = f"{sn} | Multi-d: {pct} | Denom: {dp}"
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=400,
                      popup=folium.Popup(html, max_width=370), tooltip=tip,
                      color=color, fill=True, fill_color=color, fill_opacity=0.8, weight=1
                      ).add_to(layers[cat])

    counts = df['category'].value_counts()
    folium.LayerControl(collapsed=False).add_to(m)
    _add_legend(m, 'Patronage Preference',
                'Combined: parents in school + not yet in school',
                [(COLORS[c], LABELS[c], counts.get(c,0)) for c in COLORS])
    _save(m, output_file)
    print(f"\n  Schools on map: {len(df)}")
    for c, l in LABELS.items(): print(f"    {l}: {counts.get(c,0)}")


# ── Visualisation 2 ──────────────────────────────────────────────────────────

def current_vs_preference_multid(input_file, output_file, coords_file=None):
    """
    Red/blue: currently multi-d schools vs currently denominational schools
    where a majority (>=50%) want multi-d. Excludes schools where the majority
    want to remain denominational.
    """
    df = _load_and_merge(input_file, coords_file)

    COLORS = {'currently_multid':'#e74c3c','wants_multid':'#2471a3',
              'low_response':'#95a5a6','no_survey':'#e67e22'}
    LABELS = {'currently_multid':'Currently multi-denominational',
              'wants_multid':'Currently denominational — majority want multi-d (≥50%)',
              'low_response':'Response rate too low to report',
              'no_survey':'Not included in survey'}

    def _cat(row):
        if row['_data_status'] == 'low_response': return 'low_response'
        if row['_data_status'] == 'no_survey':    return 'no_survey'
        is_multid = 'multi' in _clean_str(row.get(ETHOS_COL,'')).lower()
        m = row['multid_pct']
        wants = (not pd.isna(m)) and (m >= 50)
        if is_multid:  return 'currently_multid'
        if wants:      return 'wants_multid'
        return 'exclude'
    df['category'] = df.apply(_cat, axis=1)

    excluded = (df['category'] == 'exclude').sum()
    df = df[df['category'] != 'exclude'].copy()
    print(f"  i  {excluded} schools not shown (denom, majority want to stay denom)")

    m = folium.Map(location=IRELAND_CENTER, zoom_start=MAP_ZOOM, tiles='cartodbpositron', control_scale=True)
    layers = {c: folium.FeatureGroup(name=LABELS[c], show=True).add_to(m) for c in COLORS}

    for _, row in df.iterrows():
        cat, color = row['category'], COLORS[row['category']]
        sn  = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        pct = f"{row['multid_pct']:.1f}%" if not pd.isna(row['multid_pct']) else 'N/A'
        if cat == 'low_response':
            html = _popup_nodata(row, color, 'Response rate too low to report',
                'Responses were insufficient to report reliable figures. '
                'Still included in county and national totals.')
            tip = f"{sn} | Response rate too low to report"
        elif cat == 'no_survey':
            html = _popup_nodata(row, color, 'Not included in this survey',
                'This school appears in the register but was not part of the survey.')
            tip = f"{sn} | Not included in survey"
        else:
            html = _popup_full(row, color, df)
            tip  = f"{sn} | Config: {_clean_str(row.get(ETHOS_COL,''))} | Multi-d preference: {pct}"
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=1500,
                      popup=folium.Popup(html, max_width=370), tooltip=tip,
                      color=color, fill=True, fill_color=color, fill_opacity=0.8, weight=1
                      ).add_to(layers[cat])

    counts = df['category'].value_counts()
    folium.LayerControl(collapsed=False).add_to(m)
    _add_legend(m, 'Current Configuration vs Preference',
                'Preference = combined parents in school + not yet in school',
                [(COLORS[c], LABELS[c], counts.get(c,0)) for c in COLORS])
    _save(m, output_file)
    print(f"\n  Schools on map: {len(df)}")
    for c, l in LABELS.items(): print(f"    {l}: {counts.get(c,0)}")


# ── Visualisation 3 ──────────────────────────────────────────────────────────

def multid_preference_gradient(input_file, output_file, coords_file=None):
    """All schools coloured by % wanting multi-d on a white->green gradient."""
    df = _load_and_merge(input_file, coords_file)

    m = folium.Map(location=IRELAND_CENTER, zoom_start=MAP_ZOOM, tiles='cartodbpositron', control_scale=True)
    layer_data     = folium.FeatureGroup(name='Schools with data', show=True).add_to(m)
    layer_low      = folium.FeatureGroup(name='Response rate too low to report', show=True).add_to(m)
    layer_nosurvey = folium.FeatureGroup(name='Not included in survey', show=True).add_to(m)

    for _, row in df.iterrows():
        status = row['_data_status']
        sn     = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        pct    = row['multid_pct']

        if status == 'no_survey':
            color, target = '#e67e22', layer_nosurvey
            html = _popup_nodata(row, color, 'Not included in this survey',
                'This school appears in the register but was not part of the survey.')
            tip = f"{sn} | Not included in survey"
        elif status == 'low_response':
            color, target = '#95a5a6', layer_low
            html = _popup_nodata(row, color, 'Response rate too low to report',
                'Responses were insufficient to report reliable figures. '
                'Still included in county and national totals.')
            tip = f"{sn} | Response rate too low to report"
        else:
            color  = _green(pct) if not pd.isna(pct) else '#aaaaaa'
            target = layer_data
            html   = _popup_full(row, color, df)
            tip    = f"{sn} | Multi-d preference: {pct:.1f}%" if not pd.isna(pct) else f"{sn} | N/A"

        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=1500,
                      popup=folium.Popup(html, max_width=370), tooltip=tip,
                      color=color, fill=True, fill_color=color, fill_opacity=0.85, weight=1
                      ).add_to(target)

    folium.LayerControl(collapsed=False).add_to(m)
    stops = [(p, _green(p)) for p in [0, 25, 50, 75, 100]]
    gradient_html = ''.join(
        f'<div style="display:flex;align-items:center;margin-bottom:3px;">'
        f'<div style="width:18px;height:12px;background:{c};border:1px solid #ccc;margin-right:6px;flex-shrink:0;"></div>'
        f'<span style="font-size:11px;">{p}%</span></div>'
        for p, c in reversed(stops)
    )
    extra = [('#95a5a6','Response rate too low to report'), ('#e67e22','Not included in survey')]
    legend_html = f"""
    <div style='position:fixed;bottom:50px;left:50px;width:280px;border:2px solid #ccc;
                z-index:9999;background:white;opacity:0.95;padding:12px 14px;
                border-radius:8px;font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,0.15);'>
      <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">% Wanting Multi-denominational</div>
      <div style="font-size:11px;color:#666;margin-bottom:10px;border-bottom:1px solid #eee;padding-bottom:6px;">
        Combined: parents in school + not yet in school</div>
      {gradient_html}
      {''.join(f'<div style="display:flex;align-items:center;margin-top:5px;"><div style="width:18px;height:12px;background:{c};border:1px solid #ccc;margin-right:6px;flex-shrink:0;"></div><span style="font-size:11px;">{l}</span></div>' for c,l in extra)}
      <div style="margin-top:8px;font-size:11px;color:#888;border-top:1px solid #eee;padding-top:6px;">
        Click a dot for full detail &nbsp;|&nbsp; Layer control (top right) to toggle</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    _save(m, output_file)
    ok = df[df['_data_status']=='ok']
    print(f"\n  Schools on map: {len(df)} | With data: {len(ok)}")
    print(f"  Multi-d % — Mean: {ok['multid_pct'].mean():.1f}% | Median: {ok['multid_pct'].median():.1f}%")


# ── Visualisation 4: Gap map ──────────────────────────────────────────────────

def gap_map(input_file, output_file, coords_file=None):
    """
    For currently-denominational schools only: colour by how far multi-d
    preference EXCEEDS the current reality (0% multi-d config).
    Essentially just the multi-d preference % for denom schools, but framed
    as 'unmet demand'. Darker = bigger gap between what people want and what exists.
    Only schools currently classed as denominational are shown.
    """
    df = _load_and_merge(input_file, coords_file)

    # Only denominational schools with reportable data
    ok    = df[(df['_data_status'] == 'ok') &
               (~df[ETHOS_COL].astype(str).str.lower().str.contains('multi'))].copy()
    nodata = df[df['_data_status'].isin(['low_response','no_survey'])].copy()

    m = folium.Map(location=IRELAND_CENTER, zoom_start=MAP_ZOOM, tiles='cartodbpositron', control_scale=True)
    layer_gap  = folium.FeatureGroup(name='Denominational schools (sized by unmet demand)', show=True).add_to(m)
    layer_low  = folium.FeatureGroup(name='Response rate too low to report', show=True).add_to(m)
    layer_ns   = folium.FeatureGroup(name='Not included in survey', show=True).add_to(m)

    for _, row in ok.iterrows():
        pct   = row['multid_pct']
        color = _green(pct) if not pd.isna(pct) else '#aaaaaa'
        sn    = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        html  = _popup_full(row, color, df)
        tip   = f"{sn} | Unmet multi-d demand: {pct:.1f}%" if not pd.isna(pct) else sn
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=400,
                      popup=folium.Popup(html, max_width=370), tooltip=tip,
                      color=color, fill=True, fill_color=color, fill_opacity=0.85, weight=1
                      ).add_to(layer_gap)

    for _, row in nodata.iterrows():
        status = row['_data_status']
        color  = '#95a5a6' if status == 'low_response' else '#e67e22'
        target = layer_low if status == 'low_response' else layer_ns
        sn     = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        title  = 'Response rate too low to report' if status == 'low_response' else 'Not included in survey'
        body   = ('Responses insufficient to report reliable figures.' if status == 'low_response'
                  else 'School appears in register but not in survey dataset.')
        html   = _popup_nodata(row, color, title, body)
        tip    = f"{sn} | {title}"
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=400,
                      popup=folium.Popup(html, max_width=370), tooltip=tip,
                      color=color, fill=True, fill_color=color, fill_opacity=0.7, weight=1
                      ).add_to(target)

    folium.LayerControl(collapsed=False).add_to(m)
    stops = [(p, _green(p)) for p in [0, 25, 50, 75, 100]]
    gradient_html = ''.join(
        f'<div style="display:flex;align-items:center;margin-bottom:3px;">'
        f'<div style="width:18px;height:12px;background:{c};border:1px solid #ccc;margin-right:6px;flex-shrink:0;"></div>'
        f'<span style="font-size:11px;">{p}% want multi-d</span></div>'
        for p, c in reversed(stops)
    )
    legend_html = f"""
    <div style='position:fixed;bottom:50px;left:50px;width:280px;border:2px solid #ccc;
                z-index:9999;background:white;opacity:0.95;padding:12px 14px;
                border-radius:8px;font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,0.15);'>
      <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">Unmet Demand for Multi-d Education</div>
      <div style="font-size:11px;color:#666;margin-bottom:10px;border-bottom:1px solid #eee;padding-bottom:6px;">
        Currently-denominational schools only.<br>
        Darker green = stronger unmet demand for multi-d.</div>
      {gradient_html}
      <div style="display:flex;align-items:center;margin-top:5px;">
        <div style="width:18px;height:12px;background:#95a5a6;border:1px solid #ccc;margin-right:6px;flex-shrink:0;"></div>
        <span style="font-size:11px;">Response rate too low to report</span></div>
      <div style="display:flex;align-items:center;margin-top:4px;">
        <div style="width:18px;height:12px;background:#e67e22;border:1px solid #ccc;margin-right:6px;flex-shrink:0;"></div>
        <span style="font-size:11px;">Not included in survey</span></div>
      <div style="margin-top:8px;font-size:11px;color:#888;border-top:1px solid #eee;padding-top:6px;">
        Click a dot for full detail</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    _save(m, output_file)
    print(f"\n  Denominational schools shown: {len(ok)}")
    print(f"  Avg unmet multi-d demand: {ok['multid_pct'].mean():.1f}%")
    print(f"  Schools where >50% want multi-d: {(ok['multid_pct'] >= 50).sum()}")


# ── Visualisation 5: Proportional circle map ─────────────────────────────────

def proportional_circle_map(input_file, output_file, coords_file=None):
    """
    Dot SIZE proportional to the raw number of parents wanting multi-d education
    (in-school + not-yet-in-school combined). Colour = currently multi-d (red)
    vs currently denominational (blue). Makes the volume of unmet demand visible.
    """
    df = _load_and_merge(input_file, coords_file)
    ok = df[df['_data_status'] == 'ok'].copy()

    max_votes = ok['_multi_votes'].max()
    MIN_R, MAX_R = 200, 3000

    def _radius(votes):
        if pd.isna(votes) or votes == 0:
            return MIN_R
        return MIN_R + (votes / max_votes) ** 0.5 * (MAX_R - MIN_R)

    m = folium.Map(location=IRELAND_CENTER, zoom_start=MAP_ZOOM, tiles='cartodbpositron', control_scale=True)
    layer_multid = folium.FeatureGroup(name='Currently multi-denominational', show=True).add_to(m)
    layer_denom  = folium.FeatureGroup(name='Currently denominational', show=True).add_to(m)
    layer_low    = folium.FeatureGroup(name='Response rate too low to report', show=True).add_to(m)
    layer_ns     = folium.FeatureGroup(name='Not included in survey', show=True).add_to(m)

    # No-data schools as small fixed dots
    for _, row in df[df['_data_status'] == 'low_response'].iterrows():
        sn = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=200,
                      popup=folium.Popup(_popup_nodata(row,'#95a5a6','Response rate too low to report',
                          'Responses insufficient to report reliable figures.'), max_width=340),
                      tooltip=f"{sn} | Response rate too low",
                      color='#95a5a6', fill=True, fill_color='#95a5a6', fill_opacity=0.5, weight=1
                      ).add_to(layer_low)
    for _, row in df[df['_data_status'] == 'no_survey'].iterrows():
        sn = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=200,
                      popup=folium.Popup(_popup_nodata(row,'#e67e22','Not included in survey',
                          'School appears in register but not in survey dataset.'), max_width=340),
                      tooltip=f"{sn} | Not in survey",
                      color='#e67e22', fill=True, fill_color='#e67e22', fill_opacity=0.5, weight=1
                      ).add_to(layer_ns)

    # Data schools — sized by multi-d votes
    for _, row in ok.iterrows():
        ethos   = _clean_str(row.get(ETHOS_COL,''))
        is_multid = 'multi' in ethos.lower()
        color   = '#e74c3c' if is_multid else '#2471a3'
        target  = layer_multid if is_multid else layer_denom
        votes   = row['_multi_votes']
        radius  = _radius(votes)
        sn      = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        pct     = f"{row['multid_pct']:.1f}%" if not pd.isna(row['multid_pct']) else 'N/A'
        html    = _popup_full(row, color, df)
        tip     = f"{sn} | {_fmt_int(votes)} parents want multi-d ({pct})"
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=radius,
                      popup=folium.Popup(html, max_width=370), tooltip=tip,
                      color=color, fill=True, fill_color=color, fill_opacity=0.5, weight=1
                      ).add_to(target)

    folium.LayerControl(collapsed=False).add_to(m)
    legend_html = f"""
    <div style='position:fixed;bottom:50px;left:50px;width:290px;border:2px solid #ccc;
                z-index:9999;background:white;opacity:0.95;padding:12px 14px;
                border-radius:8px;font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,0.15);'>
      <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">Volume of Multi-d Demand</div>
      <div style="font-size:11px;color:#666;margin-bottom:10px;border-bottom:1px solid #eee;padding-bottom:6px;">
        Circle size = number of parents wanting multi-d<br>
        Combined: parents in school + not yet in school</div>
      <div style="display:flex;align-items:center;margin-bottom:5px;">
        <div style="width:20px;height:20px;background:#e74c3c;border-radius:50%;opacity:0.6;margin-right:8px;flex-shrink:0;"></div>
        <span style="font-size:12px;">Currently multi-denominational</span></div>
      <div style="display:flex;align-items:center;margin-bottom:5px;">
        <div style="width:20px;height:20px;background:#2471a3;border-radius:50%;opacity:0.6;margin-right:8px;flex-shrink:0;"></div>
        <span style="font-size:12px;">Currently denominational</span></div>
      <div style="display:flex;align-items:center;margin-bottom:5px;">
        <div style="width:14px;height:14px;background:#95a5a6;border-radius:50%;opacity:0.6;margin-right:8px;flex-shrink:0;"></div>
        <span style="font-size:12px;">Response rate too low to report</span></div>
      <div style="display:flex;align-items:center;margin-bottom:5px;">
        <div style="width:14px;height:14px;background:#e67e22;border-radius:50%;opacity:0.6;margin-right:8px;flex-shrink:0;"></div>
        <span style="font-size:12px;">Not included in survey</span></div>
      <div style="margin-top:8px;font-size:11px;color:#888;border-top:1px solid #eee;padding-top:6px;">
        Click a dot for full detail</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    _save(m, output_file)
    total_demand = int(ok['_multi_votes'].sum())
    print(f"\n  Total parents wanting multi-d: {total_demand:,}")
    print(f"  In currently-denom schools:   {int(ok[~ok[ETHOS_COL].str.lower().str.contains('multi', na=False)]['_multi_votes'].sum()):,}")


# ── Visualisation 6: County choropleth ───────────────────────────────────────

def county_choropleth(input_file, output_file, coords_file=None):
    """
    County-level choropleth shaded by the average % of parents wanting
    multi-d education across all schools in that county.
    """
    df = _load_and_merge(input_file, coords_file)
    ok = df[df['_data_status'] == 'ok'].copy()

    # Aggregate to county level
    county_stats = (ok.groupby(COUNTY_COL)
                      .agg(avg_multid_pct=('multid_pct', 'mean'),
                           n_schools=('multid_pct', 'count'),
                           total_multi_votes=('_multi_votes', 'sum'),
                           total_valid=('_total_valid', 'sum'),
                           n_majority_multid=('multid_pct', lambda x: (x >= 50).sum()))
                      .reset_index())
    county_stats['avg_multid_pct'] = county_stats['avg_multid_pct'].round(1)
    county_stats['weighted_pct']   = (county_stats['total_multi_votes'] /
                                       county_stats['total_valid'] * 100).round(1)

    # Fetch Ireland county GeoJSON from Natural Earth
    print("  Fetching county boundaries...")
    req = urllib.request.Request(_COUNTY_GEOJSON_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        geo = json.loads(r.read())

    ire_features = [f for f in geo['features'] if f['properties'].get('admin') == 'Ireland']
    for f in ire_features:
        raw = f['properties']['name']
        f['properties']['county_norm'] = _NE_NAME_MAP.get(raw, raw)

    county_geo = {'type': 'FeatureCollection', 'features': ire_features}

    # Merge stats into geojson properties for folium
    stats_dict = county_stats.set_index(COUNTY_COL).to_dict('index')
    for f in county_geo['features']:
        cn = f['properties']['county_norm']
        s  = stats_dict.get(cn, {})
        f['properties']['avg_multid_pct']     = s.get('avg_multid_pct', None)
        f['properties']['weighted_pct']        = s.get('weighted_pct', None)
        f['properties']['n_schools']           = s.get('n_schools', 0)
        f['properties']['n_majority_multid']   = s.get('n_majority_multid', 0)
        f['properties']['total_multi_votes']   = int(s.get('total_multi_votes', 0))

    m = folium.Map(location=IRELAND_CENTER, zoom_start=7, tiles='cartodbpositron', control_scale=True)

    def _style(feature):
        pct = feature['properties'].get('weighted_pct')
        if pct is None:
            fill = '#dddddd'
        else:
            fill = _green(pct)
        return {'fillColor': fill, 'color': '#555', 'weight': 1.5,
                'fillOpacity': 0.75, 'opacity': 1}

    def _highlight(feature):
        return {'weight': 3, 'color': '#333', 'fillOpacity': 0.9}

    def _tooltip_fn(feature):
        cn  = feature['properties']['county_norm']
        pct = feature['properties'].get('weighted_pct')
        return f"{cn}: {pct:.1f}% want multi-d" if pct else f"{cn}: no data"

    folium.GeoJson(
        county_geo,
        style_function=_style,
        highlight_function=_highlight,
        tooltip=folium.GeoJsonTooltip(
            fields=['county_norm','weighted_pct','avg_multid_pct',
                    'n_schools','n_majority_multid','total_multi_votes'],
            aliases=['County','Weighted % wanting multi-d','Avg % across schools',
                     'Schools with data','Schools where majority want multi-d',
                     'Total parents wanting multi-d'],
            localize=True, sticky=True
        )
    ).add_to(m)

    # School dots as a toggleable layer
    layer_schools = folium.FeatureGroup(name='Individual schools', show=False).add_to(m)
    for _, row in ok.iterrows():
        pct   = row['multid_pct']
        color = _green(pct) if not pd.isna(pct) else '#aaaaaa'
        sn    = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=300,
                      popup=folium.Popup(_popup_full(row, color, df), max_width=370),
                      tooltip=f"{sn} | {pct:.1f}%" if not pd.isna(pct) else sn,
                      color=color, fill=True, fill_color=color, fill_opacity=0.8, weight=1
                      ).add_to(layer_schools)

    folium.LayerControl(collapsed=False).add_to(m)

    stops = [(p, _green(p)) for p in [0, 25, 50, 75, 100]]
    gradient_html = ''.join(
        f'<div style="display:flex;align-items:center;margin-bottom:3px;">'
        f'<div style="width:20px;height:14px;background:{c};border:1px solid #ccc;margin-right:6px;flex-shrink:0;border-radius:2px;"></div>'
        f'<span style="font-size:11px;">{p}%</span></div>'
        for p, c in reversed(stops)
    )
    legend_html = f"""
    <div style='position:fixed;bottom:50px;left:50px;width:270px;border:2px solid #ccc;
                z-index:9999;background:white;opacity:0.95;padding:12px 14px;
                border-radius:8px;font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,0.15);'>
      <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">% Wanting Multi-d by County</div>
      <div style="font-size:11px;color:#666;margin-bottom:10px;border-bottom:1px solid #eee;padding-bottom:6px;">
        Weighted by validated responses across all schools in county</div>
      {gradient_html}
      <div style="margin-top:8px;font-size:11px;color:#888;border-top:1px solid #eee;padding-top:6px;">
        Hover over a county for detail.<br>
        Toggle individual schools via layer control (top right).</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    _save(m, output_file)
    print(f"\n  County summary (weighted % wanting multi-d):")
    for _, r in county_stats.sort_values('weighted_pct', ascending=False).iterrows():
        print(f"    {r[COUNTY_COL]:<14} {r['weighted_pct']:.1f}%  ({r['n_schools']} schools, "
              f"{r['n_majority_multid']} with majority multi-d preference)")


# ── Visualisation 7: Demand heatmap ─────────────────────────────────────────

def demand_heatmap(input_file, output_file, coords_file=None):
    """
    Heatmap of multi-d demand intensity, weighted by the number of parents
    wanting multi-d at each school location.
    """
    df = _load_and_merge(input_file, coords_file)
    ok = df[df['_data_status'] == 'ok'].copy()

    m = folium.Map(location=IRELAND_CENTER, zoom_start=MAP_ZOOM, tiles='cartodbpositron', control_scale=True)

    # Heatmap weighted by raw vote count
    heat_data = [
        [row[LAT_COL], row[LON_COL], row['_multi_votes']]
        for _, row in ok.iterrows()
        if not pd.isna(row['_multi_votes']) and row['_multi_votes'] > 0
    ]
    HeatMap(heat_data, radius=20, blur=15, min_opacity=0.3,
            gradient={0.2:'#e8f5e9', 0.5:'#4caf50', 0.8:'#1b5e20'}
            ).add_to(m)

    # School dots as toggleable overlay
    layer_schools = folium.FeatureGroup(name='Individual schools', show=False).add_to(m)
    for _, row in ok.iterrows():
        pct   = row['multid_pct']
        color = _green(pct) if not pd.isna(pct) else '#aaaaaa'
        sn    = _clean_str(row.get(NAME_COL,'')) or 'Unknown'
        folium.Circle(location=[row[LAT_COL], row[LON_COL]], radius=300,
                      popup=folium.Popup(_popup_full(row, color, df), max_width=370),
                      tooltip=f"{sn} | {pct:.1f}%" if not pd.isna(pct) else sn,
                      color=color, fill=True, fill_color=color, fill_opacity=0.8, weight=1
                      ).add_to(layer_schools)

    folium.LayerControl(collapsed=False).add_to(m)

    legend_html = """
    <div style='position:fixed;bottom:50px;left:50px;width:270px;border:2px solid #ccc;
                z-index:9999;background:white;opacity:0.95;padding:12px 14px;
                border-radius:8px;font-family:sans-serif;box-shadow:2px 2px 6px rgba(0,0,0,0.15);'>
      <div style="font-weight:bold;font-size:14px;margin-bottom:4px;">Multi-d Demand Heatmap</div>
      <div style="font-size:11px;color:#666;margin-bottom:10px;border-bottom:1px solid #eee;padding-bottom:6px;">
        Heat intensity weighted by number of parents wanting multi-d<br>
        Combined: in school + not yet in school</div>
      <div style="display:flex;align-items:center;height:14px;margin-bottom:6px;">
        <div style="flex:1;height:14px;background:linear-gradient(to right,#e8f5e9,#4caf50,#1b5e20);
                    border:1px solid #ccc;border-radius:2px;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:#666;margin-bottom:6px;">
        <span>Low</span><span>High</span>
      </div>
      <div style="margin-top:4px;font-size:11px;color:#888;border-top:1px solid #eee;padding-top:6px;">
        Toggle individual school dots via layer control (top right)</div>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
    _save(m, output_file)
    total = int(ok['_multi_votes'].sum())
    print(f"\n  Total parents wanting multi-d: {total:,}")
    print(f"  Schools included in heatmap: {len(heat_data)}")
