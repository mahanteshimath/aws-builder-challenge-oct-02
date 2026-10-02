import { X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useScenarioStore } from '@/store/scenarioStore'
import { useView } from '@/hooks/useView'
import { fmtInt, fmtMin, fmtNum, label, RESOURCE_LABEL } from '@/utils/format'
import { RoadClosureControl } from './RoadClosureControl'
import type { FacilityResult, ZoneResult } from '@/types'

const tone = (s: string) => (['inaccessible', 'offline', 'closed', 'impassable', 'isolated'].includes(s) ? 'bad' : ['operationally_affected', 'reduced', 'restricted', 'flood_risk', 'reduced_access'].includes(s) ? 'orange' : ['accessible_with_delay', 'degraded', 'watch', 'exposed'].includes(s) ? 'warn' : 'ok') as 'bad' | 'orange' | 'warn' | 'ok'

function Row({ k, v }: { k: string; v: React.ReactNode }) { return (<><dt className="text-muted">{k}</dt><dd className="text-right">{v}</dd></>) }

function FacilityView({ f }: { f: FacilityResult }) {
  const { block, baseline, result } = useView()
  const zones = block?.zones ?? []
  const failed = useScenarioStore((s) => s.scenario.failed_facility_ids.includes(f.id))
  const toggleList = useScenarioStore((s) => s.toggleListItem)
  const base = baseline?.facilities.find((x) => x.id === f.id)
  const alt = block?.alternative_routes.filter((a) => a.facility_id === f.id) ?? []
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1"><Badge tone="cyan">{f.facility_type}</Badge><Badge tone={tone(f.operational_status)}>Operation: {label(f.operational_status)}</Badge><Badge tone={tone(f.accessibility_status)}>Reach: {label(f.accessibility_status)}</Badge></div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <Row k="Capacity available" v={`${fmtInt(f.capacity_available)} / ${fmtInt(f.capacity)}`} />
        <Row k="Power dependent" v={f.power_dependent ? 'Yes' : 'No'} />
      </dl>
      <p className="text-[11px] text-muted">{f.operational_reason}</p>
      <div>
        <p className="label-xs mb-1">Travel time from zones (modeled)</p>
        <table className="w-full text-[11px]"><thead><tr className="text-muted"><th className="text-left font-medium">Zone</th><th className="text-right font-medium">Baseline</th><th className="text-right font-medium">Now</th></tr></thead>
          <tbody>{zones.map((z) => { const t = f.minutes_from_zone[z.id]; const b = base?.minutes_from_zone[z.id]; const lost = f.zones_lost.includes(z.id); return (
            <tr key={z.id} className={lost ? 'text-bad' : ''}><td>{z.id} {z.name}</td><td className="text-right">{fmtMin(b)}</td><td className="text-right">{fmtMin(t)}{lost && ' ✕'}</td></tr>) })}</tbody></table>
      </div>
      {alt.length > 0 && <p className="text-[11px] text-muted">{alt.filter((a) => a.status === 'rerouted').length} zone route(s) rerouted; {alt.filter((a) => a.status === 'no_route').length} with no route. Cyan line shows the modeled route for the most affected zone; dotted grey shows baseline.</p>}
      {!f.temporary && result && <Button size="sm" variant={failed ? 'success' : 'danger'} onClick={() => toggleList('failed_facility_ids', f.id)}>{failed ? 'Clear failure' : 'Mark facility as failed'}</Button>}
    </div>
  )
}

function ZoneView({ z }: { z: ZoneResult }) {
  const { block } = useView()
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1"><Badge tone={tone(z.status)}>{label(z.status)}</Badge></div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <Row k="Population (modeled)" v={fmtInt(z.population)} />
        <Row k="Estimated exposure" v={`${fmtInt(z.exposed_population)} (${Math.round(z.exposed_fraction * 100)}%)`} />
        <Row k="Vulnerability-weighted" v={fmtInt(z.vulnerability_weighted_exposure)} />
      </dl>
      <table className="w-full text-[11px]"><thead><tr className="text-muted"><th className="text-left font-medium">Service</th><th className="text-right font-medium">Baseline</th><th className="text-right font-medium">Now</th></tr></thead>
        <tbody>{(['hospital', 'shelter', 'water'] as const).map((s) => { const r = z.services[s]; return (
          <tr key={s} className={r.reduced ? 'text-orange' : ''}><td className="capitalize">{s} {r.best_facility_id && <span className="text-muted">({r.best_facility_id})</span>}</td><td className="text-right">{fmtMin(r.baseline_minutes)}</td><td className="text-right">{fmtMin(r.minutes)}{r.reduced && ' ⚠'}</td></tr>) })}</tbody></table>
      <p className="text-[11px] text-muted">{block?.reachable_facilities_by_zone[z.id]?.hospital.length ?? 0} hospital(s) reachable within {z.services.hospital.threshold_minutes} min. Cyan line = route to the best hospital.</p>
    </div>
  )
}

export function FeatureInspector() {
  const sel = useScenarioStore((s) => s.selection)
  const select = useScenarioStore((s) => s.select)
  const ds = useScenarioStore((s) => s.dataset)
  const scenario = useScenarioStore((s) => s.scenario)
  const toggleList = useScenarioStore((s) => s.toggleListItem)
  const { block, result } = useView()
  if (!sel || !ds) return null
  let title = sel.id, body: React.ReactNode = null
  if (sel.kind === 'road') { title = ds.layers.roads.features.find((f) => f.properties.id === sel.id)?.properties.name ?? sel.id; body = <RoadClosureControl roadId={sel.id} /> }
  else if (sel.kind === 'facility') {
    const f = block?.facilities.find((x) => x.id === sel.id)
    title = f?.name ?? sel.id; body = f ? <FacilityView f={f} /> : <p className="text-xs text-muted">Run a simulation to see status.</p>
  } else if (sel.kind === 'zone') {
    const z = block?.zones.find((x) => x.id === sel.id)
    title = `${sel.id} ${z?.name ?? ''}`; body = z ? <ZoneView z={z} /> : null
  } else if (sel.kind === 'hazard') {
    const h = block?.hazards[sel.id]; const g = ds.layers.hazards.features.find((f) => f.properties.id === sel.id)?.properties
    title = g?.name ?? sel.id
    body = <div className="space-y-1.5 text-[11px]"><Badge tone={tone(h?.hazard_class ?? 'normal')}>{label(h?.hazard_class ?? 'normal')}</Badge>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1"><Row k="Modeled flood risk" v={fmtNum(h?.risk, 2)} /><Row k="Susceptibility" v={fmtNum(g?.susceptibility_score, 2)} /><Row k="Local drainage" v={fmtNum(g?.drainage_effectiveness, 2)} /><Row k="Exposure factor" v={fmtNum(g?.exposure_factor, 2)} /></dl>
      <p className="text-muted">Candidate flood-prone area derived from SRTM terrain and Mithi / nala proximity. Risk is a comparative index, not a forecast.</p></div>
  } else if (sel.kind === 'power' || sel.kind === 'drainage') {
    const info = sel.kind === 'power' ? block?.power[sel.id] : block?.drainage[sel.id]
    const name = (sel.kind === 'power' ? ds.catalog.power_nodes : ds.catalog.drainage).find((x) => x.id === sel.id)?.name ?? sel.id
    title = name
    const key = sel.kind === 'power' ? 'affected_power_nodes' : 'failed_drainage_ids'
    const explicit = scenario[key].includes(sel.id)
    const dependents = sel.kind === 'power' ? ds.catalog.facilities.filter((f) => block?.facilities.find((x) => x.id === f.id)?.power_dependent && ds.layers.facilities.features.find((x) => x.properties.id === f.id)?.properties.power_node_id === sel.id) : []
    body = <div className="space-y-2 text-[11px]"><Badge tone={info?.failed ? 'bad' : 'ok'}>{info?.failed ? 'Failed' : 'Operating'}</Badge><p className="text-muted">{info?.reason}</p>
      {dependents.length > 0 && <p>Dependent facilities: {dependents.map((d) => d.id).join(', ')}</p>}
      <Button size="sm" variant={explicit ? 'success' : 'danger'} onClick={() => toggleList(key, sel.id)}>{explicit ? 'Restore' : sel.kind === 'power' ? 'Simulate outage' : 'Simulate pump failure'}</Button></div>
  } else if (sel.kind === 'resource') {
    const iv = block?.interventions.find((i) => `${i.resource_id}:${i.target_id}` === sel.id)
    const st = ds.layers.staging.features.find((f) => f.properties.id === sel.id)
    title = iv ? iv.resource_name : st?.properties.name ?? sel.id
    body = iv ? <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]"><Row k="Action" v={RESOURCE_LABEL[iv.resource_type]} /><Row k="Target" v={`${iv.target_id} ${iv.target_name}`} /><Row k="Cost" v={`${fmtNum(iv.cost, 1)} lakh`} /><Row k="Ready in" v={`${fmtNum(iv.deploy_minutes, 0)} min`} /></dl>
      : <div className="text-[11px]"><p className="text-muted">Resource staging depot.</p>{ds.resources.filter((r) => r.staging_id === sel.id).map((r) => <p key={r.id}>{r.name} ×{r.quantity_available}</p>)}</div>
  }
  if (!result && sel.kind !== 'resource') body = body ?? <p className="text-xs text-muted">Run a simulation to inspect this feature.</p>
  return (
    <aside aria-label="Feature inspector" className="absolute right-2 top-12 z-10 max-h-[calc(100%-5rem)] w-72 overflow-y-auto rounded-md border border-line2 bg-panel/95 p-3 shadow-2xl">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div><p className="label-xs">{sel.kind} · {sel.id}</p><h2 className="text-sm font-bold leading-tight">{title}</h2></div>
        <button type="button" aria-label="Close inspector" className="rounded p-0.5 text-muted hover:text-text" onClick={() => select(null)}><X size={15} /></button>
      </div>
      {body}
    </aside>
  )
}

