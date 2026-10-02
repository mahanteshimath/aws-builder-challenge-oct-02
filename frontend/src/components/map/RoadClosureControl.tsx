import { Ban, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useScenarioStore } from '@/store/scenarioStore'
import { fmtNum } from '@/utils/format'
import { useView } from '@/hooks/useView'

const tone = (s: string) => (s === 'closed' ? 'bad' : s === 'restricted' ? 'orange' : s === 'degraded' ? 'warn' : 'ok') as 'bad' | 'orange' | 'warn' | 'ok'

export function RoadClosureControl({ roadId }: { roadId: string }) {
  const closed = useScenarioStore((s) => s.scenario.closed_road_ids.includes(roadId))
  const toggle = useScenarioStore((s) => s.toggleRoadClosure)
  const running = useScenarioStore((s) => s.runStatus === 'running')
  const { block, result } = useView()
  const r = block?.roads[roadId]
  const b = result?.bottlenecks.find((x) => x.road_id === roadId)
  return (
    <div className="space-y-2" data-testid="road-closure-control">
      <div className="flex items-center gap-2">
        {r && <Badge tone={tone(r.status)}>{r.status}</Badge>}
        {closed && <Badge tone="bad">explicit closure</Badge>}
      </div>
      {r && <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <dt className="text-muted">Modeled flood risk</dt><dd>{fmtNum(r.risk, 2)} ({r.hazard_class.replace('_', ' ')})</dd>
        <dt className="text-muted">Travel time</dt><dd>{r.travel_minutes == null ? 'closed' : `${fmtNum(r.travel_minutes, 2)} min`} <span className="text-muted">(base {fmtNum(r.base_minutes, 2)})</span></dd>
      </dl>}
      {r?.reason && <p className="text-[11px] text-muted">{r.reason}</p>}
      {b && <p className="rounded border border-fuchsia-400/40 bg-fuchsia-400/10 p-1.5 text-[11px]"><strong>Critical bottleneck</strong> (score {fmtNum(b.score, 3)}): {b.explanation}</p>}
      <Button variant={closed ? 'success' : 'danger'} size="md" className="w-full" disabled={running} onClick={() => toggle(roadId)}>
        {closed ? <><CheckCircle2 size={13} /> Reopen this road</> : <><Ban size={13} /> Close this road</>}
      </Button>
      <p className="text-[10px] text-muted">Closing or reopening re-runs the deterministic simulation (live preview).</p>
    </div>
  )
}
