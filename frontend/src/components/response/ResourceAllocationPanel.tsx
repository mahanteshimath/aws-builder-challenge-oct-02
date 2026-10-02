import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/shared/ErrorState'
import { useScenarioStore } from '@/store/scenarioStore'
import { fmtInt, fmtNum, RESOURCE_LABEL } from '@/utils/format'

export function ResourceAllocationPanel() {
  const plan = useScenarioStore((s) => s.plan)
  const select = useScenarioStore((s) => s.select)
  if (!plan) return <EmptyState title="No response deployed" hint="Choose a strategy and press Deploy response. The optimizer selects interventions within budget, then the engine re-runs to measure recovery." />
  const byType = Object.entries(plan.resources_by_type).map(([k, v]) => ({ name: RESOURCE_LABEL[k] ?? k, units: v }))
  const bc = plan.interventions.map((i, n) => ({ name: `${n + 1}`, ratio: Number((i.benefit_cost_ratio * 100).toFixed(2)), cost: i.cost }))
  return (
    <div className="space-y-3" data-testid="allocation">
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]"><thead><tr className="border-b border-line text-left text-muted"><th className="py-1 font-medium">#</th><th className="font-medium">Action</th><th className="font-medium">Target</th><th className="text-right font-medium">Cost</th><th className="text-right font-medium">Ready</th><th className="text-right font-medium">Benefit/cost</th></tr></thead>
          <tbody>{plan.interventions.map((i, n) => (
            <tr key={`${i.resource_id}-${i.target_id}`} className="cursor-pointer border-b border-line/50 align-top hover:bg-panel2" onClick={() => select({ kind: 'resource', id: `${i.resource_id}:${i.target_id}` })} title={i.reasoning}>
              <td className="py-1 text-muted">{n + 1}</td><td>{i.action}<p className="text-[10px] text-muted">{i.resource_name}</p></td><td>{i.target_id} {i.target_name}</td>
              <td className="text-right tabular-nums">{fmtNum(i.cost, 1)}</td><td className="text-right tabular-nums">{fmtNum(i.deploy_minutes, 0)} min</td><td className="text-right tabular-nums">{fmtNum(i.benefit_cost_ratio * 100, 2)}</td></tr>))}</tbody></table>
        {plan.interventions.length === 0 && <p className="p-2 text-xs text-muted">No feasible beneficial intervention remains for this scenario and budget.</p>}
      </div>
      <ul className="space-y-1 text-[10px] text-muted">{plan.interventions.slice(0, 8).map((i) => <li key={`${i.resource_id}-${i.target_id}-r`}>• {i.reasoning}</li>)}</ul>
      <div className="grid gap-3 sm:grid-cols-2">
        <figure aria-label="Resource allocation by type"><figcaption className="label-xs mb-1">Resource allocation by type</figcaption>
          <div className="h-32"><ResponsiveContainer width="100%" height="100%"><BarChart data={byType} layout="vertical" margin={{ left: 8, right: 8 }}><CartesianGrid stroke="#1d2b48" strokeDasharray="3 3" /><XAxis type="number" allowDecimals={false} stroke="#8ca2c4" fontSize={10} /><YAxis dataKey="name" type="category" width={110} stroke="#8ca2c4" fontSize={9} /><RTooltip contentStyle={{ background: '#0b1324', border: '1px solid #2a3d63', fontSize: 11 }} /><Bar dataKey="units" fill="#22d3ee" /></BarChart></ResponsiveContainer></div></figure>
        <figure aria-label="Estimated benefit versus cost"><figcaption className="label-xs mb-1">Benefit-to-cost ratio by selected action (x100)</figcaption>
          <div className="h-32"><ResponsiveContainer width="100%" height="100%"><BarChart data={bc} margin={{ left: -14, right: 4 }}><CartesianGrid stroke="#1d2b48" strokeDasharray="3 3" /><XAxis dataKey="name" stroke="#8ca2c4" fontSize={10} /><YAxis stroke="#8ca2c4" fontSize={10} /><RTooltip contentStyle={{ background: '#0b1324', border: '1px solid #2a3d63', fontSize: 11 }} /><Bar dataKey="ratio" fill="#34d399" name="benefit/cost x100" /></BarChart></ResponsiveContainer></div></figure>
      </div>
      {plan.not_completed.length > 0 && (
        <div><h4 className="label-xs mb-1">Beneficial interventions that could not be completed</h4>
          <ul className="space-y-0.5 text-[11px]">{plan.not_completed.map((n) => <li key={`${n.resource_id}-${n.target_id}`} className="flex gap-2"><Badge tone="warn">skipped</Badge><span>{RESOURCE_LABEL[n.resource_type]} → {n.target_id} {n.target_name} <span className="text-muted">({fmtNum(n.cost, 1)}) - {n.reason}</span></span></li>)}</ul></div>)}
      <p className="text-[10px] text-muted">{plan.method} Evaluated {fmtInt(plan.candidates_evaluated)} feasible candidates; {fmtInt(plan.candidates_with_benefit)} had standalone modeled benefit. All values are modeled estimates on synthetic data.</p>
    </div>
  )
}
