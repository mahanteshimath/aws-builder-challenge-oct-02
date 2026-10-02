import { CloudLightning, CloudRain, CloudSun, ShieldCheck, Siren, Waves } from 'lucide-react'
import { useScenarioStore } from '@/store/scenarioStore'
import { cn } from '@/lib/utils'

const ICONS: Record<string, typeof CloudRain> = { baseline: CloudSun, heavy_rain: CloudRain, extreme_rain: CloudLightning, flood_closure: Waves, compound: Siren, coordinated_response: ShieldCheck }

export function ScenarioGallery() {
  const dataset = useScenarioStore((s) => s.dataset)
  const presetId = useScenarioStore((s) => s.presetId)
  const apply = useScenarioStore((s) => s.applyPreset)
  const busy = useScenarioStore((s) => s.runStatus === 'running')
  if (!dataset) return null
  return (
    <div role="radiogroup" aria-label="Scenario presets" className="grid grid-cols-1 gap-1.5">
      {dataset.presets.map((p, i) => {
        const Icon = ICONS[p.id] ?? CloudRain
        const active = presetId === p.id
        return (
          <button key={p.id} type="button" role="radio" aria-checked={active} disabled={busy} onClick={() => void apply(p.id)} title={p.description}
            className={cn('flex items-start gap-2 rounded-md border px-2 py-1.5 text-left transition-colors disabled:opacity-60', active ? 'border-cyan bg-cyan/10 shadow-glow' : 'border-line bg-panel2/50 hover:border-line2')}>
            <Icon size={15} className={cn('mt-0.5 shrink-0', active ? 'text-cyan' : 'text-muted')} aria-hidden />
            <span className="min-w-0"><span className="block text-xs font-semibold leading-tight">{i + 1}. {p.name}</span>
              <span className="line-clamp-2 block text-[10px] leading-snug text-muted">{p.description}</span></span>
          </button>
        )
      })}
    </div>
  )
}
