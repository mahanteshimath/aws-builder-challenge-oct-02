import type { Map as MlMap } from 'maplibre-gl'
import { fc } from './mapData'
import type { Dataset } from '@/types'

export const SOURCES = ['zones', 'hazards', 'roads', 'facilities', 'infra', 'response', 'routes', 'halo', 'selroad'] as const
export const LAYER_GROUPS: Record<string, string[]> = {
  boundary: ['boundary-fill', 'boundary-line'], river: ['river-line'], zones: ['zones-fill', 'zones-line'],
  hazards: ['hazards-fill', 'hazards-hatch-flood', 'hazards-hatch-imp', 'hazards-line'],
  roads: ['roads-casing', 'roads-open', 'roads-degraded', 'roads-restricted', 'roads-closed', 'roads-hit'],
  bottlenecks: ['roads-bottleneck'], facilities: ['facilities'], power: ['infra-power'], drainage: ['infra-drain'], staging: ['staging'],
  routes: ['routes-baseline', 'routes-scenario'], response: ['response-ring', 'response-dot'], basemap: ['osm'],
}
export const INTERACTIVE_LAYERS = ['facilities', 'response-dot', 'infra-power', 'infra-drain', 'staging', 'roads-hit', 'hazards-fill', 'zones-fill']

const empty = fc([])

export function addMapLayers(map: MlMap, ds: Dataset) {
  const add = (id: string, data: unknown) => { if (!map.getSource(id)) map.addSource(id, { type: 'geojson', data: data as never, promoteId: 'id' }) }
  map.addSource('osm', { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, maxzoom: 19, attribution: '© OpenStreetMap contributors' })
  add('boundary', ds.layers.boundary); add('river', ds.layers.river)
  for (const s of SOURCES) add(s, empty)
  add('staging', ds.layers.staging)

  const L = (l: object) => map.addLayer(l as never)
  L({ id: 'osm', type: 'raster', source: 'osm', layout: { visibility: 'none' }, paint: { 'raster-opacity': 0.55, 'raster-saturation': -0.8, 'raster-brightness-max': 0.5 } })
  L({ id: 'boundary-fill', type: 'fill', source: 'boundary', paint: { 'fill-color': '#0a1428', 'fill-opacity': 0.75 } })
  L({ id: 'boundary-line', type: 'line', source: 'boundary', paint: { 'line-color': '#2a3d63', 'line-width': 1.5, 'line-dasharray': [4, 3] } })
  L({ id: 'zones-fill', type: 'fill', source: 'zones', paint: { 'fill-color': ['match', ['get', 'status'], 'isolated', '#b91c1c', 'reduced_access', '#a855f7', 'exposed', '#fbbf24', '#1e3a5f'], 'fill-opacity': ['match', ['get', 'status'], 'normal', 0.14, 0.2] } })
  L({ id: 'zones-line', type: 'line', source: 'zones', paint: { 'line-color': ['match', ['get', 'status'], 'isolated', '#f87171', 'reduced_access', '#c084fc', 'exposed', '#fbbf24', '#2a3d63'], 'line-width': ['match', ['get', 'status'], 'normal', 1, 2], 'line-dasharray': [2, 2] } })
  L({ id: 'river-line', type: 'line', source: 'river', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#1d6fa5', 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 6, 15, 22], 'line-opacity': 0.55, 'line-blur': 1.5 } })
  L({ id: 'hazards-fill', type: 'fill', source: 'hazards', paint: { 'fill-color': ['match', ['get', 'cls'], 'impassable', '#dc2626', 'flood_risk', '#f97316', 'watch', '#fbbf24', '#0e7490'], 'fill-opacity': ['match', ['get', 'cls'], 'impassable', 0.5, 'flood_risk', 0.4, 'watch', 0.28, 0.0] } })
  L({ id: 'hazards-hatch-flood', type: 'fill', source: 'hazards', filter: ['==', ['get', 'cls'], 'flood_risk'], paint: { 'fill-pattern': 'hatch-flood' } })
  L({ id: 'hazards-hatch-imp', type: 'fill', source: 'hazards', filter: ['==', ['get', 'cls'], 'impassable'], paint: { 'fill-pattern': 'hatch-impassable' } })
  L({ id: 'hazards-line', type: 'line', source: 'hazards', paint: { 'line-color': ['match', ['get', 'cls'], 'impassable', '#f87171', 'flood_risk', '#fb923c', 'watch', '#fbbf24', 'rgba(14,116,144,.0)'], 'line-width': 1.5 } })
  const rl = { type: 'line', source: 'roads', layout: { 'line-cap': 'round', 'line-join': 'round' } }
  const w = ['match', ['get', 'road_type'], 'arterial', 4.5, 'bridge', 4.5, 'collector', 3.5, 2.6]
  L({ id: 'roads-casing', ...rl, paint: { 'line-color': '#050a14', 'line-width': ['+', w, 2.4] } })
  L({ id: 'roads-bottleneck', ...rl, filter: ['==', ['get', 'bottleneck'], 1], paint: { 'line-color': '#e879f9', 'line-width': ['+', w, 6], 'line-opacity': 0.45, 'line-blur': 2 } })
  L({ id: 'roads-open', ...rl, filter: ['==', ['get', 'status'], 'open'], paint: { 'line-color': '#5eead4', 'line-width': w } })
  L({ id: 'roads-degraded', ...rl, filter: ['==', ['get', 'status'], 'degraded'], paint: { 'line-color': '#fbbf24', 'line-width': w } })
  L({ id: 'roads-restricted', ...rl, filter: ['==', ['get', 'status'], 'restricted'], paint: { 'line-color': '#fb923c', 'line-width': w, 'line-dasharray': [2.2, 1.2] } })
  L({ id: 'roads-closed', ...rl, filter: ['==', ['get', 'status'], 'closed'], paint: { 'line-color': '#ef4444', 'line-width': ['+', w, 1], 'line-dasharray': [0.9, 1.3] } })
  L({ id: 'roads-hit', ...rl, paint: { 'line-color': '#000', 'line-opacity': 0.01, 'line-width': 16 } })
  L({ id: 'selroad-glow', type: 'line', source: 'selroad', paint: { 'line-color': '#22d3ee', 'line-width': 10, 'line-opacity': 0.6, 'line-blur': 3 } })
  L({ id: 'routes-baseline', type: 'line', source: 'routes', filter: ['==', ['get', 'kind'], 'baseline'], layout: { 'line-cap': 'round' }, paint: { 'line-color': '#cbd5e1', 'line-width': 3, 'line-dasharray': [1, 2], 'line-opacity': 0.9 } })
  L({ id: 'routes-scenario', type: 'line', source: 'routes', filter: ['==', ['get', 'kind'], 'scenario'], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#22d3ee', 'line-width': 5, 'line-opacity': 0.95 } })
  L({ id: 'halo', type: 'circle', source: 'halo', paint: { 'circle-radius': 20, 'circle-color': 'rgba(34,211,238,0.12)', 'circle-stroke-color': '#22d3ee', 'circle-stroke-width': 2.5 } })
  L({ id: 'staging', type: 'symbol', source: 'staging', layout: { 'icon-image': 'staging', 'icon-size': 0.6, 'icon-allow-overlap': true } })
  L({ id: 'infra-power', type: 'symbol', source: 'infra', filter: ['==', ['get', 'kind'], 'power'], layout: { 'icon-image': ['get', 'icon'], 'icon-size': 0.7, 'icon-allow-overlap': true } })
  L({ id: 'infra-drain', type: 'symbol', source: 'infra', filter: ['==', ['get', 'kind'], 'drainage'], layout: { 'icon-image': ['get', 'icon'], 'icon-size': 0.62, 'icon-allow-overlap': true } })
  L({ id: 'facilities', type: 'symbol', source: 'facilities', layout: { 'icon-image': ['concat', 'fac-', ['get', 'ftype'], '-', ['get', 'tone']], 'icon-size': ['match', ['get', 'ftype'], 'hospital', 0.95, 'school', 0.62, 0.78], 'icon-allow-overlap': true, 'symbol-sort-key': ['match', ['get', 'ftype'], 'hospital', 5, 'shelter', 4, 'emergency', 3, 'water', 2, 1] } })
  L({ id: 'response-ring', type: 'circle', source: 'response', paint: { 'circle-radius': 17, 'circle-color': 'rgba(52,211,153,.12)', 'circle-stroke-color': '#34d399', 'circle-stroke-width': 2.5, 'circle-stroke-opacity': 0.95 } })
  L({ id: 'response-dot', type: 'circle', source: 'response', paint: { 'circle-radius': 4.5, 'circle-color': '#34d399', 'circle-stroke-color': '#050a14', 'circle-stroke-width': 1.5 } })
}

