import type { Block, Dataset, DisplayStatus, GeoCollection, GeoFeature, MapState, SimulationResponse } from '@/types'

export const toneOf = (s: DisplayStatus | undefined) =>
  s === 'inaccessible' ? 'bad' : s === 'operationally_affected' ? 'ops' : s === 'accessible_with_delay' ? 'delay' : 'ok'

const EMPTY: GeoCollection = { type: 'FeatureCollection', features: [] }
export const fc = (features: GeoFeature[]): GeoCollection => ({ type: 'FeatureCollection', features })

export function roadsData(ds: Dataset, ms: MapState | null, bottleneckIds: Set<string>, closedExplicit: Set<string>): GeoCollection {
  return fc(ds.layers.roads.features.map((f) => {
    const id = f.properties.id as string
    const [status, risk] = ms?.roads[id] ?? ['open', 0]
    return { ...f, properties: { id, status, risk, name: f.properties.name, road_type: f.properties.road_type, crit: f.properties.criticality_score ?? 0,
      bottleneck: bottleneckIds.has(id) ? 1 : 0, explicit: closedExplicit.has(id) ? 1 : 0 } }
  }))
}
export function hazardsData(ds: Dataset, ms: MapState | null): GeoCollection {
  return fc(ds.layers.hazards.features.map((f) => {
    const id = f.properties.id as string
    const [cls, risk] = ms?.hazards[id] ?? ['normal', 0]
    return { ...f, properties: { id, name: f.properties.name, cls, risk } }
  }))
}
export function zonesData(ds: Dataset, ms: MapState | null): GeoCollection {
  return fc(ds.layers.zones.features.map((f) => {
    const id = f.properties.id as string
    return { ...f, properties: { id, name: f.properties.name, status: ms?.zones[id] ?? 'normal', pop: f.properties.estimated_population } }
  }))
}
export function facilitiesData(ds: Dataset, ms: MapState | null, block: Block | null): GeoCollection {
  const temp: GeoFeature[] = []
  for (const f of block?.temporary_facilities ?? []) {
    const p = anchorOf(ds, f.id.split('-').slice(1).join('-'))
    if (p) temp.push({ type: 'Feature', properties: { id: f.id, name: f.name, ftype: f.facility_type, tone: 'ok', status: 'accessible' }, geometry: { type: 'Point', coordinates: [p[0] + 0.0008, p[1] - 0.0008] } })
  }
  const base = ds.layers.facilities.features.map((f) => {
    const id = f.properties.id as string
    const st = ms?.facilities[id]
    return { ...f, properties: { id, name: f.properties.name, ftype: f.properties.facility_type, tone: toneOf(st), status: st ?? 'accessible' } }
  })
  return fc([...base, ...temp])
}
export function infraData(ds: Dataset, ms: MapState | null): GeoCollection {
  return fc(ds.layers.infrastructure.features.map((f) => {
    const id = f.properties.id as string
    const failed = f.properties.infra_type === 'power' ? ms?.power[id] : ms?.drainage[id]
    return { ...f, properties: { id, name: f.properties.name, kind: f.properties.infra_type, icon: `${f.properties.infra_type === 'power' ? 'power' : 'drain'}-${failed ? 'bad' : 'ok'}`, failed: failed ? 1 : 0 } }
  }))
}

export function anchorOf(ds: Dataset, zoneId: string): [number, number] | null {
  const z = ds.layers.zones.features.find((f) => f.properties.id === zoneId)
  const node = ds.layers.nodes.features.find((f) => f.properties.id === z?.properties.anchor_node_id)
  return node ? (node.geometry.coordinates as [number, number]) : null
}

export function responseData(ds: Dataset, result: SimulationResponse | null): GeoCollection {
  const ints = result?.recovery?.interventions ?? []
  const feats: GeoFeature[] = []
  for (const i of ints) {
    let pos: [number, number] | null = null
    if (i.resource_type === 'road_clearance_team') {
      const r = ds.layers.roads.features.find((f) => f.properties.id === i.target_id)
      pos = r ? (r.geometry.coordinates as [number, number][])[1] : null
    } else if (i.resource_type === 'portable_generator') {
      const f = [...ds.layers.facilities.features, ...ds.layers.infrastructure.features].find((x) => x.properties.id === i.target_id)
      pos = f ? (f.geometry.coordinates as [number, number]) : null
    } else pos = anchorOf(ds, i.target_id)
    if (pos) feats.push({ type: 'Feature', properties: { id: `${i.resource_id}:${i.target_id}`, name: `${i.resource_name} → ${i.target_name}`, rtype: i.resource_type }, geometry: { type: 'Point', coordinates: pos } })
  }
  return feats.length ? fc(feats) : EMPTY
}

export function roadLines(ds: Dataset, ids: string[]): GeoFeature[] {
  const set = new Set(ids)
  return ds.layers.roads.features.filter((f) => set.has(f.properties.id)).map((f) => ({ type: 'Feature', properties: { id: f.properties.id }, geometry: f.geometry }))
}

export function bboxOf(ds: Dataset): [[number, number], [number, number]] {
  const ring = ds.layers.boundary.features[0].geometry.coordinates as [number, number][][]
  const xs = ring[0].map((p) => p[0]); const ys = ring[0].map((p) => p[1])
  return [[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]]
}

