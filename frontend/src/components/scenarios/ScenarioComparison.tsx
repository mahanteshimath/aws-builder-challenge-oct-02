import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useScenarioStore } from '@/store/scenarioStore'
import { useView } from '@/hooks/useView'
import { fmtNum } from '@/utils/format'
import { cn } from '@/lib/utils'

export const C = { baseline: '#8ca2c4', disaster: '#fb923c', recovery: '#34d399' }

export function ScenarioComparison() {
  const { result } = useView()
  const { comparison, comparing, compareAll } = useScenarioStore()
  if (!result) return null
  const rows = result.comparison
  const hasRec = !!result.recovery
  const chart = ['exposed_population', 'pop_reduced_hospital', 'pop_reduced_shelter', 'pop_reduced_water'].map((k) => rows.find((r) => r.key === k)!).filter(Boolean)
    .map((r) => ({ name: r.label.replace('Population with reduced ', 'Reduced ').replace('Estimated population in potentially affected zones', 'Exposed'), Baseline: r.baseline, Disaster: r.disaster, ...(hasRec ? { Recovery: r.recovery } : {}) }))
  return (
    <div className="grid gap-4 p-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]" data-testid="comparison">
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]" aria-label="Baseline versus disaster versus recovery">
          <thead><tr className="border-b border-line text-left text-muted"><th className="py-1 font-medium">Metric</th><th className="text-right font-medium">Baseline</th><th className="text-right font-medium">Disaster</th><th className="text-right font-medium">Recovery</th></tr></thead>
          <tbody>{rows.map((r) => {
            const worse = r.delta_disaster != null && r.delta_disaster !== 0 && ((r.better === 'lower' && r.delta_disaster > 0) || (r.better === 'higher' && r.delta_disaster < 0))
            const better = r.delta_recovery != null && r.delta_recovery !== 0 && ((r.better === 'lower' && r.delta_recovery < 0) || (r.better === 'higher' && r.delta_recovery > 0))
            return (<tr key={r.key} className="border-b border-line/50">
              <td className="py-1 pr-2" title={result.metric_definitions[r.key]?.definition}>{r.label}</td>
              <td className="text-right tabular-nums">{fmtNum(r.baseline, 1)}</td>
              <td className={cn('text-right tabular-nums', worse && 'font-semibold text-orange')}>{fmtNum(r.disaster, 1)}{worse && ' ▲'}</td>
              <td className={cn('text-right tabular-nums', better && 'font-semibold text-ok')}>{r.recovery == null ? '—' : fmtNum(r.recovery, 1)}{better && ' ✓'}</td></tr>) })}</tbody>
        </table>
        <p className="mt-1 text-[10px] text-muted">▲ worse than baseline · ✓ improved by response (recovery is a re-run of the engine with interventions). Hover a metric for its definition.</p>
      </div>
      <div className="space-y-3">
        <figure aria-label="Baseline versus disaster versus recovery chart">
          <figcaption className="label-xs mb-1">People: baseline vs disaster{hasRec ? ' vs recovery' : ''}</figcaption>
          <div className="h-48"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart} margin={{ left: -8, right: 4, top: 4 }}>
            <CartesianGrid stroke="#1d2b48" strokeDasharray="3 3" /><XAxis dataKey="name" stroke="#8ca2c4" fontSize={9} interval={0} /><YAxis stroke="#8ca2c4" fontSize={10} />
            <RTooltip contentStyle={{ background: '#0b1324', border: '1px solid #2a3d63', fontSize: 11 }} /><Legend wrapperStyle={{ fontSize: 10 }} />
            <Bar dataKey="Baseline" fill={C.baseline} /><Bar dataKey="Disaster" fill={C.disaster} />{hasRec && <Bar dataKey="Recovery" fill={C.recovery} />}
          </BarChart></ResponsiveContainer></div>
        </figure>
        <div className="rounded-md border border-line p-2">
          <div className="mb-1.5 flex items-center justify-between"><p className="label-xs">Compare all presets (API)</p>
            <Button size="sm" onClick={() => void compareAll()} disabled={comparing}>{comparing && <Loader2 size={12} className="animate-spin" />} Run comparison</Button></div>
          {comparison ? (
            <table className="w-full text-[10px]"><thead><tr className="text-left text-muted"><th className="font-medium">Metric</th>{comparison.metrics[0].values.map((v) => <th key={v.scenario_id} className="text-right font-medium">{v.scenario_name.split(' ')[0]}</th>)}</tr></thead>
              <tbody>{comparison.metrics.filter((m) => ['exposed_population', 'pop_reduced_hospital', 'roads_closed', 'avg_hospital_time_min', 'facilities_inaccessible_some_zone'].includes(m.key)).map((m) => (
                <tr key={m.key} className="border-t border-line/50"><td className="py-0.5">{m.label.replace('Population with reduced hospital accessibility', 'Reduced hospital access').replace('Estimated population in potentially affected zones', 'Exposed people')}</td>{m.values.map((v) => <td key={v.scenario_id} className="text-right tabular-nums">{fmtNum(v.final, 1)}</td>)}</tr>))}</tbody></table>
          ) : <p className="text-[10px] text-muted">Runs the baseline, heavy rainfall, extreme rainfall, closure and compound presets through the comparison endpoint.</p>}
        </div>
      </div>
    </div>
  )
}
