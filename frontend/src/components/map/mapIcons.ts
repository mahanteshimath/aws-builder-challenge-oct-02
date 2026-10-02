import type { Map as MlMap } from 'maplibre-gl'

type Tone = 'ok' | 'delay' | 'ops' | 'bad'
const TONES: Record<Tone, { bg: string; ring: string }> = {
  ok: { bg: '#0b4f66', ring: '#22d3ee' }, delay: { bg: '#6b4a06', ring: '#fbbf24' },
  ops: { bg: '#6b3410', ring: '#fb923c' }, bad: { bg: '#6b1414', ring: '#f87171' },
}
export const FACILITY_KINDS = ['hospital', 'shelter', 'school', 'emergency', 'water'] as const

const S = 48
function canvas(): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas'); c.width = S; c.height = S
  return [c, c.getContext('2d')!]
}
function glyph(ctx: CanvasRenderingContext2D, kind: string) {
  ctx.fillStyle = '#fff'; ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.lineJoin = 'round'
  const cx = 24, cy = 25
  ctx.beginPath()
  switch (kind) {
    case 'hospital': ctx.fillRect(cx - 3, cy - 10, 6, 20); ctx.fillRect(cx - 10, cy - 3, 20, 6); return
    case 'shelter': ctx.moveTo(cx - 11, cy + 9); ctx.lineTo(cx, cy - 10); ctx.lineTo(cx + 11, cy + 9); ctx.closePath(); ctx.fill(); ctx.fillStyle = '#0b1324'; ctx.fillRect(cx - 3, cy + 1, 6, 8); return
    case 'school': ctx.moveTo(cx - 12, cy - 2); ctx.lineTo(cx, cy - 9); ctx.lineTo(cx + 12, cy - 2); ctx.lineTo(cx, cy + 5); ctx.closePath(); ctx.fill(); ctx.moveTo(cx - 6, cy + 2); ctx.lineTo(cx - 6, cy + 9); ctx.lineTo(cx + 6, cy + 9); ctx.lineTo(cx + 6, cy + 2); ctx.stroke(); return
    case 'emergency': ctx.moveTo(cx, cy - 11); ctx.lineTo(cx + 10, cy - 7); ctx.lineTo(cx + 9, cy + 3); ctx.quadraticCurveTo(cx + 6, cy + 9, cx, cy + 12); ctx.quadraticCurveTo(cx - 6, cy + 9, cx - 9, cy + 3); ctx.lineTo(cx - 10, cy - 7); ctx.closePath(); ctx.fill(); return
    case 'water': ctx.moveTo(cx, cy - 11); ctx.bezierCurveTo(cx + 12, cy + 2, cx + 10, cy + 11, cx, cy + 11); ctx.bezierCurveTo(cx - 10, cy + 11, cx - 12, cy + 2, cx, cy - 11); ctx.fill(); return
    case 'power': ctx.moveTo(cx + 3, cy - 12); ctx.lineTo(cx - 8, cy + 2); ctx.lineTo(cx - 1, cy + 2); ctx.lineTo(cx - 3, cy + 12); ctx.lineTo(cx + 8, cy - 3); ctx.lineTo(cx + 1, cy - 3); ctx.closePath(); ctx.fill(); return
    case 'drain': ctx.lineWidth = 3; for (const dy of [-7, 0, 7]) { ctx.moveTo(cx - 11, cy + dy); ctx.quadraticCurveTo(cx - 5, cy + dy - 5, cx, cy + dy); ctx.quadraticCurveTo(cx + 5, cy + dy + 5, cx + 11, cy + dy) } ctx.stroke(); return
    case 'staging': ctx.fillRect(cx - 9, cy - 9, 18, 18); ctx.fillStyle = '#0b1324'; ctx.fillRect(cx - 4, cy - 4, 8, 8); return
    default: ctx.arc(cx, cy, 6, 0, 7); ctx.fill()
  }
}
function badge(ctx: CanvasRenderingContext2D, tone: Tone) {
  if (tone === 'ok') return
  const x = 37, y = 11
  ctx.save(); ctx.lineWidth = 2; ctx.strokeStyle = '#050a14'
  if (tone === 'delay') { ctx.fillStyle = '#fbbf24'; ctx.beginPath(); ctx.moveTo(x, y - 8); ctx.lineTo(x + 8, y + 7); ctx.lineTo(x - 8, y + 7); ctx.closePath(); ctx.fill(); ctx.stroke(); ctx.fillStyle = '#050a14'; ctx.fillRect(x - 1, y - 2, 2, 6) }
  if (tone === 'ops') { ctx.fillStyle = '#fb923c'; ctx.fillRect(x - 7, y - 7, 14, 14); ctx.strokeRect(x - 7, y - 7, 14, 14); ctx.fillStyle = '#050a14'; ctx.beginPath(); ctx.moveTo(x + 1, y - 5); ctx.lineTo(x - 3, y + 1); ctx.lineTo(x, y + 1); ctx.lineTo(x - 1, y + 5); ctx.lineTo(x + 3, y - 1); ctx.lineTo(x, y - 1); ctx.closePath(); ctx.fill() }
  if (tone === 'bad') { ctx.fillStyle = '#f87171'; ctx.beginPath(); ctx.arc(x, y, 8, 0, 7); ctx.fill(); ctx.stroke(); ctx.strokeStyle = '#050a14'; ctx.lineWidth = 2.4; ctx.beginPath(); ctx.moveTo(x - 3.5, y - 3.5); ctx.lineTo(x + 3.5, y + 3.5); ctx.moveTo(x + 3.5, y - 3.5); ctx.lineTo(x - 3.5, y + 3.5); ctx.stroke() }
  ctx.restore()
}
function makeIcon(kind: string, tone: Tone, shape: 'circle' | 'square' = 'circle') {
  const [, ctx] = canvas()
  const { bg, ring } = TONES[tone]
  ctx.fillStyle = bg; ctx.strokeStyle = ring; ctx.lineWidth = 3
  ctx.beginPath()
  if (shape === 'circle') ctx.arc(24, 25, 17, 0, 7); else ctx.roundRect(8, 9, 32, 32, 6)
  ctx.fill(); ctx.stroke()
  glyph(ctx, kind); badge(ctx, tone)
  return ctx.getImageData(0, 0, S, S)
}
function hatch(color: string, gap: number, dots = false) {
  const [c, ctx] = canvas(); c.width = c.height = 16
  ctx.clearRect(0, 0, 16, 16); ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 2
  if (dots) { for (const [x, y] of [[4, 4], [12, 12]]) { ctx.beginPath(); ctx.arc(x, y, 1.6, 0, 7); ctx.fill() } }
  else for (let i = -16; i < 32; i += gap) { ctx.beginPath(); ctx.moveTo(i, 16); ctx.lineTo(i + 16, 0); ctx.stroke() }
  return ctx.getImageData(0, 0, 16, 16)
}
export function registerIcons(map: MlMap) {
  const add = (name: string, img: ImageData, pr = 2) => { if (!map.hasImage(name)) map.addImage(name, img, { pixelRatio: pr }) }
  for (const k of FACILITY_KINDS) for (const t of Object.keys(TONES) as Tone[]) add(`fac-${k}-${t}`, makeIcon(k, t))
  for (const k of ['power', 'drain'] as const) { add(`${k}-ok`, makeIcon(k, 'ok', 'square')); add(`${k}-bad`, makeIcon(k, 'bad', 'square')) }
  add('staging', makeIcon('staging', 'ok', 'square'))
  add('hatch-impassable', hatch('rgba(248,113,113,.85)', 6), 2)
  add('hatch-flood', hatch('rgba(251,146,60,.8)', 8, true), 2)
}


