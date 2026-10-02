"""Pydantic models for the geographic dataset (validated on load)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

FacilityType = Literal["hospital", "shelter", "school", "emergency", "water"]
RoadType = Literal["arterial", "collector", "local", "bridge"]


class GeoJSONError(ValueError):
    pass


def check_lonlat(coord) -> None:
    if not (isinstance(coord, (list, tuple)) and len(coord) >= 2):
        raise GeoJSONError(f"Invalid coordinate: {coord!r}")
    lon, lat = coord[0], coord[1]
    if not (isinstance(lon, (int, float)) and isinstance(lat, (int, float))):
        raise GeoJSONError(f"Non-numeric coordinate: {coord!r}")
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise GeoJSONError(f"Coordinate outside WGS84 range: {coord!r}")


class RoadNode(BaseModel):
    id: str
    name: str
    lon: float
    lat: float
    is_major: bool = False


class RoadSegment(BaseModel):
    id: str
    geometry: list[list[float]]
    start_node_id: str
    end_node_id: str
    road_type: RoadType
    name: str = ""
    length_m: float = Field(gt=0)
    base_travel_time_minutes: float = Field(gt=0)
    flood_susceptibility: float = Field(ge=0, le=1)
    elevation_proxy: float = Field(ge=0, le=1)
    drainage_score: float = Field(ge=0, le=1)
    power_dependency: Optional[str] = None
    current_status: str = "open"
    closure_reason: Optional[str] = None
    estimated_repair_cost: float = Field(ge=0)
    criticality_score: float = 0.0
    threshold_bonus: float = 0.0


class Facility(BaseModel):
    id: str
    name: str
    facility_type: FacilityType
    geometry: list[float]
    capacity: float = Field(ge=0)
    operational_status: str = "operational"
    power_dependent: bool = False
    backup_power_available: bool = False
    backup_power_hours: float = 0.0
    power_node_id: Optional[str] = None
    node_id: str
    minimum_accessibility_requirement: float = Field(gt=0)
    criticality_score: float = Field(ge=0, le=1)
    temporary: bool = False


class PopulationZone(BaseModel):
    id: str
    name: str
    geometry: list[list[float]]
    estimated_population: int = Field(gt=0)
    vulnerability_weight: float = Field(gt=0)
    mobility_constraint_factor: float = Field(gt=0)
    anchor_node_id: str
    bbox_grid: list[float]
    nearest_facility_ids: list[str] = []


class HazardZone(BaseModel):
    id: str
    name: str
    geometry: list[list[float]]
    susceptibility_score: float = Field(ge=0, le=1)
    estimated_water_accumulation: float = Field(ge=0, le=1)
    drainage_effectiveness: float = Field(ge=0, le=1)
    exposure_factor: float = Field(ge=0, le=1.5)
    center_grid: list[float]
    radii_grid: list[float]


class PowerNode(BaseModel):
    id: str
    name: str
    kind: str
    node_id: str
    geometry: list[float]
    elevation_proxy: float
    flood_susceptibility: float
    backup_power_available: bool = False


class DrainageAsset(BaseModel):
    id: str
    name: str
    geometry: list[float]
    power_node_id: str
    backup_power_available: bool
    effectiveness_radius_m: float
    drainage_boost: float


class EmergencyResource(BaseModel):
    id: str
    name: str
    resource_type: Literal["road_clearance_team", "portable_generator", "temporary_medical_unit",
                           "water_distribution_unit", "temporary_shelter_kit"]
    staging_id: str
    node_id: str
    location: list[float]
    quantity_available: int = Field(ge=0)
    response_radius: float = Field(gt=0)
    deployment_cost: float = Field(ge=0)
    deployment_time_minutes: float = Field(ge=0)
    service_capacity: float = Field(ge=0)


class Dataset(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    version: str
    nodes: dict[str, RoadNode]
    roads: dict[str, RoadSegment]
    facilities: dict[str, Facility]
    zones: dict[str, PopulationZone]
    hazards: dict[str, HazardZone]
    power_nodes: dict[str, PowerNode]
    drainage: dict[str, DrainageAsset]
    resources: dict[str, EmergencyResource]
    staging: dict[str, list[float]]
    raw: dict = {}
