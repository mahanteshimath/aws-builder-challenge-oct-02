import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'
import { useView } from '@/hooks/useView'
import { C } from '@/components/scenarios/ScenarioComparison'
import { label } from '@/utils/format'

const FAC_COLORS: Record<string, string> = { accessible: '#22d3ee', accessible_with_delay: '#fbbf24', operationally_affected: '#fb923c', inaccessible: '#f87171' }
const tip = { contentStyle: { background: '#0b1324', border: '1px solid #2a3d63', fontSize: 11 } }

export function RoadConditionChart() {
  const { result } = useView()
  if (!result) return null
  const count = (b: typeof result.baseline | null | undefined, s: string) => (b ? Object.values(b.roads).filter((r) => r.status === s).length : 0)
  const blocks: [string, typeof result.baseline | null][] = [['Baseline', result.baseline], ['Disaster', result.disaster], ...(result.recovery ? [['Recovery', result.recovery] as [string, typeof result.baseline]] : [])]
  const data = blocks.map(([name, b]) => ({ name, Open: count(b, 'open'), Degraded: count(b, 'degraded'), Restricted: count(b, 'restricted'), Closed: count(b, 'closed') }))
  return (
    <figure aria-label="Road condition distribution"><figcaption className="label-xs mb-1">Road condition distribution</figcaption>
      <div className="h-44"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ left: 8, right: 8 }}>
        <CartesianGrid stroke="#1d2b48" strokeDasharray="3 3" /><XAxis type="number" stroke="#8ca2c4" fontSize={10} /><YAxis dataKey="name" type="category" stroke="#8ca2c4" fontSize={10} width={62} />
        <RTooltip {...tip} /><Legend wrapperStyle={{ fontSize: 10 }} />
        <Bar dataKey="Open" stackId="a" fill="#5eead4" /><Bar dataKey="Degraded" stackId="a" fill="#fbbf24" /><Bar dataKey="Restricted" stackId="a" fill="#fb923c" /><Bar dataKey="Closed" stackId="a" fill="#ef4444" />
      </BarChart></ResponsiveContainer></div></figure>
  )
}

export function FacilityStatusChart() {
  const { block } = useView()
  if (!block) return null
  const counts: Record<string, number> = {}
  for (const f of block.facilities) counts[f.display_status] = (counts[f.display_status] ?? 0) + 1
  const data = Object.entries(counts).map(([k, v]) => ({ name: label(k), key: k, value: v }))
  return (
    <figure aria-label="Facility status distribution"><figcaption className="label-xs mb-1">Facility status distribution</figcaption>
      <div className="h-44"><ResponsiveContainer width="100%" height="100%"><PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={36} outerRadius={62} paddingAngle={2} label={(e) => `${e.value}`} labelLine={false}>
          {data.map((d) => <Cell key={d.key} fill={FAC_COLORS[d.key]} stroke="#050a14" />)}</Pie>
        <RTooltip {...tip} /><Legend wrapperStyle={{ fontSize: 10 }} /></PieChart></ResponsiveContainer></div></figure>
  )
}

export function ZoneAccessChart() {
  const { result } = useView()
  if (!result) return null
  const cap = 30
  const data = result.disaster.zones.map((z, i) => ({
    name: z.id, Baseline: result.baseline.zones[i].services.hospital.minutes ?? cap, Disaster: z.services.hospital.minutes ?? cap,
    ...(result.recovery ? { Recovery: result.recovery.zones[i].services.hospital.minutes ?? cap } : {}),
  }))
  return (
    <figure aria-label="Travel time to nearest operating hospital by zone"><figcaption className="label-xs mb-1">Minutes to nearest operating hospital (capped at {cap} = no route)</figcaption>
      <div className="h-44"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ left: -12, right: 4 }}>
        <CartesianGrid stroke="#1d2b48" strokeDasharray="3 3" /><XAxis dataKey="name" stroke="#8ca2c4" fontSize={10} /><YAxis stroke="#8ca2c4" fontSize={10} />
        <RTooltip {...tip} /><Legend wrapperStyle={{ fontSize: 10 }} />
        <Bar dataKey="Baseline" fill={C.baseline} /><Bar dataKey="Disaster" fill={C.disaster} />{result.recovery && <Bar dataKey="Recovery" fill={C.recovery} />}
      </BarChart></ResponsiveContainer></div></figure>
  )
}
