import { useEffect } from 'react'
import { X } from 'lucide-react'
import { TooltipProvider } from '@/components/ui/tooltip'
import { CommandBar } from './CommandBar'
import { ScenarioControls } from './ScenarioControls'
import { MetricsPanel } from './MetricsPanel'
import { AnalysisWorkspace } from './AnalysisWorkspace'
import { ResilienceMap } from '@/components/map/ResilienceMap'
import { MapLegend } from '@/components/map/MapLegend'
import { MapLayerControl } from '@/components/map/MapLayerControl'
import { FeatureInspector } from '@/components/map/FeatureInspector'
import { ErrorState } from '@/components/shared/ErrorState'
import { LoadingState } from '@/components/shared/LoadingState'
import { useScenarioStore } from '@/store/scenarioStore'
import { cn } from '@/lib/utils'

export function AppShell() {
  const { datasetStatus, datasetError, loadDataset, runError, run, notice, dismissNotice, bottomOpen, dataset, runStatus } = useScenarioStore()
  useEffect(() => { if (datasetStatus === 'idle') void loadDataset() }, [datasetStatus, loadDataset])

  if (datasetStatus === 'idle' || datasetStatus === 'loading') return <div className="flex h-full items-center justify-center"><LoadingState label="Loading synthetic Sahyadri Resilience District" /></div>
  if (datasetStatus === 'error' || !dataset) return <div className="mx-auto max-w-lg pt-24"><ErrorState title="Could not load the simulation dataset" message={datasetError ?? 'Unknown error'} onRetry={() => void loadDataset()} /></div>

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex h-full flex-col" data-testid="app-shell">
        <CommandBar />
        {runError && <ErrorState title="Simulation failed" message={runError} onRetry={() => void run()} />}
        {notice && (
          <div role="status" className={cn('flex items-center gap-2 border-b px-3 py-1 text-xs', notice.kind === 'error' ? 'border-bad/40 bg-bad/10 text-bad' : 'border-cyan/30 bg-cyan/10 text-cyan')}>
            {notice.text}<button type="button" aria-label="Dismiss" className="ml-auto" onClick={dismissNotice}><X size={13} /></button></div>)}
        <main className="grid min-h-0 flex-1 grid-cols-1 overflow-x-hidden overflow-y-auto lg:grid-cols-[250px_minmax(0,1fr)_272px] xl:grid-cols-[300px_minmax(0,1fr)_320px] lg:grid-rows-[minmax(0,1fr)] lg:overflow-hidden">
          <aside aria-label="Scenario controls" className="panel order-2 max-h-[70vh] overflow-hidden border-x-0 border-b-0 lg:order-1 lg:max-h-none lg:border-y-0 lg:border-l-0"><ScenarioControls /></aside>
          <div className="order-1 flex min-h-[420px] min-w-0 flex-col lg:order-2 lg:min-h-0">
            <div className="relative h-[58vh] min-h-[340px] lg:h-auto lg:min-h-0 lg:flex-1" aria-busy={runStatus === 'running'}>
              <ResilienceMap /><MapLayerControl /><MapLegend /><FeatureInspector />
              <p className="pointer-events-none absolute bottom-1 right-2 z-10 rounded bg-ink/70 px-1.5 text-[10px] text-muted">Synthetic demonstration data · modeled estimates · not a flood forecast</p>
            </div>
            <div className={cn('transition-all', bottomOpen ? 'h-[36vh] min-h-[250px]' : 'h-[46px]')}><AnalysisWorkspace /></div>
          </div>
          <aside aria-label="Insights" className="panel order-3 max-h-[70vh] overflow-hidden border-x-0 border-b-0 lg:max-h-none lg:border-y-0 lg:border-r-0"><MetricsPanel /></aside>
        </main>
      </div>
    </TooltipProvider>
  )
}


