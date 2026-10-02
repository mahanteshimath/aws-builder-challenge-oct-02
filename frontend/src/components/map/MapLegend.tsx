import { ChevronDown, ChevronUp, Map as MapIcon } from 'lucide-react'
import { useState } from 'react'

const Line = ({ color, dash, w = 4 }: { color: string; dash?: string; w?: number }) => (
  <svg width="26" height="8" aria-hidden><line x1="1" y1="4" x2="25" y2="4" stroke={color} strokeWidth={w} strokeDasharray={dash} strokeLinecap="round" /></svg>
)
const Swatch = ({ color, pattern }: { color: string; pattern?: 'hatch' | 'dots' }) => (
  <svg width="18" height="12" aria-hidden><rect width="18" height="12" rx="2" fill={color} fillOpacity=".45" stroke={color} />
    {pattern === 'hatch' && <path d="M0 12L12 0M6 12L18 0M-6 12L6 0" stroke={color} strokeWidth="1.4" />}
    {pattern === 'dots' && <><circle cx="5" cy="4" r="1.3" fill={color} /><circle cx="12" cy="8" r="1.3" fill={color} /></>}</svg>
)
const Badge = ({ shape, color, label }: { shape: 'none' | 'tri' | 'sq' | 'x'; color: string; label: string }) => (
  <span className="flex items-center gap-1.5"><svg width="16" height="16" aria-hidden><circle cx="8" cy="8" r="6" fill="#0b2a3a" stroke={color} strokeWidth="2" />
    {shape === 'tri' && <path d="M12 1l4 8H8z" fill="#fbbf24" />}{shape === 'sq' && <rect x="9" y="1" width="7" height="7" fill="#fb923c" />}
    {shape === 'x' && <><circle cx="12" cy="4" r="4" fill="#f87171" /><path d="M10.5 2.5l3 3M13.5 2.5l-3 3" stroke="#050a14" strokeWidth="1.2" /></>}</svg>{label}</span>
)

export function MapLegend() {
  const [open, setOpen] = useState(false)
  return (
    <section aria-label="Map legend" className="absolute bottom-7 left-2 z-10 max-h-[70%] w-52 overflow-y-auto rounded-md border border-line2 bg-panel/95 text-[11px] shadow-xl backdrop-blur">
      <button type="button" className="flex w-full items-center justify-between px-2.5 py-1.5 label-xs" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="flex items-center gap-1.5"><MapIcon size={12} /> Legend</span>{open ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
      </button>
      {open && (
        <div className="space-y-2 border-t border-line px-2.5 pb-2 pt-1.5">
          <div><p className="label-xs mb-1">Road condition</p>
            <ul className="space-y-0.5">
              <li className="flex items-center gap-2"><Line color="#5eead4" /> Open</li>
              <li className="flex items-center gap-2"><Line color="#fbbf24" /> Degraded (slower)</li>
              <li className="flex items-center gap-2"><Line color="#fb923c" dash="6 3" /> Restricted (dashed)</li>
              <li className="flex items-center gap-2"><Line color="#ef4444" dash="2 4" w={5} /> Closed (dotted)</li>
              <li className="flex items-center gap-2"><Line color="#e879f9" w={6} /> Critical bottleneck</li>
            </ul></div>
          <div><p className="label-xs mb-1">Flood risk zones</p>
            <ul className="space-y-0.5">
              <li className="flex items-center gap-2"><Swatch color="#fbbf24" /> Watch</li>
              <li className="flex items-center gap-2"><Swatch color="#f97316" pattern="dots" /> Flood risk (dotted)</li>
              <li className="flex items-center gap-2"><Swatch color="#f87171" pattern="hatch" /> Impassable (hatched)</li>
            </ul></div>
          <div><p className="label-xs mb-1">Facility status</p>
            <ul className="space-y-0.5">
              <li><Badge shape="none" color="#22d3ee" label="Accessible" /></li>
              <li><Badge shape="tri" color="#fbbf24" label="Accessible with delay" /></li>
              <li><Badge shape="sq" color="#fb923c" label="Operationally affected" /></li>
              <li><Badge shape="x" color="#f87171" label="Inaccessible" /></li>
            </ul>
            <p className="mt-1 text-muted">Shapes: + hospital, tent shelter, cap school, shield emergency, drop water, bolt power, waves pump, ring = response.</p></div>
          <div><p className="label-xs mb-1">Population zones</p>
            <p className="text-muted">Outline: amber exposed, purple reduced access, red isolated. Cyan line = modeled route; dotted grey = baseline route.</p></div>
        </div>
      )}
    </section>
  )
}


