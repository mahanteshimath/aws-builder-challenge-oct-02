import type { Block, Dataset, Selection } from '@/types'

export interface Highlight { roads: string[]; facilities: string[]; zones: string[]; scenarioRoute: string[]; baselineRoute: string[] }
export const NO_HIGHLIGHT: Highlight = { roads: [], facilities: [], zones: [], scenarioRoute: [], baselineRoute: [] }

/** What to emphasise on the map for the current selection. Pure function; tested. */
export function highlightFor(sel: Selection, block: Block | null, baseline: Block | null, bottlenecks: { road_id: string; affected_zone_ids: string[]; affected_facility_ids: string[] }[], _ds?: Dataset | null): Highlight {
  if (!sel || !block) return NO_HIGHLIGHT
  if (sel.kind === 'road') {
    const b = bottlenecks.find((x) => x.road_id === sel.id)
    return { ...NO_HIGHLIGHT, roads: [sel.id], facilities: b?.affected_facility_ids ?? [], zones: b?.affected_zone_ids ?? [] }
  }
  if (sel.kind === 'facility') {
    const f = block.facilities.find((x) => x.id === sel.id)
    if (!f) return NO_HIGHLIGHT
    const worst = [...f.zones_lost, ...f.zones_delayed][0]
    const zone = worst ?? f.zones_reaching[0]
    const alt = block.alternative_routes.find((a) => a.facility_id === f.id && a.zone_id === zone)
    return { roads: [], facilities: [f.id], zones: [...f.zones_lost, ...f.zones_delayed], scenarioRoute: alt?.scenario_roads ?? block.routes[zone ?? '']?.[f.id]?.roads ?? [],
      baselineRoute: alt?.baseline_roads ?? baseline?.routes[zone ?? '']?.[f.id]?.roads ?? [] }
  }
  if (sel.kind === 'zone') {
    const z = block.zones.find((x) => x.id === sel.id)
    const best = z?.services.hospital.best_facility_id
    const routes = best ? block.routes[sel.id]?.[best]?.roads ?? [] : []
    const baseId = z?.services.hospital.baseline_facility_id
    const baseRoutes = baseId ? baseline?.routes[sel.id]?.[baseId]?.roads ?? [] : []
    return { roads: [], facilities: best ? [best] : [], zones: [sel.id], scenarioRoute: routes, baselineRoute: baseRoutes }
  }
  return NO_HIGHLIGHT
}
