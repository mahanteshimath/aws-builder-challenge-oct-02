import { Info, TrendingDown, TrendingUp } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

interface Props {
  label: string; value: string; unit?: string; definition?: string; delta?: number | null; better?: 'lower' | 'higher' | 'neutral'
  tone?: 'default' | 'warn' | 'bad' | 'ok'; sub?: string; testId?: string
}
export function MetricCard({ label, value, unit, definition, delta, better = 'neutral', tone = 'default', sub, testId }: Props) {
  const good = delta != null && delta !== 0 && ((better === 'lower' && delta < 0) || (better === 'higher' && delta > 0))
  const bad = delta != null && delta !== 0 && ((better === 'lower' && delta > 0) || (better === 'higher' && delta < 0))
  return (
    <div className="rounded-md border border-line bg-panel2/60 p-2.5" data-testid={testId}>
      <div className="flex items-start justify-between gap-1">
        <p className="label-xs leading-tight">{label}</p>
        {definition && (
          <Tooltip>
            <TooltipTrigger asChild><button type="button" aria-label={`Definition: ${label}`} className="text-muted hover:text-cyan"><Info size={12} /></button></TooltipTrigger>
            <TooltipContent>{definition}</TooltipContent>
          </Tooltip>
        )}
      </div>
      <div className="mt-1 flex flex-wrap items-baseline gap-x-1.5 gap-y-0">
        <span className={cn('text-xl font-bold tabular-nums', tone === 'warn' && 'text-warn', tone === 'bad' && 'text-bad', tone === 'ok' && 'text-ok')}>{value}</span>
        {unit && <span className="text-[10px] text-muted">{unit}</span>}
        {delta != null && delta !== 0 && (
          <span className={cn('ml-auto flex items-center gap-0.5 whitespace-nowrap text-[10px] font-semibold', good && 'text-ok', bad && 'text-bad', !good && !bad && 'text-muted')}
            aria-label={`${delta > 0 ? 'up' : 'down'} ${Math.abs(delta)} vs baseline`}>
            {delta > 0 ? <TrendingUp size={11} aria-hidden /> : <TrendingDown size={11} aria-hidden />}{delta > 0 ? '+' : ''}{Number.isInteger(delta) ? delta.toLocaleString('en-IN') : delta}
          </span>
        )}
      </div>
      {sub && <p className="mt-0.5 text-[10px] text-muted">{sub}</p>}
    </div>
  )
}

