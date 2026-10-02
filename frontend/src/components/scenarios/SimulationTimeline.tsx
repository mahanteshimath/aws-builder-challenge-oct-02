import { SkipBack, SkipForward, Play, RotateCcw, FastForward, Pause } from 'lucide-react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'
import { Button } from '@/components/ui/button'
import { useScenarioStore } from '@/store/scenarioStore'
import { useView } from '@/hooks/useView'
import { cn } from '@/lib/utils'
import { fmtInt, fmtNum } from '@/utils/format'
import { EmptyState } from '@/components/shared/ErrorState'

export function SimulationTimeline() {
  const { result, stageIndex, mode } = useView()
  const { setStage, stepStage, replay, jumpToRecovery, resetToBaseline, playing, stopPlayback } = useScenarioStore()
  if (!result || !result.timeline.length) return <EmptyState title="No timeline" hint="Run a simulation to see scenario stages." />
  const tl = result.timeline
  const current = stageIndex ?? (mode === 'baseline' ? 0 : mode === 'recovery' ? tl.length - 1 : tl.length - 2)
  const data = tl.map((t) => ({ t: `T+${t.t_minutes}`, exposed: t.metrics.exposed_population, roads: t.metrics.roads_affected, reduced: t.metrics.pop_reduced_hospital }))
  return (
    <div className="grid gap-4 p-3 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]" data-testid="timeline-tab">
      <div>
        <div className="mb-2 flex flex-wrap items-center gap-1.5" role="group" aria-label="Timeline controls">
          <Button size="sm" onClick={resetToBaseline}><RotateCcw size={12} /> Reset to baseline</Button>
          <Button size="sm" onClick={() => stepStage(-1)} aria-label="Step backward"><SkipBack size={12} /> Back</Button>
          <Button size="sm" onClick={() => stepStage(1)} aria-label="Step forward"><SkipForward size={12} /> Forward</Button>
          <Button size="sm" variant="primary" onClick={() => (playing ? stopPlayback() : replay())}>{playing ? <><Pause size={12} /> Pause</> : <><Play size={12} /> Replay</>}</Button>
          <Button size="sm" onClick={jumpToRecovery}><FastForward size={12} /> {result.recovery ? 'Jump to recovery' : 'Jump to end'}</Button>
        </div>
        <ol className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
          {tl.map((t, i) => (
            <li key={t.t_minutes}>
              <button type="button" onClick={() => setStage(i)} aria-current={i === current ? 'step' : undefined}
                className={cn('h-full w-full rounded-md border p-2 text-left transition-colors', i === current ? 'border-cyan bg-cyan/10 shadow-glow' : 'border-line bg-panel2/40 hover:border-line2', t.phase === 'recovery' && 'border-ok/40')}>
                <p className="font-mono text-[11px] font-bold text-cyan">T+{String(t.t_minutes).padStart(2, '0')}</p>
                <p className="text-xs font-semibold leading-tight">{t.label}</p>
                <p className="mt-0.5 line-clamp-2 text-[10px] leading-snug text-muted">{t.description}</p>
                <p className="mt-1 text-[10px] tabular-nums text-text/80">{fmtNum(t.rainfall_mm, 0)} mm · {fmtInt(t.metrics.exposed_population)} exposed · {fmtInt(t.metrics.roads_affected)} roads</p>
              </button>
            </li>))}
        </ol>
        <p className="mt-2 text-[10px] text-muted">Stages are illustrative deterministic states (rainfall scaled 0 → 35% → 70% → 100%; closures at T+45; failures at T+60; response at T+90), not a physical flood simulation.</p>
      </div>
      <figure aria-label="Timeline chart of modeled exposure and roads affected">
        <figcaption className="label-xs mb-1">Exposure and road disruption by stage</figcaption>
        <div className="h-52"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ left: -10, right: 8, top: 4 }}>
          <CartesianGrid stroke="#1d2b48" strokeDasharray="3 3" /><XAxis dataKey="t" stroke="#8ca2c4" fontSize={10} /><YAxis yAxisId="l" stroke="#8ca2c4" fontSize={10} /><YAxis yAxisId="r" orientation="right" stroke="#8ca2c4" fontSize={10} />
          <RTooltip contentStyle={{ background: '#0b1324', border: '1px solid #2a3d63', fontSize: 11 }} /><Legend wrapperStyle={{ fontSize: 10 }} />
          <Line yAxisId="l" type="monotone" dataKey="exposed" name="People exposed" stroke="#fbbf24" strokeWidth={2} dot={{ r: 3 }} />
          <Line yAxisId="l" type="monotone" dataKey="reduced" name="Reduced hospital access" stroke="#f87171" strokeWidth={2} strokeDasharray="5 3" dot={{ r: 3 }} />
          <Line yAxisId="r" type="monotone" dataKey="roads" name="Roads affected" stroke="#22d3ee" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart></ResponsiveContainer></div>
      </figure>
    </div>
  )
}
