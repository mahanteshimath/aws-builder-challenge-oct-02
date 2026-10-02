"""Dataset loading and GeoJSON validation. Reads bundled GeoJSON (optionally from S3)."""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from ..models.geography import (Dataset, DrainageAsset, EmergencyResource, Facility, GeoJSONError, HazardZone,
                                PopulationZone, PowerNode, RoadNode, RoadSegment, check_lonlat)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "geojson"
LAYERS = ["roads", "nodes", "facilities", "zones", "hazards", "infrastructure", "staging", "resources", "boundary", "river"]

GEOM_DEPTH = {"Point": 0, "LineString": 1, "Polygon": 2}


def _check_geometry(geom: dict) -> None:
    if not isinstance(geom, dict) or geom.get("type") not in GEOM_DEPTH:
        raise GeoJSONError(f"Unsupported geometry: {geom!r}"[:120])
    coords = geom.get("coordinates")
    if coords is None:
        raise GeoJSONError("Geometry without coordinates")
    depth = GEOM_DEPTH[geom["type"]]
    if depth == 0:
        check_lonlat(coords)
    elif depth == 1:
        if len(coords) < 2:
            raise GeoJSONError("LineString needs >= 2 points")
        for c in coords:
            check_lonlat(c)
    else:
        for ring in coords:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise GeoJSONError("Polygon ring must be closed with >= 4 points")
            for c in ring:
                check_lonlat(c)


def validate_collection(coll: dict, name: str = "collection") -> None:
    """Raise GeoJSONError when a FeatureCollection is malformed."""
    if not isinstance(coll, dict) or coll.get("type") != "FeatureCollection" or not isinstance(coll.get("features"), list):
        raise GeoJSONError(f"{name}: not a FeatureCollection")
    seen = set()
    for f in coll["features"]:
        if not isinstance(f, dict) or f.get("type") != "Feature":
            raise GeoJSONError(f"{name}: invalid feature")
        fid = f.get("id") or (f.get("properties") or {}).get("id")
        if not fid:
            raise GeoJSONError(f"{name}: feature without stable id")
        if fid in seen:
            raise GeoJSONError(f"{name}: duplicate id {fid}")
        seen.add(fid)
        _check_geometry(f.get("geometry"))


def _read_layers() -> dict[str, dict]:
    bucket = os.environ.get("GEOJSON_BUCKET")
    prefix = os.environ.get("GEOJSON_PREFIX", "geojson/")
    out: dict[str, dict] = {}
    s3 = None
    if bucket:
        try:
            import boto3
            s3 = boto3.client("s3")
        except Exception:  # pragma: no cover
            s3 = None
    for layer in LAYERS:
        data = None
        if s3 is not None:
            try:
                obj = s3.get_object(Bucket=bucket, Key=f"{prefix}{layer}.geojson")
                data = json.loads(obj["Body"].read())
            except Exception:
                data = None  # fall back to the bundled copy
        if data is None:
            data = json.loads((DATA_DIR / f"{layer}.geojson").read_text(encoding="utf-8"))
        out[layer] = data
    return out


def build_dataset(layers: dict[str, dict]) -> Dataset:
    for name, coll in layers.items():
        validate_collection(coll, name)
    props = lambda f: {k: v for k, v in f["properties"].items() if k != "id"}  # noqa: E731
    nodes = {f["id"]: RoadNode(id=f["id"], name=f["properties"]["name"], lon=f["geometry"]["coordinates"][0],
                               lat=f["geometry"]["coordinates"][1], is_major=f["properties"].get("is_major", False))
             for f in layers["nodes"]["features"]}
    roads = {}
    for f in layers["roads"]["features"]:
        r = RoadSegment(id=f["id"], geometry=f["geometry"]["coordinates"], **props(f))
        if r.start_node_id not in nodes or r.end_node_id not in nodes:
            raise GeoJSONError(f"Road {r.id} references unknown node")
        roads[r.id] = r
    facilities = {}
    for f in layers["facilities"]["features"]:
        fac = Facility(id=f["id"], geometry=f["geometry"]["coordinates"], **props(f))
        if fac.node_id not in nodes:
            raise GeoJSONError(f"Facility {fac.id} references unknown node")
        facilities[fac.id] = fac
    zones = {f["id"]: PopulationZone(id=f["id"], geometry=f["geometry"]["coordinates"][0], **props(f))
             for f in layers["zones"]["features"]}
    hazards = {f["id"]: HazardZone(id=f["id"], geometry=f["geometry"]["coordinates"][0],
                                   **{k: v for k, v in props(f).items() if k != "center"})
               for f in layers["hazards"]["features"]}
    power, drain = {}, {}
    for f in layers["infrastructure"]["features"]:
        p = props(f)
        if p["infra_type"] == "power":
            power[f["id"]] = PowerNode(id=f["id"], name=p["name"], kind=p["kind"], node_id=p["node_id"],
                                       geometry=f["geometry"]["coordinates"], elevation_proxy=p["elevation_proxy"],
                                       flood_susceptibility=p["flood_susceptibility"],
                                       backup_power_available=p.get("backup_power_available", False))
        else:
            drain[f["id"]] = DrainageAsset(id=f["id"], name=p["name"], geometry=f["geometry"]["coordinates"],
                                           power_node_id=p["power_node_id"], backup_power_available=p["backup_power_available"],
                                           effectiveness_radius_m=p["effectiveness_radius_m"], drainage_boost=p["drainage_boost"])
    resources = {f["id"]: EmergencyResource(id=f["id"], location=f["geometry"]["coordinates"], **props(f))
                 for f in layers["resources"]["features"]}
    staging = {f["id"]: f["geometry"]["coordinates"] for f in layers["staging"]["features"]}
    for fac in facilities.values():
        if fac.power_node_id and fac.power_node_id not in power:
            raise GeoJSONError(f"Facility {fac.id} references unknown power node")
    manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8")) if (DATA_DIR / "manifest.json").exists() else {}
    return Dataset(version=manifest.get("dataset_version", "unknown"), nodes=nodes, roads=roads, facilities=facilities,
                   zones=zones, hazards=hazards, power_nodes=power, drainage=drain, resources=resources,
                   staging=staging, raw=layers)


@lru_cache(maxsize=1)
def get_dataset() -> Dataset:
    from .scenario_engine import annotate_baseline_criticality
    ds = build_dataset(_read_layers())
    annotate_baseline_criticality(ds)
    return ds
