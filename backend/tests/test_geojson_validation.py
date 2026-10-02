import copy
import json

import pytest

from src.models.geography import GeoJSONError
from src.simulation.dataset import LAYERS, _read_layers, build_dataset, validate_collection


def test_bundled_geojson_valid():
    for name, coll in _read_layers().items():
        validate_collection(coll, name)


def test_invalid_geojson_rejected():
    with pytest.raises(GeoJSONError):
        validate_collection({"type": "Feature"}, "x")
    bad = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": "A", "properties": {}, "geometry": {"type": "Point", "coordinates": [500, 20]}}]}
    with pytest.raises(GeoJSONError):
        validate_collection(bad, "x")
    dup = {"type": "FeatureCollection", "features": [{"type": "Feature", "id": "A", "properties": {}, "geometry": {"type": "Point", "coordinates": [73, 18]}}] * 2}
    with pytest.raises(GeoJSONError):
        validate_collection(dup, "x")


def test_road_with_unknown_node_rejected():
    layers = copy.deepcopy(_read_layers())
    layers["roads"]["features"][0]["properties"]["start_node_id"] = "N-NOPE"
    with pytest.raises(GeoJSONError):
        build_dataset(layers)


def test_dataset_carries_provenance_and_license():
    for coll in _read_layers().values():
        assert coll["properties"]["synthetic"] is False and coll["properties"]["modeled_attributes"] is True
        assert "OpenStreetMap" in coll["properties"]["license"]
    roads = _read_layers()["roads"]["features"]
    assert all(f["properties"]["osm_way_id"] for f in roads)
    assert any(f["properties"]["crosses_mithi"] for f in roads)
