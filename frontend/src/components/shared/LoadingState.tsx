import { Loader2 } from 'lucide-react'
export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center justify-center gap-2 p-6 text-xs text-muted">
      <Loader2 className="animate-spin text-cyan" size={16} /> {label}…
    </div>
  )
}
