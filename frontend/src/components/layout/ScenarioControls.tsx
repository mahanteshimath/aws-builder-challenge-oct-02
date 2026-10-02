import { useEffect, useState } from 'react'
import { Play, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ScenarioGallery } from '@/components/scenarios/ScenarioGallery'
import { useScenarioStore } from '@/store/scenarioStore'
import { budgetSchema, rainfallSchema } from '@/utils/schema'
import { cn } from '@/lib/utils'
import { fmtNum } from '@/utils/format'

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="border-b border-line px-3 py-3">
      <div className="mb-2 flex items-center justify-between"><h3 className="label-xs">{title}</h3>
        {hint && <Tooltip><TooltipTrigger asChild><button type="button" className="text-[10px] text-muted underline decoration-dotted" aria-label={`About ${title}`}>?</button></TooltipTrigger><TooltipContent>{hint}</TooltipContent></Tooltip>}</div>
      {children}
    </section>
  )
}

function NumberField({ id, value, min, max, step = 1, unit, onCommit, schema }: { id: string; value: number; min: number; max: number; step?: number; unit: string; onCommit: (n: number) => void; schema: { safeParse: (v: unknown) => { success: boolean } } }) {
  const [text, setText] = useState(String(value))
  useEffect(() => setText(String(value)), [value])
  const n = Number(text)
  const invalid = text.trim() === '' || Number.isNaN(n) || !schema.safeParse(n).success
  return (
    <div className="flex items-center gap-1">
      <input id={id} inputMode="decimal" type="number" min={min} max={max} step={step} value={text} aria-invalid={invalid}
        aria-describedby={invalid ? `${id}-err` : undefined}
        onChange={(e) => { setText(e.target.value); const v = Number(e.target.value); if (e.target.value.trim() !== '' && !Number.isNaN(v) && schema.safeParse(v).success) onCommit(v) }}
        className={cn('h-7 w-16 rounded border bg-ink px-1.5 text-right text-xs tabular-nums', invalid ? 'border-bad' : 'border-line2')} />
      <span className="text-[10px] text-muted">{unit}</span>
      {invalid && <span id={`${id}-err`} role="alert" className="text-[10px] text-bad">{min}–{max}</span>}
    </div>
  )
}

export function ScenarioControls() {
  const { scenario, dataset, setScenario, toggleListItem, toggleRoadClosure, run, runStatus, stale, select } = useScenarioStore()
  if (!dataset) return null
  const busy = runStatus === 'running'
  const bottleneckRoads = [...dataset.layers.roads.features].sort((a, b) => (b.properties.criticality_score ?? 0) - (a.properties.criticality_score ?? 0)).slice(0, 12)
  const hospitals = dataset.catalog.facilities.filter((f) => f.power_dependent || f.facility_type === 'hospital')
  return (
    <div className="flex h-full flex-col overflow-y-auto" data-testid="scenario-controls">
      <Section title="Scenario presets"><ScenarioGallery /></Section>

      <Section title="Rainfall" hint="Total rainfall over the selected window. Shorter windows mean higher intensity. Illustrative; not a forecast.">
        <div className="mb-1.5 flex items-center justify-between"><label htmlFor="rain" className="text-xs">Rainfall intensity</label>
          <NumberField id="rain" value={scenario.rainfall_mm} min={0} max={200} unit="mm" schema={rainfallSchema} onCommit={(n) => setScenario({ rainfall_mm: n })} /></div>
        <Slider aria-label="Rainfall in millimetres" min={0} max={200} step={5} value={[scenario.rainfall_mm]} onValueChange={([v]) => setScenario({ rainfall_mm: v })} />
        <div className="mt-2 flex items-center justify-between"><label htmlFor="dur" className="text-xs">Time window</label>
          <select id="dur" value={scenario.duration_hours} onChange={(e) => setScenario({ duration_hours: Number(e.target.value) })} className="h-7 rounded border border-line2 bg-ink px-1.5 text-xs">
            {[1, 3, 6, 12, 24, 48, 72].map((h) => <option key={h} value={h}>{h} h</option>)}</select></div>
      </Section>

      <Section title="Terrain & drainage" hint="Susceptibility scales local flood risk. Drainage effectiveness reduces it (1 = excellent).">
        <div role="radiogroup" aria-label="Flood susceptibility preset" className="mb-2.5 grid grid-cols-3 gap-1">
          {(['low', 'moderate', 'high'] as const).map((p) => (
            <button key={p} type="button" role="radio" aria-checked={scenario.susceptibility_preset === p} onClick={() => setScenario({ susceptibility_preset: p })}
              className={cn('rounded border py-1 text-[11px] font-semibold capitalize', scenario.susceptibility_preset === p ? 'border-cyan bg-cyan/15 text-cyan' : 'border-line2 text-muted hover:text-text')}>{p}</button>))}
        </div>
        <div className="mb-1 flex justify-between text-xs"><span>Drainage effectiveness</span><span className="tabular-nums">{Math.round(scenario.drainage_effectiveness * 100)}%</span></div>
        <Slider aria-label="Drainage effectiveness percent" min={0} max={100} step={5} value={[Math.round(scenario.drainage_effectiveness * 100)]} onValueChange={([v]) => setScenario({ drainage_effectiveness: v / 100 })} />
      </Section>

      <Section title="Road closures" hint="Click any road on the map to close or reopen it (live re-run), or pick a high-criticality road here.">
        <select aria-label="Add road closure" value="" onChange={(e) => e.target.value && toggleRoadClosure(e.target.value)} className="mb-2 h-7 w-full rounded border border-line2 bg-ink px-1.5 text-xs">
          <option value="">Close a critical road…</option>
          {bottleneckRoads.filter((r) => !scenario.closed_road_ids.includes(r.properties.id)).map((r) => <option key={r.properties.id} value={r.properties.id}>{r.properties.id} · {r.properties.road_type} · criticality {fmtNum(r.properties.criticality_score, 2)}</option>)}
        </select>
        {scenario.closed_road_ids.length === 0 ? <p className="text-[11px] text-muted">No explicit closures. Click a road on the map.</p> :
          <ul className="flex flex-wrap gap-1">{scenario.closed_road_ids.map((id) => (
            <li key={id}><button type="button" onClick={() => select({ kind: 'road', id })} className="flex items-center gap-1 rounded border border-bad/50 bg-bad/10 px-1.5 py-0.5 text-[11px] text-bad">{id}
              <span role="button" tabIndex={0} aria-label={`Reopen ${id}`} onClick={(e) => { e.stopPropagation(); toggleRoadClosure(id) }} onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); toggleRoadClosure(id) } }}><X size={11} /></span></button></li>))}</ul>}
      </Section>

      <Section title="Power & infrastructure failure" hint="Power outages reduce dependent facilities (backup power helps for its rated hours) and can stop drainage pumps.">
        <ul className="space-y-1.5">
          {dataset.catalog.power_nodes.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2 text-xs"><label htmlFor={`pw-${p.id}`} className="min-w-0 truncate">{p.id} · {p.name}</label>
              <Switch id={`pw-${p.id}`} checked={scenario.affected_power_nodes.includes(p.id)} onCheckedChange={() => toggleListItem('affected_power_nodes', p.id)} aria-label={`Power outage at ${p.name}`} /></li>))}
        </ul>
        <details className="mt-2 text-xs"><summary className="cursor-pointer text-muted hover:text-text">Critical facility & pump failures ({scenario.failed_facility_ids.length + scenario.failed_drainage_ids.length})</summary>
          <ul className="mt-1.5 space-y-1">
            {dataset.catalog.drainage.map((d) => <li key={d.id} className="flex items-center justify-between gap-2"><label htmlFor={`dr-${d.id}`} className="truncate">{d.id} · {d.name}</label><Switch id={`dr-${d.id}`} checked={scenario.failed_drainage_ids.includes(d.id)} onCheckedChange={() => toggleListItem('failed_drainage_ids', d.id)} aria-label={`Fail pump ${d.name}`} /></li>)}
            {hospitals.filter((f) => f.facility_type === 'hospital').map((f) => <li key={f.id} className="flex items-center justify-between gap-2"><label htmlFor={`fc-${f.id}`} className="truncate">{f.id} · {f.name}</label><Switch id={`fc-${f.id}`} checked={scenario.failed_facility_ids.includes(f.id)} onCheckedChange={() => toggleListItem('failed_facility_ids', f.id)} aria-label={`Fail facility ${f.name}`} /></li>)}
          </ul></details>
      </Section>

      <Section title="Emergency resources" hint="Budget in illustrative INR lakh. Availability scales each resource pool (rounded down).">
        <div className="mb-1.5 flex items-center justify-between"><label htmlFor="budget" className="text-xs">Response budget</label>
          <NumberField id="budget" value={scenario.resource_budget} min={0} max={1000} unit="lakh" schema={budgetSchema} onCommit={(n) => setScenario({ resource_budget: n })} /></div>
        <Slider aria-label="Response budget" min={0} max={100} step={1} value={[Math.min(100, scenario.resource_budget)]} onValueChange={([v]) => setScenario({ resource_budget: v })} />
        <div className="mb-1 mt-2.5 flex justify-between text-xs"><span>Resource availability</span><span className="tabular-nums">{Math.round(scenario.resource_availability * 100)}%</span></div>
        <Slider aria-label="Resource availability percent" min={0} max={100} step={10} value={[Math.round(scenario.resource_availability * 100)]} onValueChange={([v]) => setScenario({ resource_availability: v / 100 })} />
        <ul className="mt-2 grid grid-cols-2 gap-x-2 text-[10px] text-muted">{dataset.resources.map((r) => <li key={r.id} className="truncate">{r.name} ×{Math.floor(r.quantity_available * scenario.resource_availability + 1e-9)}</li>)}</ul>
      </Section>

      <div className="sticky bottom-0 mt-auto bg-panel/95 p-3 backdrop-blur">
        <Button variant="primary" size="lg" className="w-full" disabled={busy} onClick={() => void run()} data-testid="run-sim-left">
          <Play size={14} /> {busy ? 'Simulating…' : stale ? 'Run Simulation (inputs changed)' : 'Run Simulation'}
        </Button>
      </div>
    </div>
  )
}
