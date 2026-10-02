export const fmtInt = (n: number | null | undefined) => (n == null ? '—' : Math.round(n).toLocaleString('en-IN'))
export const fmtNum = (n: number | null | undefined, d = 1) => (n == null ? '—' : Number(n).toFixed(d).replace(/\.0+$/, ''))
export const fmtMin = (n: number | null | undefined) => (n == null ? 'no route' : `${fmtNum(n, 1)} min`)
export const pct = (n: number) => `${Math.round(n * 100)}%`

export const STATUS_LABEL: Record<string, string> = {
  open: 'Open', degraded: 'Degraded', restricted: 'Restricted', closed: 'Closed',
  normal: 'Normal', watch: 'Watch', flood_risk: 'Flood risk', impassable: 'Impassable',
  accessible: 'Accessible', accessible_with_delay: 'Accessible with delay', operationally_affected: 'Operationally affected', inaccessible: 'Inaccessible',
  operational: 'Operational', reduced: 'Reduced capacity', offline: 'Offline',
  exposed: 'Exposed', reduced_access: 'Reduced access', isolated: 'Isolated',
}
export const label = (s: string) => STATUS_LABEL[s] ?? s.replace(/_/g, ' ')

export const RESOURCE_LABEL: Record<string, string> = {
  road_clearance_team: 'Road clearance team', portable_generator: 'Portable generator', temporary_medical_unit: 'Temporary medical unit',
  water_distribution_unit: 'Water distribution unit', temporary_shelter_kit: 'Temporary shelter kit',
}

export function download(filename: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const a = document.createElement('a')
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
