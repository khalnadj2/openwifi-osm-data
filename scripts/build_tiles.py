#!/usr/bin/env python3
"""Build per-tile JSON files of WiFi places from OSM GeoJSON-seq features (osmium export --attributes=type,id)."""

import argparse
import datetime
import json
import math
import pathlib
import sys

ZOOM = 12
FORMAT = 2
ATTRIBUTION = "© OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright"
OSM_TYPES = {"node", "way", "relation"}


def tile_for(lat: float, lon: float, zoom: int = ZOOM) -> tuple[int, int]:
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return min(max(x, 0), n - 1), min(max(y, 0), n - 1)


def centroid(geometry: dict) -> tuple[float, float] | None:
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Point":
        return coords[1], coords[0]
    if kind == "Polygon":
        ring = coords[0]
    elif kind == "MultiPolygon":
        ring = coords[0][0]
    elif kind == "LineString":
        ring = coords
    else:
        return None
    if not ring:
        return None
    lon = sum(p[0] for p in ring) / len(ring)
    lat = sum(p[1] for p in ring) / len(ring)
    return lat, lon


def ref_of(feature: dict) -> str | None:
    props = feature.get("properties") or {}
    kind = props.get("@type")
    ident = props.get("@id")
    if kind in OSM_TYPES and ident is not None:
        return f"{kind}/{ident}"
    return None


def address_of(tags: dict) -> str:
    street = " ".join(v for v in (tags.get("addr:housenumber"), tags.get("addr:street")) if v)
    return ", ".join(v for v in (street, tags.get("addr:city")) if v)


def place_from(feature: dict) -> dict | None:
    ref = ref_of(feature)
    point = centroid(feature.get("geometry") or {})
    if ref is None or point is None:
        return None
    tags = feature.get("properties") or {}
    lat, lon = point
    return {
        "ref": ref,
        "name": tags.get("name", ""),
        "ssid": tags.get("internet_access:ssid", ""),
        "venue": tags.get("amenity") or tags.get("tourism") or tags.get("shop") or "",
        "address": address_of(tags),
        "internet_access": tags.get("internet_access", ""),
        "fee": tags.get("internet_access:fee", ""),
        "lat": round(lat, 6),
        "lon": round(lon, 6),
    }


def read_features(paths: list[pathlib.Path]):
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip().lstrip("\x1e")
                if line:
                    yield json.loads(line)


def build(paths: list[pathlib.Path], out: pathlib.Path) -> int:
    tiles: dict[tuple[int, int], dict[str, dict]] = {}
    read = skipped = 0
    for feature in read_features(paths):
        read += 1
        if read == 1:
            props = feature.get("properties") or {}
            print(f"first feature properties: {sorted(props)}", file=sys.stderr)
        place = place_from(feature)
        if place is None:
            skipped += 1
            continue
        key = tile_for(place["lat"], place["lon"])
        tiles.setdefault(key, {})[place["ref"]] = place

    total = sum(len(v) for v in tiles.values())
    print(f"features read: {read}, skipped without type or position: {skipped}", file=sys.stderr)
    if total == 0:
        raise SystemExit("no WiFi places found in the input; refusing to publish empty data")

    out.mkdir(parents=True, exist_ok=True)
    tiles_dir = out / "tiles" / str(ZOOM)
    for (x, y), places in tiles.items():
        target = tiles_dir / str(x) / f"{y}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"format": FORMAT, "attribution": ATTRIBUTION,
                        "places": sorted(places.values(), key=lambda p: p["ref"])},
                       ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    manifest = {
        "format": FORMAT,
        "zoom": ZOOM,
        "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "attribution": ATTRIBUTION,
        "tiles": len(tiles),
        "places": total,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("features", nargs="+", type=pathlib.Path, help="GeoJSON-seq files from osmium export")
    args = parser.parse_args()
    total = build(args.features, args.out)
    print(f"wrote {total} places", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
