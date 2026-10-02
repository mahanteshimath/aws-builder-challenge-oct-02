import maplibregl from 'maplibre-gl'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Crosshair, Layers } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useScenarioStore } from '@/store/scenarioStore'
import { blockFor, mapStateFor } from '@/utils/view'
import { highlightFor } from './highlight'
import { registerIcons } from './mapIcons'
import { INTERACTIVE_LAYERS, LAYER_GROUPS, addMapLayers } from './mapLayers'
import { bboxOf, facilitiesData, fc, hazardsData, infraData, responseData, roadLines, roadsData, zonesData } from './mapData'
import { SvgFallbackMap } from './SvgFallbackMap'
import { label } from '@/utils/format'
import type { GeoFeature, Selection } from '@/types'

const STYLE_URL = import.meta.env.VITE_MAP_STYLE_URL as string | undefined
const OFFLINE_STYLE = { version: 8 as const, sources: {}, layers: [{ id: 'bg', type: 'background' as const, paint: { 'background-color': '#050a14' } }] }

function pick(features: maplibregl.MapGeoJSONFeature[]): Selection {
  const order: [string, Selection['kind' & keyof Selection] | string][] = [['facilities', 'facility'], ['infra-power', 'power'], ['infra-drain', 'drainage'], ['response-dot', 'resource'], ['staging', 'resource'], ['roads-hit', 'road'], ['hazards-fill', 'hazard'], ['zones-fill', 'zone']]
  for (const [layer, kind] of order) {
    const f = features.find((x) => x.layer.id === layer)
    if (f) return { kind: kind as never, id: String(f.properties?.id) }
  }
  return null
}
const setData = (map: maplibregl.Map, id: string, data: unknown) => (map.getSource(id) as maplibregl.GeoJSONSource | undefined)?.setData(data as never)

export function ResilienceMap() {
  const box = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const popup = useRef<maplibregl.Popup | null>(null)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState<string | null>(null)
  const [tileError, setTileError] = useState(false)
  const ds = useScenarioStore((s) => s.dataset)!
  const { result, mode, stageIndex, layers, selection, runStatus, playing } = useScenarioStore()
  const select = useScenarioStore((s) => s.select)
  const toggleLayer = useScenarioStore((s) => s.toggleLayer)

  const ms = mapStateFor(result, mode, stageIndex)
  const block = blockFor(result, mode)
  const bottleneckIds = useMemo(() => new Set((result?.bottlenecks ?? []).slice(0, 5).map((b) => b.road_id)), [result])
  const hl = useMemo(() => highlightFor(selection, block, result?.baseline ?? null, result?.bottlenecks ?? []), [selection, block, result])

  useEffect(() => {
    if (!box.current || mapRef.current) return
    let map: maplibregl.Map
    try {
      map = new maplibregl.Map({ container: box.current, style: (STYLE_URL || OFFLINE_STYLE) as never, bounds: bboxOf(ds), fitBoundsOptions: { padding: 40 }, attributionControl: { compact: true }, dragRotate: false, pitchWithRotate: false, maxBounds: [[bboxOf(ds)[0][0] - 0.08, bboxOf(ds)[0][1] - 0.06], [bboxOf(ds)[1][0] + 0.08, bboxOf(ds)[1][1] + 0.06]] })
    } catch (e) {
      setFailed(e instanceof Error ? e.message : 'WebGL not supported'); return
    }
    mapRef.current = map
    if (new URLSearchParams(window.location.search).has('e2e')) (window as unknown as { __rsMap?: maplibregl.Map }).__rsMap = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.on('error', (e) => { if ((e as { sourceId?: string }).sourceId === 'osm') { setTileError(true); useScenarioStore.getState().toggleLayer('basemap') } })
    map.on('load', () => {
      registerIcons(map); addMapLayers(map, ds)
      for (const f of ds.layers.zones.features) {
        const el = document.createElement('div')
        el.textContent = String(f.properties.id)
        el.style.cssText = 'pointer-events:none;font:600 10px Inter,sans-serif;color:#8ca2c4;background:rgba(5,10,20,.7);padding:1px 5px;border-radius:3px;border:1px solid #1d2b48'
        const ring = (f.geometry.coordinates as number[][][])[0]
        const cx = ring.reduce((a, p) => a + p[0], 0) / ring.length; const cy = ring.reduce((a, p) => a + p[1], 0) / ring.length
        new maplibregl.Marker({ element: el }).setLngLat([cx, cy]).addTo(map)
      }
      setReady(true)
    })
    popup.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 })
    let raf = 0
    map.on('mousemove', (e) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const bb: [maplibregl.PointLike, maplibregl.PointLike] = [[e.point.x - 6, e.point.y - 6], [e.point.x + 6, e.point.y + 6]]
        const fs = map.queryRenderedFeatures(bb, { layers: INTERACTIVE_LAYERS.filter((l) => map.getLayer(l)) })
        map.getCanvas().style.cursor = fs.length ? 'pointer' : ''
        const f = fs[0]
        if (!f) { popup.current?.remove(); return }
        const p = f.properties ?? {}
        const line = f.layer.id === 'roads-hit' ? `${p.name} · ${label(String(p.status))}` : f.layer.id === 'hazards-fill' ? `${p.name} · ${label(String(p.cls))}` : f.layer.id === 'zones-fill' ? `${p.id} ${p.name} · ${label(String(p.status))}` : `${p.name ?? p.id}${p.status ? ' · ' + label(String(p.status)) : p.failed === 1 ? ' · failed' : ''}`
        const el = document.createElement('div'); el.textContent = line
        popup.current?.setLngLat(e.lngLat).setDOMContent(el).addTo(map)
      })
    })
    map.on('mouseout', () => popup.current?.remove())
    map.on('click', (e) => {
      const bb: [maplibregl.PointLike, maplibregl.PointLike] = [[e.point.x - 7, e.point.y - 7], [e.point.x + 7, e.point.y + 7]]
      const fs = map.queryRenderedFeatures(bb, { layers: INTERACTIVE_LAYERS.filter((l) => map.getLayer(l)) })
      useScenarioStore.getState().stopPlayback()
      select(pick(fs))
    })
    return () => { map.remove(); mapRef.current = null; setReady(false) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    setData(map, 'roads', roadsData(ds, ms, bottleneckIds, new Set(result?.scenario.closed_road_ids ?? [])))
    setData(map, 'hazards', hazardsData(ds, ms)); setData(map, 'zones', zonesData(ds, ms))
    setData(map, 'facilities', facilitiesData(ds, ms, block)); setData(map, 'infra', infraData(ds, ms))
    setData(map, 'response', stageIndex != null && stageIndex < 5 ? fc([]) : responseData(ds, result))
  }, [ready, ds, ms, block, result, bottleneckIds, stageIndex])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    for (const [key, ids] of Object.entries(LAYER_GROUPS)) for (const id of ids) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', layers[key as keyof typeof layers] ? 'visible' : 'none')
    if (map.getLayer('selroad-glow')) map.setLayoutProperty('selroad-glow', 'visibility', layers.roads ? 'visible' : 'none')
  }, [ready, layers])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    setData(map, 'selroad', fc(roadLines(ds, hl.roads)))
    const facs = ds.layers.facilities.features.filter((f) => hl.facilities.includes(f.properties.id))
    setData(map, 'halo', fc(facs.map((f) => ({ type: 'Feature', properties: { id: f.properties.id }, geometry: f.geometry }) as GeoFeature)))
    const routes = [...roadLines(ds, hl.baselineRoute).map((f) => ({ ...f, properties: { ...f.properties, kind: 'baseline' } })), ...roadLines(ds, hl.scenarioRoute).map((f) => ({ ...f, properties: { ...f.properties, kind: 'scenario' } }))]
    setData(map, 'routes', { type: 'FeatureCollection', features: routes.map((f, i) => ({ ...f, id: `${f.properties.kind}-${i}` })) })
  }, [ready, ds, hl])

  if (failed) return <SvgFallbackMap ds={ds} reason={failed} />
  return (
    <div className="relative h-full w-full" data-testid="map-root">
      <div ref={box} className="absolute inset-0" aria-label="Interactive map of Kurla and the Mithi River, Mumbai" />
      {(runStatus === 'running' || playing) && <div className="scanbar absolute inset-x-0 top-0 z-10 h-0.5 overflow-hidden bg-cyan/20" aria-hidden />}
      <div className="absolute left-2 top-2 z-10 flex flex-col gap-1.5">
        <Button size="sm" variant="secondary" onClick={() => mapRef.current?.fitBounds(bboxOf(ds), { padding: 40, duration: 500 })} aria-label="Fit map to neighborhood"><Crosshair size={13} /> Fit</Button>
        <Button size="sm" variant={layers.basemap ? 'primary' : 'secondary'} aria-pressed={layers.basemap} onClick={() => { setTileError(false); toggleLayer('basemap') }} title="Optional OpenStreetMap basemap (attribution required; subject to OSM tile usage policy)"><Layers size={13} /> OSM basemap</Button>
      </div>
      {tileError && <p role="status" className="absolute bottom-8 left-2 z-10 max-w-xs rounded border border-warn/40 bg-panel/90 p-2 text-[11px] text-warn">Basemap tiles could not be loaded. Showing the local OpenStreetMap-derived layers only.</p>}
    </div>
  )
}

