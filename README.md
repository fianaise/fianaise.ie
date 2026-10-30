# Fianaise

Source for [fianaise.ie](https://fianaise.ie): evidence on Irish public life, from open data. *Fianaise* is Irish for evidence.

Built with [Quarto](https://quarto.org). Every push to `main` builds the site and publishes it to the `gh-pages` branch. Preview locally with `quarto preview`.

## Layout

- `*.qmd`, `religion/*.qmd`: the pages.
- `figures/`: the interactive figures the pages embed, as standalone HTML. Plotly figures load a shared copy of plotly.js from `figures/lib/` (run `python3 -I tools/slim_plotly.py figures/*.html` after adding one).
- `analysis/education_equality/`: code and data for the religion and Primary School Survey figures. Moved from [maedbhk/education_equality](https://github.com/maedbhk/education_equality).
- `analysis/charts/make_charts.py`: redraws the census, marriage and survey bar charts in the site's style, from the same data.
- `analysis/charts/make_maps.py`: draws the school ethos and Primary School Survey maps on county outlines (`analysis/charts/data/ireland_counties.geojson`, built by `make_geography.py` from Natural Earth). Inputs are in `analysis/charts/data/raw/`.
- `tools/fetch_school_lists.py`: downloads new or changed "Data on Individual Schools" lists from gov.ie. The `Refresh school data` workflow runs it on the 3rd of each month and, if a list changed, redraws the maps and opens a pull request. It can also be run by hand from the Actions tab.
- `analysis/charities/`: the pipeline for the charities landscape. Moved from [opentalamh/opentalamh.ie](https://github.com/opentalamh/opentalamh.ie).

Text and figures are CC BY 4.0. Code is MIT licensed (see `LICENSE-code`).
