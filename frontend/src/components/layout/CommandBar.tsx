import { Download, FileJson, FileSpreadsheet, FileText, HelpCircle, Play, RotateCcw, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { HelpDialog } from '@/components/shared/HelpDialog'
import { useScenarioStore } from '@/store/scenarioStore'
import { cn } from '@/lib/utils'
import type { ViewMode } from '@/types'

function Logo() {
  return (
    <div className="flex items-center gap-2">
      <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden><rect width="32" height="32" rx="7" fill="#0b1324" stroke="#22d3ee" strokeOpacity=".5" /><path d="M5 20c3-5 6-5 9 0s6 5 9 0 3-3 4-3" fill="none" stroke="#22d3ee" strokeWidth="2.4" strokeLinecap="round" /><circle cx="16" cy="11" r="3.2" fill="#f6c343" /></svg>
      <div className="leading-none"><p className="text-[13px] font-extrabold tracking-[0.14em]">RESILIENCE <span className="text-cyan">SIMULATOR</span></p>
        <p className="mt-0.5 hidden text-[10px] text-muted xl:block">Stress-test a neighborhood before disaster strikes.</p></div>
    </div>
  )
}

export function CommandBar() {
  const { scenario, result, mode, setMode, run, reset, runStatus, stale, presetId, stageIndex, dataset, exportReport, exportScenario, importScenario } = useScenarioStore()
  const [menu, setMenu] = useState(false)
  const file = useRef<HTMLInputElement>(null)
  const busy = runStatus === 'running'
  const stage = stageIndex != null ? result?.timeline[stageIndex] : null
  const modes: [ViewMode, string, boolean][] = [['baseline', 'Baseline', !!result], ['scenario', 'Scenario', !!result], ['recovery', 'Recovery', !!result?.recovery]]
  const status = busy ? { t: 'Simulating', tone: 'cyan' as const } : stale ? { t: 'Inputs changed', tone: 'warn' as const } : result ? { t: 'Up to date', tone: 'ok' as const } : { t: 'Idle', tone: 'neutral' as const }
  return (
    <header className="flex min-h-[52px] flex-wrap items-center gap-x-4 gap-y-1 border-b border-line bg-panel px-3 py-1.5" data-testid="command-bar">
      <Logo />
      <div className="hidden min-w-0 border-l border-line pl-4 md:block">
        <p className="label-xs">Neighborhood</p>
        <p className="truncate text-xs font-semibold">Sahyadri Resilience District <Badge tone="warn" className="ml-1">synthetic</Badge></p>
      </div>
      <div className="min-w-0 border-l border-line pl-4">
        <p className="label-xs">Scenario</p>
        <p className="flex items-center gap-1.5 truncate text-xs font-semibold" data-testid="scenario-status">{presetId === 'custom' ? 'Custom scenario' : scenario.name} <Badge tone={status.tone}>{status.t}</Badge></p>
      </div>
      <div className="hidden border-l border-line pl-4 lg:block">
        <p className="label-xs">Sim time</p>
        <p className="font-mono text-xs font-semibold text-cyan" data-testid="sim-time">{stage ? `T+${String(stage.t_minutes).padStart(2, '0')} · ${stage.label}` : mode === 'baseline' ? 'T+00 · Baseline' : mode === 'recovery' ? 'T+90 · Recovery' : 'T+60 · Reassessed'}</p>
      </div>
      <div role="radiogroup" aria-label="View mode" className="ml-auto flex rounded-md border border-line2 p-0.5">
        {modes.map(([m, l, enabled]) => (
          <button key={m} type="button" role="radio" aria-checked={mode === m} disabled={!enabled} onClick={() => setMode(m)}
            className={cn('rounded px-2.5 py-1 text-xs font-semibold disabled:opacity-40', mode === m ? 'bg-cyan/20 text-cyan' : 'text-muted hover:text-text')}>{l}</button>))}
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <Button variant="primary" onClick={() => void run()} disabled={busy} data-testid="run-sim"><Play size={13} /> {busy ? 'Simulating…' : 'Run Simulation'}</Button>
        <Button onClick={() => void reset()} disabled={busy} data-testid="reset-sim"><RotateCcw size={13} /> Reset</Button>
        <div className="relative">
          <Button onClick={() => setMenu(!menu)} aria-expanded={menu} aria-haspopup="menu" disabled={!result} data-testid="export-menu"><Download size={13} /> Export Results</Button>
          {menu && result && (
            <div role="menu" className="absolute right-0 z-40 mt-1 w-56 rounded-md border border-line2 bg-panel p-1 shadow-2xl">
              {([['json', 'Report (JSON)', FileJson], ['csv', 'Impact summary (CSV)', FileSpreadsheet], ['html', 'Printable report (HTML)', FileText]] as const).map(([f, l, I]) => (
                <button key={f} role="menuitem" type="button" className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-panel2" onClick={() => { setMenu(false); void exportReport(f) }}><I size={13} /> {l}</button>))}
              <hr className="my-1 border-line" />
              <button role="menuitem" type="button" className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-panel2" onClick={() => { setMenu(false); exportScenario() }}><FileJson size={13} /> Scenario config (shareable)</button>
              <button role="menuitem" type="button" className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-panel2" onClick={() => file.current?.click()}><Upload size={13} /> Import scenario config…</button>
            </div>)}
          <input ref={file} type="file" accept="application/json,.json" className="hidden" aria-label="Import scenario file" data-testid="import-input"
            onChange={async (e) => { const f = e.target.files?.[0]; setMenu(false); if (f) importScenario(await f.text()); e.target.value = '' }} />
        </div>
        <HelpDialog trigger={<Button variant="ghost" size="icon" aria-label="Help and about"><HelpCircle size={16} /></Button>} version={dataset?.simulation_version ?? ''} />
      </div>
    </header>
  )
}

