import type { Block, MapState, SimulationResponse, ViewMode } from '@/types'

export function blockFor(result: SimulationResponse | null, mode: ViewMode): Block | null {
  if (!result) return null
  if (mode === 'baseline') return result.baseline
  if (mode === 'recovery') return result.recovery ?? result.disaster
  return result.disaster
}

export function mapStateFor(result: SimulationResponse | null, mode: ViewMode, stageIndex: number | null): MapState | null {
  if (!result) return null
  if (stageIndex != null && result.timeline[stageIndex]) return result.timeline[stageIndex].map_state
  return blockFor(result, mode)?.map_state ?? null
}

export function hasHazard(s: { rainfall_mm: number; closed_road_ids: string[]; affected_power_nodes: string[]; failed_drainage_ids: string[]; failed_facility_ids: string[] }) {
  return s.rainfall_mm > 0 || s.closed_road_ids.length > 0 || s.affected_power_nodes.length > 0 || s.failed_drainage_ids.length > 0 || s.failed_facility_ids.length > 0
}
