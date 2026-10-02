import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide border', {
  variants: {
    tone: {
      neutral: 'border-line2 text-muted bg-panel2', cyan: 'border-cyan/40 text-cyan bg-cyan/10', ok: 'border-ok/40 text-ok bg-ok/10',
      warn: 'border-warn/40 text-warn bg-warn/10', orange: 'border-orange/40 text-orange bg-orange/10', bad: 'border-bad/50 text-bad bg-bad/10',
    },
  },
  defaultVariants: { tone: 'neutral' },
})
export function Badge({ className, tone, ...p }: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...p} />
}
