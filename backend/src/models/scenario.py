"""Scenario request models with strict bounds."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

SIMULATION_VERSION = "1.0.0"

ResourceType = Literal["road_clearance_team", "portable_generator", "temporary_medical_unit",
                       "water_distribution_unit", "temporary_shelter_kit"]
Strategy = Literal["protect_critical", "maximize_access", "balanced"]


class Thresholds(BaseModel):
    """Flood-risk classification thresholds (illustrative, not calibrated)."""
    watch: float = Field(0.25, ge=0, le=1)
    flood_risk: float = Field(0.50, ge=0, le=1)
    impassable: float = Field(0.75, ge=0, le=1)
    degraded_penalty: float = Field(1.3, ge=1, le=10)
    restricted_penalty: float = Field(2.5, ge=1, le=20)
    delay_ratio: float = Field(1.25, ge=1, le=5)

    @model_validator(mode="after")
    def ordered(self):
        if not (self.watch < self.flood_risk < self.impassable):
            raise ValueError("thresholds must satisfy watch < flood_risk < impassable")
        return self


class Intervention(BaseModel):
    """A deployed resource action. Cost/time are recomputed server-side from the dataset."""
    resource_id: str = Field(max_length=32)
    resource_type: ResourceType
    target_id: str = Field(max_length=32)


class Scenario(BaseModel):
    id: str = Field("custom", max_length=64)
    name: str = Field("Custom scenario", max_length=120)
    rainfall_mm: float = Field(0, ge=0, le=200)
    duration_hours: float = Field(6, ge=1, le=72)
    drainage_effectiveness: float = Field(0.5, ge=0, le=1)
    susceptibility_preset: Literal["low", "moderate", "high"] = "moderate"
    closed_road_ids: list[str] = Field(default_factory=list, max_length=60)
    affected_power_nodes: list[str] = Field(default_factory=list, max_length=20)
    failed_drainage_ids: list[str] = Field(default_factory=list, max_length=20)
    failed_facility_ids: list[str] = Field(default_factory=list, max_length=40)
    resource_budget: float = Field(30, ge=0, le=1000)
    resource_availability: float = Field(1.0, ge=0, le=1)
    strategy: Optional[Strategy] = None
    deployed_resources: list[Intervention] = Field(default_factory=list, max_length=40)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    created_at: Optional[str] = None
    simulation_version: str = SIMULATION_VERSION


class SimulateRequest(BaseModel):
    scenario: Scenario
    include_timeline: bool = True


class OptimizeRequest(BaseModel):
    scenario: Scenario
    strategy: Strategy = "balanced"


class BriefRequest(BaseModel):
    scenario: Scenario
    brief_type: Literal["situation", "executive"] = "situation"
    allow_ai: bool = True


class CompareRequest(BaseModel):
    scenarios: list[Scenario] = Field(min_length=2, max_length=5)


class ExportRequest(BaseModel):
    scenario: Scenario
    format: Literal["json", "csv", "html"] = "json"


