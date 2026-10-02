import { Layers } from 'lucide-react'
import { useState } from 'react'
import { Switch } from '@/components/ui/switch'
import { useScenarioStore, type LayerKey } from '@/store/scenarioStore'

const ITEMS: [LayerKey, string][] = [
  ['roads', 'Roads'], ['bottlenecks', 'Critical bottlenecks'], ['hazards', 'Flood-risk zones'], ['zones', 'Population zones'], ['facilities', 'Facilities'],
  ['power', 'Power infrastructure'], ['drainage', 'Drainage pumps'], ['staging', 'Staging locations'], ['response', 'Response deployments'],
  ['routes', 'Routes'], ['river', 'River'], ['boundary', 'District boundary'],
]
export function MapLayerControl() {
  const [open, setOpen] = useState(false)
  const layers = useScenarioStore((s) => s.layers)
  const toggle = useScenarioStore((s) => s.toggleLayer)
  return (
    <div className="absolute right-12 top-2 z-10">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-haspopup="true"
        className="flex h-8 items-center gap-1.5 rounded-md border border-line2 bg-panel/95 px-2.5 text-xs font-semibold text-text hover:border-cyan/60"><Layers size={13} /> Layers</button>
      {open && (
        <div role="group" aria-label="Map layers" className="mt-1 w-56 rounded-md border border-line2 bg-panel/95 p-2 shadow-xl">
          {ITEMS.map(([k, label]) => (
            <label key={k} className="flex cursor-pointer items-center justify-between gap-2 rounded px-1.5 py-1 text-xs hover:bg-panel2">
              <span>{label}</span><Switch checked={layers[k]} onCheckedChange={() => toggle(k)} aria-label={`Toggle ${label}`} />
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

