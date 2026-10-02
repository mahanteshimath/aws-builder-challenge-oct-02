import { useMemo } from 'react'
import { useScenarioStore } from '@/store/scenarioStore'
import { blockFor, mapStateFor } from '@/utils/view'
import { bboxOf } from './mapData'
import type { Dataset } from '@/types'

const ROAD_COLOR = { open: '#5eead4', degraded: '#fbbf24', restricted: '#fb923c', closed: '#ef4444' } as const
const FAC_COLOR = { accessible: '#22d3ee', accessible_with_delay: '#fbbf24', operationally_affected: '#fb923c', inaccessible: '#f87171' } as const

/** Local-data visualization used when WebGL/MapLibre is unavailable. Simple equirectangular projection. */
export function SvgFallbackMap({ ds, reason }: { ds: Dataset; reason: string }) {
  const mode = useScenarioStore((s) => s.mode)
  const result = useScenarioStore((s) => s.result)
  const stage = useScenarioStore((s) => s.stageIndex)
  const select = useScenarioStore((s) => s.select)
  const ms = mapStateFor(result, mode, stage)
  const block = blockFor(result, mode)
  const { project, w, h } = useMemo(() => {
    const [[x0, y0], [x1, y1]] = bboxOf(ds)
    const w = 1000, h = Math.round((w * (y1 - y0)) / (x1 - x0) / 0.95)
    return { w, h, project: (p: number[]) => [((p[0] - x0) / (x1 - x0)) * w, h - ((p[1] - y0) / (y1 - y0)) * h] as [number, number] }
  }, [ds])
  return (
    <div className="relative h-full w-full bg-ink" data-testid="svg-fallback-map">
      <p className="absolute left-2 top-2 z-10 max-w-sm rounded border border-warn/40 bg-panel/90 p-2 text-[11px] text-warn" role="status">
        Interactive map unavailable ({reason}). Showing a simplified local-data view of the synthetic district.
      </p>
      <svg viewBox={`0 0 ${w} ${h}`} className="h-full w-full" role="img" aria-label="Simplified map of the synthetic district">
        {ds.layers.zones.features.map((f) => (
          <polygon key={f.properties.id} points={(f.geometry.coordinates as number[][][])[0].map((p) => project(p).join(',')).join(' ')} fill="#1e3a5f" fillOpacity={0.3} stroke="#2a3d63" strokeDasharray="4 4" />
        ))}
        {ds.layers.roads.features.map((f) => {
          const id = f.properties.id as string; const st = ms?.roads[id]?.[0] ?? 'open'
          return <polyline key={id} onClick={() => select({ kind: 'road', id })} points={(f.geometry.coordinates as number[][]).map((p) => project(p).join(',')).join(' ')} fill="none" stroke={ROAD_COLOR[st]} strokeWidth={st === 'closed' ? 6 : 4} strokeDasharray={st === 'closed' ? '3 7' : st === 'restricted' ? '12 6' : undefined} style={{ cursor: 'pointer' }} />
        })}
        {ds.layers.facilities.features.map((f) => {
          const id = f.properties.id as string; const [x, y] = project(f.geometry.coordinates as number[])
          const st = ms?.facilities[id] ?? 'accessible'
          return <g key={id} onClick={() => select({ kind: 'facility', id })} style={{ cursor: 'pointer' }}><circle cx={x} cy={y} r={9} fill="#0b1324" stroke={FAC_COLOR[st]} strokeWidth={3} /><text x={x} y={y + 3} fontSize="8" textAnchor="middle" fill="#e6edf7">{String(f.properties.facility_type)[0].toUpperCase()}</text></g>
        })}
      </svg>
      {block && <span className="sr-only">{block.metrics.roads_affected} roads affected</span>}
    </div>
  )
}
