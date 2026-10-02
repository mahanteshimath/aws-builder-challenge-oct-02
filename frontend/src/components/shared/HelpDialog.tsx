import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from '@/components/ui/dialog'

export function HelpDialog({ trigger, version }: { trigger: React.ReactNode; version: string }) {
  return (
    <Dialog>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogTitle className="text-base font-extrabold tracking-wide">About Resilience Simulator</DialogTitle>
        <DialogDescription className="mt-1 text-xs text-muted">Stress-test a neighborhood before disaster strikes. Simulation engine v{version}.</DialogDescription>
        <div className="mt-3 space-y-3 text-xs leading-relaxed">
          <p className="rounded border border-warn/40 bg-warn/10 p-2 text-warn"><strong>Real map, modeled attributes.</strong> Roads, Mithi River bridges, rail over-bridges, hospitals, schools, police and fire stations in Kurla (BMC Ward L, Mumbai) come from OpenStreetMap (© OpenStreetMap contributors, ODbL); terrain from SRTM 30 m. Zone populations (scaled from Census 2011 Ward L density), capacities, backup power, power links, most pumps and response resources are <em>modeled planning assumptions</em>, not official BMC data. This is a comparative planning and tabletop-drill tool, not a flood forecast, and not an operational emergency management system.</p>
          <div><h3 className="label-xs mb-1">Try the 90-second demo</h3>
            <ol className="list-decimal space-y-0.5 pl-4"><li>Pick <strong>Extreme rainfall</strong> and press <strong>Run Simulation</strong> - watch the timeline play.</li><li>Click the pink-glow <strong>SCLR rail over-bridge</strong> and <strong>Close this road</strong>; accessibility is re-computed on the road graph.</li><li>Click a hospital or zone to see travel-time changes and alternative routes.</li><li>Open <strong>Response Strategies</strong>, compare <strong>Maximize population access</strong> with <strong>Balanced</strong> and deploy.</li><li>Open <strong>AI Situation Brief</strong> and generate it (Amazon Bedrock, or a labelled rule-based fallback).</li><li>Use <strong>Export Results</strong> for a report.</li></ol></div>
          <div><h3 className="label-xs mb-1">How it works</h3>
            <p>A deterministic engine computes a flood-risk index per road and hazard zone, degrades or closes roads, re-routes with Dijkstra on the road graph, and derives exposure, accessibility, bottlenecks and recovery by re-running the same engine with interventions. AI only explains these outputs.</p></div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
