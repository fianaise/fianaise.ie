# Fianaise

Source for [fianaise.ie](https://fianaise.ie): evidence on Irish public life, from open data. *Fianaise* is Irish for evidence.

Built with [Quarto](https://quarto.org). Every push to `main` builds the site and publishes it to the `gh-pages` branch. Preview locally with `quarto preview`.

## Layout

- `*.qmd`, `religion/*.qmd`: the pages.
- `figures/`: the interactive figures the pages embed, as standalone HTML. Plotly figures load a shared copy of plotly.js from `figures/lib/` (run `python3 -I tools/slim_plotly.py figures/*.html` after adding one).
- `analysis/education_equality/`: code and data for the religion and Primary School Survey figures. Moved from [maedbhk/education_equality](https://github.com/maedbhk/education_equality).
- `analysis/charts/make_charts.py`: redraws the census, marriage and survey bar charts in the site's style, from the same data.
- `analysis/charts/make_maps.py`: draws the patronage maps and headline numbers on the Schools page (`religion/_patronage-stats.md`), the preference-versus-provision chart, and the school ethos and Primary School Survey maps on county outlines (`analysis/charts/data/ireland_counties.geojson`, built by `make_geography.py` from Natural Earth). Inputs are in `analysis/charts/data/raw/`.
- `tools/fetch_school_lists.py`: downloads new or changed "Data on Individual Schools" lists from gov.ie (or data.gov.ie). gov.ie refuses requests from GitHub's servers, so run it from your own computer, or download the list and upload it to `analysis/charts/data/raw/` on GitHub. Either way, a push of a new list to `main` starts the `Refresh school data` workflow, which redraws the maps and opens a pull request.
- `analysis/cycling/`: DLR's open bicycle counter data (`data/raw/`, fetched by `tools/fetch_cycle_counts.py`), `dlr_counts.py`, which loads and cleans it, `make_counter_page.py`, which draws the DLR cycle counters page, and `make_cycling_charts.py`, which draws the counter charts on the Blackrock DART laneway page. The `Refresh cycle counts` workflow checks for new data every Monday, redraws both, commits them to `main` and republishes the site.
- `marriage/`: the Married, or not project. `marriage/tax-rules.js` holds the tax rules (update after each Budget); `node analysis/marriage/make_examples.js` redraws the worked-examples table and `node analysis/marriage/make_tiles.js` the tile images.
- `analysis/charities/`: the pipeline for the charities landscape. Moved from [opentalamh/opentalamh.ie](https://github.com/opentalamh/opentalamh.ie).

Text and figures are CC BY 4.0. Code is MIT licensed (see `LICENSE-code`).
