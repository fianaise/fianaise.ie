# Fianaise

Source for [fianaise.ie](https://fianaise.ie): evidence on Irish public life, from open data. *Fianaise* is Irish for evidence.

Built with [Quarto](https://quarto.org). Every push to `main` builds the site and publishes it to the `gh-pages` branch. Preview locally with `quarto preview`.

## Layout

- `*.qmd`, `religion/*.qmd`: the pages.
- `figures/`: the interactive figures the pages embed, as standalone HTML. Plotly figures load a shared copy of plotly.js from `figures/lib/` (run `python3 -I tools/slim_plotly.py figures/*.html` after adding one).
- `analysis/education_equality/`: code and data for the religion and Primary School Survey figures. Moved from [maedbhk/education_equality](https://github.com/maedbhk/education_equality).
- `analysis/charts/make_charts.py`: redraws the census, marriage and survey bar charts in the site's style, from the same data.
- `figures/data/`: the numbers behind each figure as CSV, written by the chart scripts (`save_csv` in `make_charts.py`). `figures/figure-tools.js`, loaded on every page through `_figure-tools.html`, adds Download data (CSV), Download image (PNG) and Share buttons under each figure: it uses `figures/data/<figure>.csv` when there is one and otherwise reads the numbers out of the Plotly chart. Tables written as `<div class="data-table-wrap" data-figure="<name>">` get the same buttons. The same script fits charts to narrower screens (it wraps titles and legends, shrinks labels that would be cut off, and stacks side-by-side maps on a phone), folds each caption's `::: {.caption-details}` block behind a "Show details and sources" button, and lets wide tables scroll sideways on a phone.

Write each figure caption as a short first sentence (`**Figure N.** ...`) followed by a `::: {.caption-details}` block with the full description, sources and which schools are covered.
- `analysis/charts/make_maps.py`: draws the patronage maps and headline numbers on the Schools page (`religion/_patronage-stats.md`), the Primary School Survey county table (`religion/_county-multid-table.md`) and county map, the preference-versus-provision chart, and the school ethos and Primary School Survey maps on county outlines (`analysis/charts/data/ireland_counties.geojson`, built by `make_geography.py` from Natural Earth). Inputs are in `analysis/charts/data/raw/`.
- `tools/fetch_school_lists.py`: downloads new or changed "Data on Individual Schools" lists from gov.ie (or data.gov.ie). gov.ie refuses requests from GitHub's servers, so run it from your own computer, or download the list and upload it to `analysis/charts/data/raw/` on GitHub. Either way, a push of a new list to `main` starts the `Refresh school data` workflow, which redraws the maps and opens a pull request.
- `analysis/cycling/`: DLR's open bicycle counter data (`data/raw/`, fetched by `tools/fetch_cycle_counts.py`), `dlr_counts.py`, which loads and cleans it, `make_counter_page.py`, which draws the DLR cycle counters page, and `make_cycling_charts.py`, which draws the counter charts on the Blackrock DART laneway page. The `Refresh cycle counts` workflow checks for new data every Monday, redraws both, commits them to `main` and republishes the site.
- `cohabitation/`: the Cohabitation in Ireland project. `cohabitation/tax-rules.js` holds the tax rules (update after each Budget); `node analysis/cohabitation/make_examples.js` redraws the worked-examples table and `node analysis/cohabitation/make_tiles.js` the tile images.
- `analysis/airspace/`: the Irish airspace project. For each day, `scan_day.py` streams the adsb.lol archive and keeps every aircraft seen over Ireland (`data/daily/`), `summarise.py` counts government and business jets at Irish airports, `tracks.py` pulls their full tracks, `build.py` merges them, `video.py` draws the timelapse as a video and a GIF (needs matplotlib and ffmpeg) and `make_page.py` writes the tables in `airspace/`.
- `analysis/charities/`: the pipeline for the charities landscape. Moved from [opentalamh/opentalamh.ie](https://github.com/opentalamh/opentalamh.ie).

Text and figures are CC BY 4.0. Code is MIT licensed (see `LICENSE-code`).
