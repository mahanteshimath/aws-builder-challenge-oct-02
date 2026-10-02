import { Check } from 'lucide-react'
import { useScenarioStore } from '@/store/scenarioStore'
import { cn } from '@/lib/utils'
import type { Strategy } from '@/types'

const BLURB: Record<Strategy, string> = {
  protect_critical: 'Hospitals, emergency facilities and critical infrastructure first.',
  maximize_access: 'Restore essential-service access for the most people.',
  balanced: 'Criticality + vulnerable exposure + travel time + cost.',
}
const LABEL: Record<Strategy, string> = { protect_critical: 'A · Protect critical services', maximize_access: 'B · Maximize population access', balanced: 'C · Balanced community response' }

export function ResponseStrategySelector() {
  const { strategy, setStrategy, dataset, optimizing } = useScenarioStore()
  if (!dataset) return null
  return (
    <div role="radiogroup" aria-label="Response strategy" className="grid gap-1.5 sm:grid-cols-3 xl:grid-cols-1">
      {dataset.strategies.map((s) => {
        const active = strategy === s.id
        return (
          <button key={s.id} type="button" role="radio" aria-checked={active} disabled={optimizing} onClick={() => setStrategy(s.id)}
            className={cn('rounded-md border p-2 text-left transition-colors', active ? 'border-cyan bg-cyan/10 shadow-glow' : 'border-line bg-panel2/40 hover:border-line2')}>
            <p className="flex items-center gap-1 text-xs font-bold">{active && <Check size={12} className="text-cyan" aria-hidden />}{LABEL[s.id]}</p>
            <p className="mt-0.5 text-[10px] leading-snug text-muted">{BLURB[s.id]}</p>
            <p className="mt-1 text-[9px] text-muted">Weights: {Object.entries(s.weights).map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(' · ')}</p>
          </button>)
      })}
    </div>
  )
}
