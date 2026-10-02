import { useScenarioStore } from '@/store/scenarioStore'
import { useView } from '@/hooks/useView'
import { MetricCard } from '@/components/shared/MetricCard'
import { fmtInt, fmtNum } from '@/utils/format'
import { EmptyState } from '@/components/shared/ErrorState'
import { Badge } from '@/components/ui/badge'

export function MetricsPanel() {
  const { result, block, baseline, mode, stage } = useView()
  const scenario = useScenarioStore((s) => s.scenario)
  if (!result || !block || !baseline) return <EmptyState title="No results yet" hint="Run a simulation to see modeled metrics." />
  const m = block.metrics, b = baseline.metrics, defs = result.metric_definitions
  const d = (k: string) => (m[k] != null && b[k] != null ? Number(m[k]) - Number(b[k]) : null)
  const def = (k: string) => defs[k]?.definition
  const budget = scenario.resource_budget
  const used = Number(m.budget_consumed ?? 0)
  const roadsCritical = Number(m.roads_closed ?? 0)
  const tone = (v: number | null | undefined, hi: number, mid = 1): 'default' | 'warn' | 'bad' => (v != null && v >= hi ? 'bad' : v != null && v >= mid ? 'warn' : 'default')
  const shelterOk = Number(m.shelter_capacity_available) >= Number(m.shelter_demand)
  return (
    <div className="flex h-full flex-col overflow-y-auto p-3" data-testid="metrics-panel">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="label-xs">Modeled impact · {stage ? `T+${stage.t_minutes}` : mode}</h2><Badge tone="warn">estimates</Badge>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <MetricCard testId="m-exposed" label="People potentially exposed" value={fmtInt(m.exposed_population)} delta={d('exposed_population')} better="lower" definition={def('exposed_population')} tone={tone(Number(m.exposed_population), 15000, 1)} sub={`of ${fmtInt(m.population_total)} (modeled)`} />
        <MetricCard testId="m-reduced-hospital" label="Reduced hospital access" value={fmtInt(m.pop_reduced_hospital)} unit="people" delta={d('pop_reduced_hospital')} better="lower" definition={def('pop_reduced_hospital')} tone={tone(Number(m.pop_reduced_hospital), 20000, 1)} />
        <MetricCard testId="m-hospitals" label="Hospitals reachable" value={`${m.hospitals_accessible}/${Math.max(Number(b.hospitals_accessible), Number(m.hospitals_accessible))}`} delta={d('hospitals_accessible')} better="higher" definition={def('hospitals_accessible')} tone={Number(m.hospitals_accessible) < Number(b.hospitals_accessible) ? 'warn' : 'ok'} sub={Number(m.hospitals_accessible) > Number(b.hospitals_accessible) ? 'incl. temporary medical units' : undefined} />
        <MetricCard testId="m-inaccessible" label="Facilities cut off from a zone" value={fmtInt(m.facilities_inaccessible_some_zone)} delta={d('facilities_inaccessible_some_zone')} better="lower" definition={def('facilities_inaccessible_some_zone')} />
        <MetricCard testId="m-roads" label="Critical road failures" value={fmtInt(roadsCritical)} unit={`closed · ${fmtInt(m.roads_affected)} affected`} delta={d('roads_closed')} better="lower" definition={def('roads_closed')} tone={tone(roadsCritical, 10, 1)} />
        <MetricCard testId="m-power" label="Power-dependent affected" value={fmtInt(m.electricity_dependent_affected)} delta={d('electricity_dependent_affected')} better="lower" definition={def('electricity_dependent_affected')} />
        <MetricCard testId="m-shelter" label="Shelter capacity vs demand" value={`${fmtInt(m.shelter_capacity_available)}`} unit={`/ ${fmtInt(m.shelter_demand)} demand`} better="higher" definition={def('shelter_shortfall')} tone={shelterOk ? 'ok' : 'bad'} sub={shelterOk ? 'Capacity covers modeled demand' : `Shortfall ${fmtInt(m.shelter_shortfall)}`} />
        <MetricCard testId="m-time" label="Avg hospital travel time" value={fmtNum(m.avg_hospital_time_min as number | null, 1)} unit="min" delta={d('avg_hospital_time_min') != null ? Number(fmtNum(d('avg_hospital_time_min'), 1)) : null} better="lower" definition={def('avg_hospital_time_min')} />
        <MetricCard testId="m-noroute" label="Zones with no feasible route" value={fmtInt(m.zones_no_feasible_route)} unit="of 8 zones" delta={d('zones_no_feasible_route')} better="lower" definition={def('zones_no_feasible_route')} tone={tone(Number(m.zones_no_feasible_route), 2, 1)} />
        <MetricCard testId="m-capacity" label="Service capacity available" value={fmtInt(m.service_capacity_available)} delta={d('service_capacity_available')} better="higher" definition={def('service_capacity_available')} />
        <MetricCard testId="m-restore" label="Est. time to restore access" value={fmtNum(block.estimated_restore_hours, 1)} unit="h" definition="Heuristic: natural recession (0.5 x event duration + 10 x peak road risk + 3 h for explicit closures) or, with a response, the longest deployment time. Illustrative." />
        <MetricCard testId="m-budget" label="Response budget used" value={`${fmtNum(used, 1)}`} unit={`/ ${fmtNum(budget, 0)} lakh`} definition={def('budget_consumed')} sub={budget > 0 ? `${Math.round((used / budget) * 100)}% utilised · ${Number(m.resources_deployed)} resources` : undefined} />
      </div>
      {result.recovery_summary && mode === 'recovery' && (
        <div className="mt-2 rounded-md border border-ok/40 bg-ok/10 p-2.5" data-testid="restored-callout">
          <p className="label-xs text-ok">Modeled access restored</p>
          <p className="text-xl font-bold tabular-nums text-ok">{fmtInt(result.recovery_summary.population_access_restored)} <span className="text-[10px] font-normal text-muted">person-service equivalents</span></p>
        </div>)}
      {result.warnings.length > 0 && <ul className="mt-3 space-y-1 text-[10px] leading-snug text-muted">{result.warnings.map((w, i) => <li key={i}>• {w}</li>)}</ul>}
    </div>
  )
}

