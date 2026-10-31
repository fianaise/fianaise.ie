"""
staff_board_data.py
────────────────────
Hand-transcribed reference data from the Department of Education and Youth's
official report:

    "Primary School Survey – Results Summary Report" (June 2026)
    Department of Education and Youth, Ireland

WHERE TO GET THE ORIGINAL REPORT
---------------------------------
The report is published at:
    https://www.gov.ie/en/department-of-education/campaigns/primary-school-survey/
(look for "Primary School Survey - Results Summary Report" under "Publications").

The direct PDF link used for this project was:
    https://assets.gov.ie/static/documents/1e08f77c/Primary_School_Survey_Results_Summary_Report_final__.pdf

NOTE: assets.gov.ie blocks automated/robotic downloads (robots.txt), so this
file CANNOT be fetched programmatically — it must be downloaded manually in a
browser and, if you want to re-derive the numbers below yourself, placed in
DATA_DIR (e.g. as 'Primary_School_Survey_Results_Summary_Report.pdf').

WHY THIS DATA IS HARDCODED RATHER THAN COMPUTED
--------------------------------------------------
The school/SPA-level spreadsheets published alongside the report contain ONLY
parent/guardian survey results. Staff and Board of Management member results
are published exclusively as pre-aggregated summary tables inside the PDF
report (Tables 7 and 8) — no underlying microdata or per-school/per-county
breakdown is available anywhere else. These numbers therefore cannot be
independently re-derived from the spreadsheet; they are transcribed directly
from the PDF, one field at a time, and cited below by table and page number.
Every other figure used elsewhere in this notebook that CAN be checked against
the spreadsheet (parent-side multi-denominational preference) IS checked —
see the verification cells in the notebook.
"""

import pandas as pd

REPORT_CITATION = (
    "Department of Education and Youth (2026). 'Primary School Survey – "
    "Results Summary Report', June 2026. "
    "https://www.gov.ie/en/department-of-education/campaigns/primary-school-survey/"
)

# ─────────────────────────────────────────────────────────────────────────
# Table 7 – "high level results for staff / boards of management members"
# (Section 4.2, p.26)
# ─────────────────────────────────────────────────────────────────────────
TABLE_7_STAFF_BOARD_NATIONAL = pd.DataFrame([
    ('CO-EDUCATIONAL',            30977, 94.2),
    ('SINGLE-SEX',                 1924,  5.8),
    ('DENOMINATIONAL',            21469, 65.3),
    ('MULTI-DENOMINATIONAL',      11432, 34.7),
    ('EDUCATION THROUGH ENGLISH', 28474, 86.5),
    ('EDUCATION THROUGH IRISH',    4427, 13.5),
], columns=['preference', 'responses', 'percentage'])

# Section 4.1, p.25
STAFF_BOARD_TARGET_POPULATION   = 84285   # eligible staff/BoM members nationally
STAFF_BOARD_SUBMITTED_RESPONSES = 32999
STAFF_BOARD_VALID_RESPONSES     = 32901   # = final analytical base, 39.0% response rate
STAFF_BOARD_RESPONSE_RATE_PCT   = 39.0

# Section 4.3, p.26: staff and board members associated with denominational
# schools who prefer multi-denominational patronage (93.7% at multi-
# denominational schools). Compare parents at denominational schools, 40.2%
# (INTEND_TO_ENROL_MULTIDENOM['current_denom_school_want_multi_pct']).
STAFF_BOARD_DENOM_SCHOOL_WANT_MULTI_PCT      = 31.6
STAFF_BOARD_MULTIDENOM_SCHOOL_WANT_MULTI_PCT = 93.7

# Parents and guardians: eligible households, responses received and valid
# responses after validation (one per household, checked by Eircode), from the
# same report. Parental response rates by county ranged from 31.5% (Louth) to
# 63.4% (Meath).
PARENT_ELIGIBLE            = 485482
PARENT_SUBMITTED_RESPONSES = 241301
PARENT_VALID_RESPONSES     = 200381   # = Table 2a 'ALL' responses
PARENT_RESPONSE_RATE_RANGE = (("Louth", 31.5), ("Meath", 63.4))

# ─────────────────────────────────────────────────────────────────────────
# Table 8 – "Staff and board of management member preferences by county"
# (Section 4.4, p.29)
# ─────────────────────────────────────────────────────────────────────────
TABLE_8_STAFF_BOARD_BY_COUNTY = pd.DataFrame([
    ('Carlow',     447, 89.9, 26.2, 15.0),
    ('Cavan',      621, 97.9, 25.4,  8.9),
    ('Clare',      792, 99.9, 31.9,  9.2),
    ('Cork',      3702, 91.4, 42.1, 13.1),
    ('Donegal',   1427, 99.6, 22.9, 20.4),
    ('Dublin',    7114, 90.2, 43.3, 12.7),
    ('Galway',    2077, 98.7, 34.0, 23.5),
    ('Kerry',     1094, 97.4, 24.9, 20.8),
    ('Kildare',   1354, 93.7, 38.8, 13.4),
    ('Kilkenny',   719, 97.6, 33.0,  9.6),
    ('Laois',      730, 91.8, 25.5,  8.2),
    ('Leitrim',    357, 99.7, 19.3, 13.2),
    ('Limerick',  1462, 91.9, 31.9, 12.4),
    ('Longford',   470, 97.0, 19.1,  7.4),
    ('Louth',      991, 94.9, 34.6, 13.2),
    ('Mayo',      1098, 99.7, 26.4, 16.2),
    ('Meath',     1400, 98.3, 35.6, 13.4),
    ('Monaghan',   451, 88.9, 20.8, 13.3),
    ('Offaly',     692, 92.5, 24.7,  8.2),
    ('Roscommon',  685, 98.1, 22.5,  6.3),
    ('Sligo',      466, 99.8, 31.5, 11.8),
    ('Tipperary', 1178, 91.9, 32.9, 10.6),
    ('Waterford',  900, 82.9, 39.3, 13.0),
    ('Westmeath',  755, 98.1, 22.8, 11.1),
    ('Wexford',   1032, 99.3, 39.1, 10.8),
    ('Wicklow',    887, 96.4, 41.0, 12.9),
], columns=['County', 'Responses', 'CoEd_pref_pct', 'MultiDenom_pref_pct', 'Irish_pref_pct'])

# ─────────────────────────────────────────────────────────────────────────
# Table 3 – "Summary of preferences by county, household type" (p.19)
# Only the multi-denominational preference columns are reproduced here
# (co-education and Irish columns from the same table are omitted as they
# are not used in this notebook, but could be added the same way).
# ─────────────────────────────────────────────────────────────────────────
TABLE_3_PARENT_MULTIDENOM_BY_COUNTY = pd.DataFrame([
    ('Carlow',    38.40, 37.10, 41.40),
    ('Cavan',     35.90, 35.60, 36.60),
    ('Clare',     44.20, 41.90, 48.30),
    ('Cork',      49.70, 48.30, 52.70),
    ('Donegal',   29.90, 29.80, 30.00),
    ('Dublin',    52.60, 51.30, 55.20),
    ('Galway',    41.70, 41.30, 42.50),
    ('Kerry',     38.40, 36.80, 41.50),
    ('Kildare',   49.80, 49.10, 51.50),
    ('Kilkenny',  43.60, 42.60, 45.70),
    ('Laois',     37.20, 36.30, 39.20),
    ('Leitrim',   37.20, 37.80, 35.70),
    ('Limerick',  37.50, 36.50, 39.70),
    ('Longford',  29.80, 29.90, 29.60),
    ('Louth',     39.40, 37.90, 42.60),
    ('Mayo',      34.90, 34.40, 35.80),
    ('Meath',     43.60, 42.90, 45.10),
    ('Monaghan',  29.40, 29.50, 29.10),
    ('Offaly',    34.60, 33.40, 37.00),
    ('Roscommon', 34.50, 34.50, 34.50),
    ('Sligo',     42.80, 41.10, 46.60),
    ('Tipperary', 39.20, 37.80, 42.10),
    ('Waterford', 49.00, 48.20, 50.60),
    ('Westmeath', 36.60, 36.30, 37.20),
    ('Wexford',   45.50, 44.30, 47.80),
    ('Wicklow',   56.50, 55.70, 58.00),
], columns=['County', 'All_households_pct', 'Children_in_school_pct', 'Not_yet_in_school_pct'])

# ─────────────────────────────────────────────────────────────────────────
# Table 2a – "Summary of household preferences with breakdown by household
# type" — Proportions rows (p.16). Used to cross-check the spreadsheet-
# derived national figures in the notebook.
# ─────────────────────────────────────────────────────────────────────────
TABLE_2A_NATIONAL_PROPORTIONS = pd.DataFrame([
    ('ALL',                       200381, 94.4, 5.6, 45.0, 55.0, 77.9, 22.1),
    ('not_yet_in_school_only',     66403, 93.7, 6.3, 47.0, 53.0, 74.1, 25.9),
    ('in_school_only',            107948, 94.6, 5.4, 43.9, 56.1, 80.2, 19.8),
    ('both_in_school_and_not_yet', 26030, 95.0, 5.0, 44.5, 55.5, 78.0, 22.0),
], columns=['household_type', 'responses', 'coed_pct', 'singlesex_pct',
            'multidenom_pct', 'denom_pct', 'english_pct', 'irish_pct'])

# ─────────────────────────────────────────────────────────────────────────
# Section 3.1.2 "Multi-denominational preference" narrative figures (p.14).
# These describe the "intend to enrol" chain for households with a child
# NOT yet in school, and are the source of the 90.7% / 42% / 86.5% figures.
# ─────────────────────────────────────────────────────────────────────────
INTEND_TO_ENROL_MULTIDENOM = {
    # Base used throughout Section 3.1 for "households with a child not yet
    # in school" (this is a validated-response base and is NOT the same as
    # the 66,403 total shown in Table 2a / Annex 1 for that household type —
    # see the verification cell in the notebook for why).
    'not_yet_in_school_base': 56227,

    'intend_denom_school':                50980,   # out of 56,227
    'intend_denom_school_pct':             90.7,

    'intend_denom_want_change_to_multi':  21464,   # out of 50,980
    'intend_denom_want_change_to_multi_pct': 42.0,

    'intend_multidenom_school':            5247,   # 56,227 - 50,980 = 5,247
    'intend_multidenom_want_multi':        4543,   # out of 5,247
    'intend_multidenom_want_multi_pct':    86.5,

    # For comparison — same section, households with children CURRENTLY in
    # school (used as context, not plotted, but included for completeness):
    'current_denom_school_want_multi':     53735,  # out of 133,523
    'current_denom_school_base':          133523,
    'current_denom_school_want_multi_pct':  40.2,
    'current_multidenom_school_want_multi': 10338, # out of 12,179
    'current_multidenom_school_base':      12179,
    'current_multidenom_school_want_multi_pct': 84.9,
}
