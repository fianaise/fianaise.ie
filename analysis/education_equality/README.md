# education_equality

Code and data behind the religion and Primary School Survey figures. Moved here from [maedbhk/education_equality](https://github.com/maedbhk/education_equality).

| Script | Makes |
| --- | --- |
| `fetch_religion_cso.py`, `fetch_marriage_cso.py` | Downloads CSO tables F5071 and VSA44 into `data/` |
| `plot_CSO.py`, `make_html.py` | The census and marriage charts (`figures/catholic_religion_stats.html`, `no_religion_stats.html`, `marriage_stats.html`) |
| `fetch_school_patronage.py`, `plot_ethos_geospatial.py` | The school ethos map (`figures/ethos_current_config.html`) |
| `plot_survey_geospatial.py` | The school-level survey maps (`figures/map2_current_vs_preference.html`) |
| `plot_survey_summary.py`, `staff_board_data.py` | The county and summary survey figures (`figures/map9_parents_vs_staff_board.html`, `vis2_intend_vs_preference.html`) |

The Department of Education spreadsheets the survey and ethos scripts read are not kept in the repo. Download them from the links in each script.

Set up with `conda env create -f environment.yml`.
