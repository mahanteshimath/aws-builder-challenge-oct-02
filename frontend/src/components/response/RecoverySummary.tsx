import { ArrowRight } from 'lucide-react'
import { useScenarioStore } from '@/store/scenarioStore'
import { useView } from '@/hooks/useView'
import { fmtInt, fmtNum } from '@/utils/format'
import { MetricCard } from '@/components/shared/MetricCard'

export function RecoverySummary() {
  const { result } = useView()
  const plan = useScenarioStore((s) => s.plan)
  if (!result?.recovery || !result.recovery_summary) return null
  const r = result.recovery_summary
  const d = result.disaster.metrics, c = result.recovery.metrics
  const restoredNames = r.facilities_restored_or_protected
  return (
    <div className="space-y-2" data-testid="recovery-summary">
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <MetricCard label="Modeled access restored" value={fmtInt(r.population_access_restored)} unit="person-service eq." tone="ok" definition={result.metric_definitions.population_access_restored?.definition} />
        <MetricCard label="Reduced access (any service)" value={fmtInt(c.pop_reduced_any)} unit="people" better="lower" delta={Number(c.pop_reduced_any) - Number(d.pop_reduced_any)} definition={result.metric_definitions.pop_reduced_any?.definition} sub={`was ${fmtInt(d.pop_reduced_any)} in disaster`} />
        <MetricCard label="Budget remaining" value={fmtNum(r.budget_remaining, 1)} unit={`of ${fmtNum(r.budget, 0)} lakh`} sub={`${fmtNum(r.budget_consumed, 1)} spent · ${fmtInt(c.resources_deployed)} resources`} />
        <MetricCard label="Capacity recovered" value={fmtInt(r.capacity_recovered)} better="higher" tone={r.capacity_recovered > 0 ? 'ok' : 'default'} sub={`restore est. ${fmtNum(r.estimated_restore_hours, 1)} h`} />
      </div>
      {plan && <p className="flex flex-wrap items-center gap-1 text-[11px]"><strong>{plan.strategy_label}</strong><ArrowRight size={12} aria-hidden /> {plan.interventions.length} actions, {fmtNum(plan.budget_consumed, 1)} of {fmtNum(plan.budget, 0)} lakh.</p>}
      <p className="text-[11px]">Facilities restored or protected: {restoredNames.length ? restoredNames.join(', ') : 'none beyond reduced-access relief'}. Recovery metrics come from re-running the simulation with the interventions applied.</p>
    </div>
  )
}
