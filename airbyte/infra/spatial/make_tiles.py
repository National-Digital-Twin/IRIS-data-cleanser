#!/usr/bin/env python3
import argparse
import json
import math
import os
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

try:
    from pyproj import Transformer
except Exception:  # pragma: no cover
    Transformer = None  # type: ignore


def _slug(s: str) -> str:
    return (
        s.strip()
        .replace("/", "-")
        .replace(" ", "_")
        .replace("__", "_")
        .replace("__", "_")
    )


@dataclass
class Tile:
    minx: int
    miny: int
    maxx: int
    maxy: int

    def to_bbox_text(self, region_code: str) -> str:
        return f"{self.minx},{self.miny},{self.maxx},{self.maxy}|{region_code}"


def parse_bbox_arg(bbox: str) -> Tuple[float, float, float, float]:
    parts = [p.strip() for p in bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("--bbox must be 'minx,miny,maxx,maxy'")
    return tuple(map(float, parts))  # type: ignore


def snap_floor(value: float, step: int) -> int:
    return int(math.floor(value / step) * step)


def snap_ceil(value: float, step: int) -> int:
    return int(math.ceil(value / step) * step)


def grid_tiles_from_bbox(
    bbox_27700: Tuple[float, float, float, float], tile_size_m: int
) -> Iterable[Tile]:
    minx, miny, maxx, maxy = bbox_27700
    x0 = snap_floor(minx, tile_size_m)
    y0 = snap_floor(miny, tile_size_m)
    x1 = snap_ceil(maxx, tile_size_m)
    y1 = snap_ceil(maxy, tile_size_m)

    y = y0
    while y < y1:
        x = x0
        while x < x1:
            yield Tile(x, y, x + tile_size_m, y + tile_size_m)
            x += tile_size_m
        y += tile_size_m


def load_region_geometry_4326(
    region_geojson_path: str, region_name: str
) -> List[List[List[Tuple[float, float]]]]:
    """
    Load a MultiPolygon in EPSG:4326 as nested lists of rings.
    Returns: List of polygons, each a list of rings, each a list of (lon, lat)
    """
    with open(region_geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)

    name_keys = [
        "RGN24NM",  # matches provided dataset
        "RGN22NM",
        "RGN21NM",
        "name",
        "NAME",
    ]

    target = None
    for feat in gj.get("features", []):
        props = feat.get("properties", {}) or {}
        val = None
        for k in name_keys:
            if k in props:
                val = props[k]
                break
        if val == region_name:
            target = feat
            break

    if not target:
        available = [
            next((props.get(k) for k in name_keys if k in props), None)
            for props in (f.get("properties", {}) for f in gj.get("features", []))
        ]
        raise ValueError(
            f"Region '{region_name}' not found in {region_geojson_path}. Available: {available}"
        )

    geom = target.get("geometry", {})
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])
    if gtype == "Polygon":
        multipoly = [coords]
    elif gtype == "MultiPolygon":
        multipoly = coords
    else:
        raise ValueError(f"Unsupported geometry type: {gtype}")

    # Normalize typing to List[List[List[(lon,lat)]]]
    mp: List[List[List[Tuple[float, float]]]] = []
    for poly in multipoly:
        rings: List[List[Tuple[float, float]]] = []
        for ring in poly:
            rings.append([(float(lon), float(lat)) for lon, lat in ring])
        mp.append(rings)
    return mp


def transform_points(
    points: List[Tuple[float, float]], from_epsg: int, to_epsg: int
) -> List[Tuple[float, float]]:
    if Transformer is None:
        raise RuntimeError("pyproj is required for coordinate transformations")
    tr = Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
    xs, ys = tr.transform([p[0] for p in points], [p[1] for p in points])
    return list(zip(xs, ys))


def region_bbox_27700_from_geojson(
    region_geojson_path: str, region_name: str
) -> Tuple[float, float, float, float]:
    mp_4326 = load_region_geometry_4326(region_geojson_path, region_name)
    mins = [math.inf, math.inf]
    maxs = [-math.inf, -math.inf]
    for poly in mp_4326:
        for ring in poly:
            ring_27700 = transform_points(ring, 4326, 27700)
            for x, y in ring_27700:
                mins[0] = min(mins[0], x)
                mins[1] = min(mins[1], y)
                maxs[0] = max(maxs[0], x)
                maxs[1] = max(maxs[1], y)
    return (mins[0], mins[1], maxs[0], maxs[1])


def point_in_ring(point: Tuple[float, float], ring: List[Tuple[float, float]]) -> bool:
    # Ray casting algorithm for rings in lon/lat (EPSG:4326)
    x, y = point
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-16) + x1
        ):
            inside = not inside
    return inside


def point_in_multipolygon_4326(
    point_lonlat: Tuple[float, float], mp_4326: List[List[List[Tuple[float, float]]]]
) -> bool:
    # inside outer ring and not inside any inner rings
    for poly in mp_4326:
        if not poly:
            continue
        outer = poly[0]
        holes = poly[1:]
        if point_in_ring(point_lonlat, outer):
            in_hole = any(point_in_ring(point_lonlat, h) for h in holes)
            if not in_hole:
                return True
    return False


def maybe_filter_tiles_by_region(
    tiles: Iterable[Tile],
    region_geojson_path: Optional[str],
    region_name: Optional[str],
    sample_step: int,
) -> List[Tile]:
    if not region_geojson_path or not region_name:
        return list(tiles)
    # Load region geometry (4326) and keep tiles whose centroid (27700) -> 4326 lies inside
    mp_4326 = load_region_geometry_4326(region_geojson_path, region_name)
    if Transformer is None:
        # Can't transform -> return unfiltered
        return list(tiles)
    tr_to4326 = Transformer.from_crs(27700, 4326, always_xy=True)
    filtered: List[Tile] = []
    for i, t in enumerate(tiles):
        # simple stride to keep performance acceptable on very large grids
        cx = (t.minx + t.maxx) / 2
        cy = (t.miny + t.maxy) / 2
        lon, lat = tr_to4326.transform(cx, cy)
        if point_in_multipolygon_4326((lon, lat), mp_4326):
            filtered.append(t)
    return filtered


def write_text_lines(path: str, lines: Iterable[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            if line.strip():
                f.write(line + "\n")


def export_tiles_geojson_27700(path: str, tiles: List[Tile]) -> None:
    features = []
    for t in tiles:
        # Note: GeoJSON spec expects lon/lat (4326), but for QC we keep 27700 as requested
        coordinates = [
            [
                [t.minx, t.miny],
                [t.maxx, t.miny],
                [t.maxx, t.maxy],
                [t.minx, t.maxy],
                [t.minx, t.miny],
            ]
        ]
        features.append(
            {
                "type": "Feature",
                "properties": {"minx": t.minx, "miny": t.miny, "maxx": t.maxx, "maxy": t.maxy},
                "geometry": {"type": "Polygon", "coordinates": coordinates},
            }
        )
    fc = {"type": "FeatureCollection", "features": features, "crs": "EPSG:27700"}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f)


def export_preview_html_4326(path: str, tiles: List[Tile], region_geojson_path: Optional[str]) -> None:
    try:
        import folium  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("folium is required for HTML preview") from e

    if Transformer is None:
        raise RuntimeError("pyproj is required for HTML preview (27700 -> 4326)")

    tr_to4326 = Transformer.from_crs(27700, 4326, always_xy=True)
    # center map on first tile
    if not tiles:
        return
    cx = (tiles[0].minx + tiles[0].maxx) / 2
    cy = (tiles[0].miny + tiles[0].maxy) / 2
    lon0, lat0 = tr_to4326.transform(cx, cy)
    m = folium.Map(location=[lat0, lon0], zoom_start=7, tiles="OpenStreetMap")

    # Add all region boundaries as background if provided (GeoJSON is in 4326)
    if region_geojson_path:
        try:
            with open(region_geojson_path, "r", encoding="utf-8") as f:
                gj = json.load(f)
            def _style(_):
                return {
                    "fill": False,
                    "color": "#999999",
                    "weight": 1,
                    "opacity": 0.7,
                }
            folium.GeoJson(gj, name="Regions", style_function=_style).add_to(m)
        except Exception as e:
            print(f"[warn] Could not overlay region boundaries on HTML: {e}")

    for t in tiles:
        ring27700 = [
            (t.minx, t.miny),
            (t.maxx, t.miny),
            (t.maxx, t.maxy),
            (t.minx, t.maxy),
            (t.minx, t.miny),
        ]
        ring4326 = [tr_to4326.transform(x, y)[::-1] for x, y in ring27700]  # to (lat, lon)
        folium.PolyLine(ring4326, color="#3388ff", weight=1, opacity=0.8).add_to(m)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    m.save(path)


def export_preview_png(path: str, tiles: List[Tile], region_geojson_path: Optional[str]) -> None:
    try:
        import matplotlib.pyplot as plt  # type: ignore
        from matplotlib.collections import PatchCollection  # type: ignore
        from matplotlib.patches import Rectangle  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("matplotlib is required for PNG preview") from e

    fig, ax = plt.subplots(figsize=(8, 8))

    # Draw region boundaries as background (transform 4326 -> 27700)
    if region_geojson_path:
        try:
            with open(region_geojson_path, "r", encoding="utf-8") as f:
                gj = json.load(f)
            if Transformer is None:
                raise RuntimeError("pyproj required for PNG region overlay")
            tr = Transformer.from_crs(4326, 27700, always_xy=True)

            def draw_ring(coords4326):
                xs = [c[0] for c in coords4326]
                ys = [c[1] for c in coords4326]
                X, Y = tr.transform(xs, ys)
                ax.plot(X, Y, color="#aaaaaa", linewidth=0.5, alpha=0.7)

            for feat in gj.get("features", []):
                geom = feat.get("geometry", {})
                gtype = geom.get("type")
                coords = geom.get("coordinates", [])
                if gtype == "Polygon":
                    for ring in coords:
                        draw_ring(ring)
                elif gtype == "MultiPolygon":
                    for poly in coords:
                        for ring in poly:
                            draw_ring(ring)
        except Exception as e:
            print(f"[warn] Could not overlay region boundaries on PNG: {e}")
    patches = []
    for t in tiles:
        patches.append(Rectangle((t.minx, t.miny), t.maxx - t.minx, t.maxy - t.miny))
    pc = PatchCollection(patches, facecolor="none", edgecolor="#3388ff", linewidths=0.3)
    ax.add_collection(pc)
    # bounds
    if tiles:
        minx = min(t.minx for t in tiles)
        miny = min(t.miny for t in tiles)
        maxx = max(t.maxx for t in tiles)
        maxy = max(t.maxy for t in tiles)
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
    ax.set_aspect("equal")
    ax.set_title("5 km tiles (EPSG:27700)")
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Generate 5 km tiles for a region (EPSG:27700)"
    )
    parser.add_argument(
        "--region-geojson",
        help="Path to regions GeoJSON (expects EPSG:4326, e.g. Regions_December_2024_*.geojson)",
    )
    parser.add_argument("--region-name", help="Region name (e.g. 'South East')")
    parser.add_argument(
        "--region-code",
        required=True,
        help="Region code (e.g. E12000008)",
    )
    parser.add_argument(
        "--bbox",
        help=(
            "Manual bbox in EPSG:27700 as 'minx,miny,maxx,maxy' (used when region polygon not available)"
        ),
    )
    parser.add_argument(
        "--tile-size-m", type=int, default=5000, help="Tile size in meters (default 5000)"
    )
    parser.add_argument("--outdir", default="out/", help="Output directory")
    parser.add_argument(
        "--no-joined",
        action="store_true",
        help="Do not write '*_joined.txt' joined files (joined is written by default)",
    )
    parser.add_argument(
        "--no-geojson", action="store_true", help="Do not write GeoJSON output"
    )
    parser.add_argument(
        "--no-preview-html", action="store_true", help="Do not write Folium HTML preview"
    )
    parser.add_argument(
        "--no-preview-png", action="store_true", help="Do not write PNG preview"
    )

    args = parser.parse_args()

    if not args.bbox and not (args.region_geojson and args.region_name):
        parser.error("Either --bbox or (--region-geojson and --region-name) must be provided")

    if args.bbox:
        bbox_27700 = parse_bbox_arg(args.bbox)
    else:
        bbox_27700 = region_bbox_27700_from_geojson(args.region_geojson, args.region_name)

    tiles = list(grid_tiles_from_bbox(bbox_27700, args.tile_size_m))

    # Optional filter by centroid-in-polygon when region geometry is available
    tiles = maybe_filter_tiles_by_region(
        tiles, args.region_geojson, args.region_name, sample_step=1
    )

    # Prepare outputs
    region_slug = _slug(args.region_name or args.region_code)
    base_a = os.path.join(args.outdir, f"tiles_{region_slug}")
    base_b = os.path.join(args.outdir, f"tiles_{args.region_code}")

    text_lines = [t.to_bbox_text(args.region_code) for t in tiles]

    write_text_lines(base_a + ".txt", text_lines)
    # Write a second name variant for convenience
    if base_b != base_a:
        write_text_lines(base_b + ".txt", text_lines)

    # By default write joined variant for Airbyte declarative source config
    if not args.no_joined:
        joined = "|||".join(text_lines)
        os.makedirs(os.path.dirname(base_a), exist_ok=True)
        with open(base_a + "_joined.txt", "w", encoding="utf-8") as f:
            if joined:
                f.write(joined)
        if base_b != base_a:
            with open(base_b + "_joined.txt", "w", encoding="utf-8") as f:
                if joined:
                    f.write(joined)

    if not args.no_geojson:
        export_tiles_geojson_27700(base_a + ".geojson", tiles)

    if not args.no_preview_html:
        try:
            export_preview_html_4326(
                base_a + "_preview.html", tiles, args.region_geojson
            )
        except Exception as e:
            print(f"[warn] Could not write HTML preview: {e}")

    if not args.no_preview_png:
        try:
            export_preview_png(base_a + "_preview.png", tiles, args.region_geojson)
        except Exception as e:
            print(f"[warn] Could not write PNG preview: {e}")

    wrote = [base_a + ".txt"]
    if base_b != base_a:
        wrote.append(base_b + ".txt")
    if not args.no_joined:
        wrote.append(base_a + "_joined.txt")
        if base_b != base_a:
            wrote.append(base_b + "_joined.txt")
    print("Wrote: " + ", ".join(wrote))


if __name__ == "__main__":
    main()
