export type Strategy = 'protect_critical' | 'maximize_access' | 'balanced'
export type ResourceType =
  | 'road_clearance_team' | 'portable_generator' | 'temporary_medical_unit' | 'water_distribution_unit' | 'temporary_shelter_kit'
export type RoadStatus = 'open' | 'degraded' | 'restricted' | 'closed'
export type HazardClass = 'normal' | 'watch' | 'flood_risk' | 'impassable'
export type FacilityType = 'hospital' | 'shelter' | 'school' | 'emergency' | 'water'
export type DisplayStatus = 'accessible' | 'accessible_with_delay' | 'operationally_affected' | 'inaccessible'
export type ZoneStatus = 'normal' | 'exposed' | 'reduced_access' | 'isolated'
export type Service = 'hospital' | 'shelter' | 'water'

export interface Thresholds {
  watch: number; flood_risk: number; impassable: number
  degraded_penalty: number; restricted_penalty: number; delay_ratio: number
}
export interface Intervention { resource_id: string; resource_type: ResourceType; target_id: string }

export interface Scenario {
  id: string; name: string
  rainfall_mm: number; duration_hours: number; drainage_effectiveness: number
  susceptibility_preset: 'low' | 'moderate' | 'high'
  closed_road_ids: string[]; affected_power_nodes: string[]; failed_drainage_ids: string[]; failed_facility_ids: string[]
  resource_budget: number; resource_availability: number
  strategy: Strategy | null
  deployed_resources: Intervention[]
  thresholds: Thresholds
  created_at?: string | null
  simulation_version: string
}

export interface Preset { id: string; name: string; description: string; scenario: Scenario; response_strategy: Strategy | null }
export interface StrategyInfo { id: Strategy; label: string; description: string; weights: Record<string, number> }
export interface ResourceDef {
  id: string; name: string; resource_type: ResourceType; staging_id: string; node_id: string; location: [number, number]
  quantity_available: number; response_radius: number; deployment_cost: number; deployment_time_minutes: number; service_capacity: number
}

export interface GeoFeature {
  type: 'Feature'; id?: string | number
  properties: Record<string, any>
  geometry: { type: 'Point'; coordinates: [number, number] } | { type: 'LineString'; coordinates: [number, number][] } | { type: 'Polygon'; coordinates: [number, number][][] }
}
export interface GeoCollection { type: 'FeatureCollection'; features: GeoFeature[]; properties?: Record<string, unknown> }

export interface Dataset {
  dataset_version: string; simulation_version: string; data_label: string; synthetic_data: boolean
  layers: Record<'roads' | 'nodes' | 'facilities' | 'zones' | 'hazards' | 'infrastructure' | 'staging' | 'resources' | 'boundary' | 'river', GeoCollection>
  presets: Preset[]; strategies: StrategyInfo[]; resources: ResourceDef[]
  default_thresholds: Thresholds; service_thresholds_minutes: Record<string, number>
  catalog: {
    power_nodes: { id: string; name: string }[]
    drainage: { id: string; name: string; power_node_id: string }[]
    facilities: { id: string; name: string; facility_type: FacilityType; power_dependent: boolean }[]
  }
}

export interface MetricDef { label: string; unit: string; better: 'lower' | 'higher' | 'neutral'; definition: string }
export type Metrics = Record<string, number | null>

export interface RoadResult { status: RoadStatus; risk: number; hazard_class: HazardClass; travel_minutes: number | null; base_minutes: number; reason: string | null }
export interface HazardResult { risk: number; hazard_class: HazardClass }
export interface ServiceResult {
  best_facility_id: string | null; minutes: number | null; baseline_facility_id: string | null; baseline_minutes: number | null
  threshold_minutes: number; reduced: boolean; no_route: boolean; reachable_count: number
}
export interface ZoneResult {
  id: string; name: string; population: number; exposure_score: number; exposed_fraction: number; exposed_population: number
  vulnerability_weighted_exposure: number; status: ZoneStatus; services: Record<Service, ServiceResult>; reduced_service_count: number
}
export interface FacilityResult {
  id: string; name: string; facility_type: FacilityType; capacity: number; operational_status: 'operational' | 'reduced' | 'offline'
  capacity_multiplier: number; capacity_available: number; operational_reason: string; power_dependent: boolean; temporary: boolean
  accessibility_status: 'accessible' | 'accessible_with_delay' | 'inaccessible'; display_status: DisplayStatus
  zones_reaching: string[]; zones_lost: string[]; zones_delayed: string[]; minutes_from_zone: Record<string, number | null>
}
export interface AppliedIntervention {
  resource_id: string; resource_name: string; resource_type: ResourceType; target_id: string; target_name: string
  cost: number; deploy_minutes: number; capacity_added: number
}
export interface MapState {
  roads: Record<string, [RoadStatus, number]>
  hazards: Record<string, [HazardClass, number]>
  facilities: Record<string, DisplayStatus>
  zones: Record<string, ZoneStatus>
  power: Record<string, boolean>
  drainage: Record<string, boolean>
}
export interface AltRoute {
  zone_id: string; facility_id: string; facility_type: Service; baseline_minutes: number; baseline_roads: string[]
  scenario_minutes: number | null; scenario_roads: string[]; status: 'rerouted' | 'no_route'; delay_minutes: number | null
}
export interface Block {
  metrics: Metrics
  roads: Record<string, RoadResult>
  hazards: Record<string, HazardResult>
  power: Record<string, { risk: number; hazard_class: HazardClass; failed: boolean; reason: string }>
  drainage: Record<string, { failed: boolean; reason: string }>
  zones: ZoneResult[]; facilities: FacilityResult[]
  affected_road_ids: string[]; flooded_road_ids: string[]; inaccessible_facility_ids: string[]; facilities_lost_access_ids: string[]
  affected_zone_ids: string[]; impacted_population_estimate: number; affected_service_capacity: number
  reachable_facilities_by_zone: Record<string, Record<Service, string[]>>
  interventions: AppliedIntervention[]; estimated_restore_hours: number; temporary_facilities: FacilityResult[]
  routes: Record<string, Record<string, { minutes: number; roads: string[] }>>
  alternative_routes: AltRoute[]
  map_state: MapState
}
export interface ComparisonRow {
  key: string; label: string; unit: string; better: 'lower' | 'higher' | 'neutral'
  baseline: number | null; disaster: number | null; recovery: number | null
  delta_disaster: number | null; delta_recovery: number | null
}
export interface TimelineStage {
  t_minutes: number; label: string; description: string; rainfall_mm: number; phase: string
  metrics: Metrics; map_state: MapState
}
export interface Bottleneck {
  road_id: string; score: number; population_affected: number; affected_zone_ids: string[]; affected_facility_ids: string[]
  sole_route_facility_ids: string[]; status: RoadStatus; name: string; road_type: string; explanation: string; baseline_criticality: number
}
export interface RecoverySummary {
  population_access_restored: number; facilities_restored_or_protected: string[]; budget: number; budget_consumed: number
  budget_remaining: number; capacity_recovered: number; estimated_restore_hours: number
}
export interface SimulationResponse {
  simulation_version: string; dataset_version: string; synthetic_data: boolean; data_label: string; generated_at: string
  scenario: Scenario; baseline: Block; disaster: Block; recovery: Block | null
  comparison: ComparisonRow[]; recovery_summary: RecoverySummary | null; timeline: TimelineStage[]
  bottlenecks: Bottleneck[]; metric_definitions: Record<string, MetricDef>; assumptions: string[]; warnings: string[]
}
export interface PlanIntervention extends AppliedIntervention {
  benefit: number; benefit_cost_ratio: number; people_access_gain: number; capacity_gain: number; action: string; reasoning: string
}
export interface Plan {
  strategy: Strategy; strategy_label: string; strategy_description: string; weights: Record<string, number>
  interventions: PlanIntervention[]; budget: number; budget_consumed: number; budget_remaining: number
  resources_by_type: Record<string, number>
  not_completed: { resource_id: string; resource_type: ResourceType; target_id: string; target_name: string; cost: number; reason: string }[]
  candidates_evaluated: number; candidates_with_benefit: number; scenario: Scenario; method: string
}
export interface OptimizeResponse { plan: Plan; simulation: SimulationResponse }

export interface BriefSections {
  situation_summary: string; top_impacts: string[]; critical_bottlenecks: string[]; services_requiring_attention: string[]
  immediate_actions: string[]; followup_actions: string[]; resource_tradeoffs: string[]; uncertainties: string[]
}
export interface Brief {
  provider: 'bedrock' | 'rule_based'; provider_label: string; model_id: string | null; sections: BriefSections
  fallback_reason: string | null; simulation_version: string; dataset_version: string; synthetic_data: boolean; brief_type: string
}
export interface CompareResponse {
  metrics: { key: string; label: string; unit: string; better: string; values: { scenario_id: string; scenario_name: string; disaster: number | null; final: number | null; has_recovery: boolean; delta_vs_first: number | null }[] }[]
  zone_accessibility: unknown[]
  resource_tradeoffs: { scenario_id: string; scenario_name: string; budget: number; budget_consumed: number; resources_deployed: number; population_access_restored: number }[]
}
export interface ApiErrorBody { error: { code: string; message: string; details?: { field: string; message: string }[] } }

export type ViewMode = 'baseline' | 'scenario' | 'recovery'
export type Selection = { kind: 'road' | 'facility' | 'zone' | 'hazard' | 'power' | 'drainage' | 'resource'; id: string } | null

