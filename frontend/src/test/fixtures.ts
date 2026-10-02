import type { Dataset, Scenario, SimulationResponse, Block, MapState } from '@/types'
import { BASE_SCENARIO } from '@/store/scenarioStore'

const ms = (over: Partial<MapState> = {}): MapState => ({ roads: { 'R-001': ['open', 0], 'R-019': ['closed', 0.2] }, hazards: { 'HZ-01': ['normal', 0] }, facilities: { 'H-01': 'accessible' }, zones: { 'Z-01': 'normal' }, power: {}, drainage: {}, ...over })

export const metrics = (o: Record<string, number | null> = {}) => ({
  population_total: 70100, exposed_population: 0, vulnerability_weighted_exposure: 0, pop_reduced_hospital: 0, pop_reduced_shelter: 0, pop_reduced_water: 0, pop_reduced_any: 0,
  roads_total: 91, roads_affected: 0, roads_degraded: 0, roads_restricted: 0, roads_closed: 0, facilities_operationally_affected: 0, facilities_inaccessible_some_zone: 0,
  avg_hospital_time_min: 5.7, zones_no_feasible_route: 0, service_capacity_available: 12070, shelter_capacity_available: 2000, shelter_demand: 0, shelter_shortfall: 0,
  hospitals_accessible: 4, shelters_accessible: 6, water_points_accessible: 6, electricity_dependent_affected: 0, resources_deployed: 0, budget_consumed: 0, ...o,
})

export const block = (m: Record<string, number | null> = {}, extra: Partial<Block> = {}): Block => ({
  metrics: metrics(m), roads: { 'R-019': { status: 'closed', risk: 0.2, hazard_class: 'normal', travel_minutes: null, base_minutes: 2.6, reason: 'Explicit closure' } },
  hazards: {}, power: {}, drainage: {}, zones: [], facilities: [], affected_road_ids: [], flooded_road_ids: [], inaccessible_facility_ids: [], facilities_lost_access_ids: [],
  affected_zone_ids: [], impacted_population_estimate: 0, affected_service_capacity: 0, reachable_facilities_by_zone: {}, interventions: [], estimated_restore_hours: 0,
  temporary_facilities: [], routes: {}, alternative_routes: [], map_state: ms(), ...extra,
})

export function makeResult(withRecovery = false, scenario: Scenario = BASE_SCENARIO): SimulationResponse {
  const dis = block({ exposed_population: 20426, pop_reduced_hospital: 34600, roads_affected: 56, roads_closed: 3, hospitals_accessible: 3 })
  const rec = withRecovery ? block({ exposed_population: 20426, pop_reduced_hospital: 9800, roads_affected: 50, roads_closed: 2, hospitals_accessible: 4, budget_consumed: 28.9, resources_deployed: 8 }) : null
  const stage = (t: number, label: string) => ({ t_minutes: t, label, description: label, rainfall_mm: 0, phase: 'disaster', metrics: metrics(), map_state: ms() })
  return {
    simulation_version: '1.0.0', dataset_version: 'test', synthetic_data: true, data_label: 'SYNTHETIC DEMONSTRATION DATA', generated_at: '2026-10-02T00:00:00Z',
    scenario, baseline: block(), disaster: dis, recovery: rec,
    comparison: [{ key: 'exposed_population', label: 'Estimated population in potentially affected zones', unit: 'people', better: 'lower', baseline: 0, disaster: 20426, recovery: rec ? 20426 : null, delta_disaster: 20426, delta_recovery: rec ? 0 : null }],
    recovery_summary: rec ? { population_access_restored: 22300, facilities_restored_or_protected: ['H-03'], budget: 30, budget_consumed: 28.9, budget_remaining: 1.1, capacity_recovered: 5044, estimated_restore_hours: 1.4 } : null,
    timeline: [stage(0, 'Baseline'), stage(15, 'Rainfall intensifies'), stage(30, 'Thresholds crossed'), stage(45, 'Road disruption'), stage(60, 'Reassessed'), stage(90, 'Response')],
    bottlenecks: [{ road_id: 'R-019', score: 0.1, population_affected: 20000, affected_zone_ids: ['Z-01'], affected_facility_ids: ['H-02'], sole_route_facility_ids: [], status: 'closed', name: 'Bridge R-019', road_type: 'bridge', explanation: 'Losing R-019 reduces access.', baseline_criticality: 0.5 }],
    metric_definitions: { exposed_population: { label: 'Exposed', unit: 'people', better: 'lower', definition: 'Modeled exposure definition' } },
    assumptions: ['Synthetic'], warnings: ['Modeled estimates only'],
  }
}

export const feature = (id: string, coords: number[], props: Record<string, unknown> = {}) => ({ type: 'Feature' as const, id, properties: { id, ...props }, geometry: { type: 'Point' as const, coordinates: coords as [number, number] } })
const coll = (features: unknown[] = []) => ({ type: 'FeatureCollection' as const, features }) as never

export function makeDataset(): Dataset {
  return {
    dataset_version: 'test', simulation_version: '1.0.0', data_label: 'SYNTHETIC', synthetic_data: true,
    layers: { roads: coll(), nodes: coll(), facilities: coll(), zones: coll(), hazards: coll(), infrastructure: coll(), staging: coll(), resources: coll(), boundary: coll(), river: coll() },
    presets: [
      { id: 'baseline', name: 'Baseline neighborhood', description: 'Normal', scenario: BASE_SCENARIO, response_strategy: null },
      { id: 'extreme_rain', name: 'Extreme rainfall', description: 'Heavy', scenario: { ...BASE_SCENARIO, id: 'extreme_rain', name: 'Extreme rainfall', rainfall_mm: 160, drainage_effectiveness: 0.35 }, response_strategy: null },
      { id: 'coordinated_response', name: 'Coordinated emergency response', description: 'Compound plus response', scenario: { ...BASE_SCENARIO, id: 'coordinated_response', rainfall_mm: 150, strategy: 'balanced', closed_road_ids: ['R-019'] }, response_strategy: 'balanced' },
    ],
    strategies: [{ id: 'protect_critical', label: 'Protect critical services', description: '', weights: { crit: 0.55 } }, { id: 'maximize_access', label: 'Maximize population access', description: '', weights: { pop: 0.65 } }, { id: 'balanced', label: 'Balanced community response', description: '', weights: { pop: 0.35 } }],
    resources: [], default_thresholds: BASE_SCENARIO.thresholds, service_thresholds_minutes: { hospital: 20 },
    catalog: { power_nodes: [{ id: 'P-02', name: 'Riverside Substation' }], drainage: [{ id: 'D-01', name: 'Riverside Pump', power_node_id: 'P-02' }], facilities: [{ id: 'H-01', name: 'Civil Hospital', facility_type: 'hospital', power_dependent: true }] },
  }
}
