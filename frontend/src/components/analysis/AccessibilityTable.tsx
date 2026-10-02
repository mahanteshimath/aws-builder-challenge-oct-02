import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { useScenarioStore } from '@/store/scenarioStore'
import { useView } from '@/hooks/useView'
import { cn } from '@/lib/utils'
import { fmtInt, fmtMin, label } from '@/utils/format'
import { EmptyState } from '@/components/shared/ErrorState'
import type { Service } from '@/types'

const tone = (s: string) => (s === 'inaccessible' ? 'bad' : s === 'operationally_affected' ? 'orange' : s === 'accessible_with_delay' ? 'warn' : 'ok') as 'bad' | 'orange' | 'warn' | 'ok'

export function AccessibilityTable() {
  const { block, baseline } = useView()
  const select = useScenarioStore((s) => s.select)
  const [svc, setSvc] = useState<Service>('hospital')
  if (!block || !baseline) return <EmptyState title="No accessibility results" hint="Run a simulation." />
  const facs = block.facilities.filter((f) => f.facility_type === svc)
  return (
    <div className="grid gap-4 p-3 xl:grid-cols-2" data-testid="accessibility-tab">
      <div className="overflow-x-auto">
        <h3 className="label-xs mb-1">Accessibility by population zone (minutes to nearest operating facility)</h3>
        <table className="w-full text-[11px]"><thead><tr className="border-b border-line text-left text-muted">
          <th className="py-1 font-medium">Zone</th><th className="text-right font-medium">Pop.</th>{(['hospital', 'shelter', 'water'] as const).map((s) => <th key={s} className="text-right font-medium capitalize">{s}</th>)}<th className="font-medium pl-2">Status</th></tr></thead>
          <tbody>{block.zones.map((z) => (
            <tr key={z.id} className="cursor-pointer border-b border-line/50 hover:bg-panel2" onClick={() => select({ kind: 'zone', id: z.id })}>
              <td className="py-1"><span className="font-mono text-muted">{z.id}</span> {z.name}</td><td className="text-right tabular-nums">{fmtInt(z.population)}</td>
              {(['hospital', 'shelter', 'water'] as const).map((s) => { const r = z.services[s]; return (
                <td key={s} className={cn('text-right tabular-nums', r.reduced && 'font-semibold text-orange')}>{r.minutes == null ? 'no route' : r.minutes.toFixed(1)}{r.baseline_minutes != null && <span className="text-muted"> ({r.baseline_minutes.toFixed(1)})</span>}{r.reduced && ' ⚠'}</td>) })}
              <td className="pl-2"><Badge tone={z.status === 'isolated' ? 'bad' : z.status === 'reduced_access' ? 'orange' : z.status === 'exposed' ? 'warn' : 'ok'}>{label(z.status)}</Badge></td></tr>))}</tbody></table>
        <p className="mt-1 text-[10px] text-muted">Parentheses show baseline. ⚠ = unreachable, beyond threshold (hospital 20, shelter 25, water 15 min) or ≥25% and ≥2 min slower than baseline.</p>
      </div>
      <div className="overflow-x-auto">
        <div className="mb-1 flex items-center justify-between"><h3 className="label-xs">Facility operation vs reachability</h3>
          <div role="radiogroup" aria-label="Service type" className="flex gap-1">{(['hospital', 'shelter', 'water'] as const).map((s) => (
            <button key={s} role="radio" aria-checked={svc === s} type="button" onClick={() => setSvc(s)} className={cn('rounded border px-2 py-0.5 text-[10px] font-semibold capitalize', svc === s ? 'border-cyan text-cyan' : 'border-line2 text-muted')}>{s}</button>))}</div></div>
        <table className="w-full text-[11px]"><thead><tr className="border-b border-line text-left text-muted"><th className="py-1 font-medium">Facility</th><th className="font-medium">Operation</th><th className="font-medium">Reachability</th><th className="text-right font-medium">Capacity</th><th className="text-right font-medium">Zones cut</th></tr></thead>
          <tbody>{facs.map((f) => (
            <tr key={f.id} className="cursor-pointer border-b border-line/50 hover:bg-panel2" onClick={() => select({ kind: 'facility', id: f.id })}>
              <td className="py-1"><span className="font-mono text-muted">{f.id}</span> {f.name}</td>
              <td><Badge tone={f.operational_status === 'operational' ? 'ok' : f.operational_status === 'reduced' ? 'orange' : 'bad'}>{label(f.operational_status)}</Badge></td>
              <td><Badge tone={tone(f.accessibility_status)}>{label(f.accessibility_status)}</Badge></td>
              <td className="text-right tabular-nums">{fmtInt(f.capacity_available)}/{fmtInt(f.capacity)}</td>
              <td className="text-right tabular-nums">{f.zones_lost.length ? f.zones_lost.join(', ') : '—'}</td></tr>))}</tbody></table>
        <p className="mt-1 text-[10px] text-muted">A facility can be operational but unreachable, or reachable but running at reduced capacity. These are tracked separately. Example travel: {facs[0] ? `${facs[0].id} from Z-01 ${fmtMin(facs[0].minutes_from_zone['Z-01'])}` : ''}.</p>
      </div>
    </div>
  )
}
