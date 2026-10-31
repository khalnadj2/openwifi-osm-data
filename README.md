# openwifi-osm-data

Weekly-built WiFi hotspot tiles for the OpenWifi Android app, derived from OpenStreetMap.

Each place tagged `internet_access=wlan` or `internet_access=yes` is written to the tile
(zoom 12) that contains its centre point, as `tiles/12/{x}/{y}.json`. A `manifest.json`
at the root records when the data was built and how many places it holds.

## Data and attribution

The data is derived from OpenStreetMap and is licensed under the
[Open Database License](https://opendatacommons.org/licenses/odbl/1.0/).

© OpenStreetMap contributors. Derived data must keep this attribution and the same license.

## Build

The workflow in `.github/workflows/build.yml` downloads the Geofabrik extract, filters it with
`osmium-tool`, converts the result to GeoJSON-seq, and runs `scripts/build_tiles.py`.
It publishes the `site/` folder with GitHub Pages.

Run it by hand from the Actions tab (`workflow_dispatch`), or wait for the weekly schedule.

## Local test

```
python3 scripts/build_tiles.py --out site path/to/features.geojsonseq
```
