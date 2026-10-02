import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
export function ErrorState({ title = 'Something went wrong', message, onRetry }: { title?: string; message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="m-3 flex items-start gap-3 rounded-md border border-bad/40 bg-bad/10 p-3 text-xs">
      <AlertTriangle className="mt-0.5 shrink-0 text-bad" size={16} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-bad">{title}</p>
        <p className="mt-0.5 break-words text-text/90">{message}</p>
      </div>
      {onRetry && <Button size="sm" variant="danger" onClick={onRetry}><RotateCcw size={12} /> Retry</Button>}
    </div>
  )
}
export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 p-6 text-center text-xs text-muted">
      <p className="font-semibold text-text/80">{title}</p>{hint && <p>{hint}</p>}
    </div>
  )
}
