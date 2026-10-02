import { Bot, Cpu, Loader2, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ErrorState, EmptyState } from '@/components/shared/ErrorState'
import { useScenarioStore } from '@/store/scenarioStore'
import type { BriefSections } from '@/types'

const SECTIONS: [keyof BriefSections, string][] = [
  ['top_impacts', 'Three most important modeled impacts'], ['critical_bottlenecks', 'Critical infrastructure bottlenecks'],
  ['services_requiring_attention', 'Essential services requiring attention'], ['immediate_actions', 'Suggested immediate actions'],
  ['followup_actions', 'Suggested follow-up actions'], ['resource_tradeoffs', 'Resource allocation trade-offs'], ['uncertainties', 'Remaining uncertainties and assumptions'],
]
const REASON: Record<string, string> = {
  disabled: 'Amazon Bedrock is not enabled for this deployment.', throttled: 'Amazon Bedrock throttled the request.', access_denied: 'Amazon Bedrock access was denied for this model.',
  model_unavailable: 'The configured Amazon Bedrock model is unavailable.', timeout: 'Amazon Bedrock timed out.', error: 'Amazon Bedrock returned an error.',
  invalid_model_output: 'The model output failed structure/grounding validation, so the deterministic brief is shown.', ai_not_requested: 'AI was not requested.',
}

export function SituationBrief() {
  const { brief, briefStatus, briefError, generateBrief, result } = useScenarioStore()
  if (!result) return <EmptyState title="Run a simulation first" hint="The brief explains deterministic simulation output." />
  const ai = brief?.provider === 'bedrock'
  return (
    <div className="grid gap-3 p-3 lg:grid-cols-[260px_minmax(0,1fr)]" data-testid="brief-tab">
      <div className="space-y-2">
        <Button variant="primary" size="lg" className="w-full" onClick={() => void generateBrief()} disabled={briefStatus === 'loading'} data-testid="generate-brief">
          {briefStatus === 'loading' ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} Generate AI Situation Brief
        </Button>
        <p className="text-[10px] leading-snug text-muted">Generated only when you click. The deterministic engine computes every number; Amazon Bedrock only explains them. If Bedrock is unavailable a clearly labelled rule-based brief is produced instead.</p>
        {brief && (
          <div className="rounded-md border border-line p-2 text-[11px]" data-testid="brief-provider">
            <p className="label-xs mb-1">Provider</p>
            <Badge tone={ai ? 'cyan' : 'warn'}>{ai ? <Bot size={11} /> : <Cpu size={11} />} {ai ? 'Amazon Bedrock' : 'Rule-based (not AI)'}</Badge>
            <p className="mt-1 text-muted">{brief.provider_label}</p>
            {brief.model_id && <p className="font-mono text-[10px] text-muted">{brief.model_id}</p>}
            {brief.fallback_reason && <p className="mt-1 text-warn">{REASON[brief.fallback_reason] ?? brief.fallback_reason}</p>}
            <p className="mt-1 text-[10px] text-muted">Sim v{brief.simulation_version} · OSM geography, modeled attributes</p>
          </div>)}
      </div>
      <div className="min-w-0">
        {briefStatus === 'error' && <ErrorState title="Brief failed" message={briefError ?? 'Unknown error'} onRetry={() => void generateBrief()} />}
        {briefStatus === 'loading' && <p role="status" className="p-3 text-xs text-muted">Grounding the brief in simulation output…</p>}
        {!brief && briefStatus === 'idle' && <EmptyState title="No brief yet" hint="Click Generate to create an evidence-grounded brief for the current scenario." />}
        {brief && (
          <article className="space-y-3 text-xs leading-relaxed" aria-label="Situation brief">
            <div><h3 className="label-xs mb-1">Situation summary</h3><p>{brief.sections.situation_summary}</p></div>
            {SECTIONS.map(([k, title]) => (
              <div key={k}><h3 className="label-xs mb-1">{title}</h3><ul className="list-disc space-y-0.5 pl-4">{(brief.sections[k] as string[]).map((s, i) => <li key={i}>{s}</li>)}</ul></div>))}
          </article>)}
      </div>
    </div>
  )
}
