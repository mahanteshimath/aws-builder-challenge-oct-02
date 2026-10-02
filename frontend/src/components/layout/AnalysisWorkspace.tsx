import { ChevronDown, ChevronUp, Loader2, Rocket, Undo2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CriticalBottlenecks } from '@/components/analysis/CriticalBottlenecks'
import { AccessibilityTable } from '@/components/analysis/AccessibilityTable'
import { FacilityStatusChart, RoadConditionChart, ZoneAccessChart } from '@/components/analysis/ImpactCharts'
import { ScenarioComparison } from '@/components/scenarios/ScenarioComparison'
import { SimulationTimeline } from '@/components/scenarios/SimulationTimeline'
import { ResponseStrategySelector } from '@/components/response/ResponseStrategySelector'
import { ResourceAllocationPanel } from '@/components/response/ResourceAllocationPanel'
import { RecoverySummary } from '@/components/response/RecoverySummary'
import { SituationBrief } from '@/components/ai/SituationBrief'
import { EmptyState } from '@/components/shared/ErrorState'
import { Badge } from '@/components/ui/badge'
import { useScenarioStore, type BottomTab } from '@/store/scenarioStore'
import { useView } from '@/hooks/useView'
import { label } from '@/utils/format'

function Infrastructure() {
  const { block, result } = useView()
  if (!block || !result) return <EmptyState title="No impact results" hint="Run a simulation." />
  const failedPower = Object.entries(block.power).filter(([, p]) => p.failed)
  const failedDrain = Object.entries(block.drainage).filter(([, d]) => d.failed)
  return (
    <div className="grid gap-4 p-3 lg:grid-cols-3" data-testid="infrastructure-tab">
      <CriticalBottlenecks />
      <div className="space-y-3"><RoadConditionChart /><FacilityStatusChart /></div>
      <div className="space-y-3 text-xs">
        <div><h3 className="label-xs mb-1">Power & drainage dependencies</h3>
          {failedPower.length === 0 && failedDrain.length === 0 ? <p className="text-muted">No power or pumping failures in this state.</p> :
            <ul className="space-y-1">{failedPower.map(([id, p]) => <li key={id}><Badge tone="bad">power</Badge> {id}: {p.reason}</li>)}{failedDrain.map(([id, d]) => <li key={id}><Badge tone="orange">pump</Badge> {id}: {d.reason}</li>)}</ul>}
          <p className="mt-1 text-[10px] text-muted">Facilities below normal capacity: {block.facilities.filter((f) => f.operational_status !== 'operational').map((f) => `${f.id} (${label(f.operational_status)})`).join(', ') || 'none'}</p></div>
        <ZoneAccessChart />
      </div>
    </div>
  )
}

function Response() {
  const { strategy, optimize, optimizing, plan, clearResponse, scenario } = useScenarioStore()
  const { result } = useView()
  if (!result) return <EmptyState title="Run a simulation first" />
  const hazard = result.disaster.metrics.pop_reduced_any! > 0 || result.disaster.metrics.exposed_population! > 0 || result.disaster.metrics.facilities_operationally_affected! > 0
  return (
    <div className="grid gap-4 p-3 xl:grid-cols-[280px_minmax(0,1fr)]" data-testid="response-tab">
      <div className="space-y-2">
        <h3 className="label-xs">Response strategy</h3>
        <ResponseStrategySelector />
        <div className="flex gap-1.5">
          <Button variant="primary" className="flex-1" disabled={optimizing || !hazard || scenario.resource_budget <= 0} onClick={() => void optimize(strategy)} data-testid="deploy-response">
            {optimizing ? <Loader2 size={13} className="animate-spin" /> : <Rocket size={13} />} Deploy response</Button>
          <Button disabled={!plan} onClick={clearResponse} aria-label="Clear deployed response"><Undo2 size={13} /> Clear</Button>
        </div>
        {!hazard && <p className="text-[10px] text-warn">No modeled impact to respond to. Run a disaster scenario first.</p>}
        {scenario.resource_budget <= 0 && <p className="text-[10px] text-warn">Budget is 0; increase the response budget in Emergency resources.</p>}
      </div>
      <div className="min-w-0 space-y-3"><RecoverySummary /><ResourceAllocationPanel /></div>
    </div>
  )
}

export function AnalysisWorkspace() {
  const { bottomOpen, bottomTab, setBottom } = useScenarioStore()
  const tabs: [BottomTab, string][] = [['timeline', 'Scenario Timeline'], ['infrastructure', 'Infrastructure Impact'], ['accessibility', 'Service Accessibility'], ['response', 'Response Strategies'], ['brief', 'AI Situation Brief']]
  return (
    <section aria-label="Analysis workspace" className="flex min-h-0 flex-col border-t border-line bg-panel" data-testid="analysis-workspace">
      <Tabs value={bottomTab} onValueChange={(v) => setBottom(true, v as BottomTab)} className="flex min-h-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-line px-2 py-1">
          <TabsList aria-label="Analysis tabs" className="flex-1">{tabs.map(([v, l]) => <TabsTrigger key={v} value={v}>{l}</TabsTrigger>)}</TabsList>
          <Button variant="ghost" size="icon" aria-label={bottomOpen ? 'Collapse analysis workspace' : 'Expand analysis workspace'} aria-expanded={bottomOpen} onClick={() => setBottom(!bottomOpen)}>{bottomOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}</Button>
        </div>
        {bottomOpen && (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <TabsContent value="timeline"><SimulationTimeline /><div className="border-t border-line"><ScenarioComparison /></div></TabsContent>
            <TabsContent value="infrastructure"><Infrastructure /></TabsContent>
            <TabsContent value="accessibility"><AccessibilityTable /></TabsContent>
            <TabsContent value="response"><Response /></TabsContent>
            <TabsContent value="brief"><SituationBrief /></TabsContent>
          </div>)}
      </Tabs>
    </section>
  )
}
