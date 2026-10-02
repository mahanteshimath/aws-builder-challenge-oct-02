import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/shared/ErrorState'
import { useScenarioStore } from '@/store/scenarioStore'
import { useView } from '@/hooks/useView'
import { fmtInt, fmtNum } from '@/utils/format'

export function CriticalBottlenecks() {
  const { result } = useView()
  const select = useScenarioStore((s) => s.select)
  const selection = useScenarioStore((s) => s.selection)
  if (!result) return null
  if (!result.bottlenecks.length) return <EmptyState title="No bottlenecks detected" hint="No traversable road removal reduces modeled service access." />
  const max = result.bottlenecks[0].score || 1
  return (
    <div data-testid="bottlenecks">
      <h3 className="label-xs mb-1.5">Critical bottlenecks <span className="normal-case tracking-normal text-muted">- roads whose loss cuts the most modeled service access (score = population-weighted access loss, 0-1)</span></h3>
      <ol className="space-y-1">
        {result.bottlenecks.slice(0, 8).map((b, i) => (
          <li key={b.road_id}>
            <button type="button" onClick={() => select({ kind: 'road', id: b.road_id })} aria-pressed={selection?.kind === 'road' && selection.id === b.road_id}
              className="w-full rounded-md border border-line bg-panel2/40 p-2 text-left hover:border-fuchsia-400/60 aria-pressed:border-fuchsia-400 aria-pressed:bg-fuchsia-400/10">
              <div className="flex items-center gap-2"><span className="font-mono text-[11px] text-muted">#{i + 1}</span><span className="text-xs font-bold">{b.road_id}</span><Badge tone={b.status === 'open' ? 'ok' : 'warn'}>{b.status}</Badge><Badge>{b.road_type}</Badge>
                <span className="ml-auto text-[11px] tabular-nums">score {fmtNum(b.score, 3)}</span></div>
              <div className="mt-1 h-1 overflow-hidden rounded bg-line"><div className="h-full bg-fuchsia-400" style={{ width: `${(b.score / max) * 100}%` }} /></div>
              <p className="mt-1 text-[10px] text-muted">{fmtInt(b.population_affected)} people in {b.affected_zone_ids.join(', ')} · facilities: {b.affected_facility_ids.slice(0, 5).join(', ') || 'none'}{b.sole_route_facility_ids.length ? ` · sole route to ${b.sole_route_facility_ids.slice(0, 3).join(', ')}` : ''}</p>
            </button>
          </li>))}
      </ol>
    </div>
  )
}
