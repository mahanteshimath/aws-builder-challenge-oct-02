import { create } from 'zustand'
import { api, ApiError } from '@/services/api'
import { parseScenario } from '@/utils/schema'
import { download } from '@/utils/format'
import { hasHazard } from '@/utils/view'
import type { Brief, Dataset, OptimizeResponse, Plan, Scenario, Selection, SimulationResponse, Strategy, ViewMode, CompareResponse } from '@/types'

type Status = 'idle' | 'loading' | 'ready' | 'error'
export type BottomTab = 'timeline' | 'infrastructure' | 'accessibility' | 'response' | 'brief'

export const DEFAULT_LAYERS = {
  boundary: true, river: true, zones: true, hazards: true, roads: true, facilities: true, power: true, drainage: true,
  staging: true, routes: true, response: true, bottlenecks: true, basemap: false,
} as const
export type LayerKey = keyof typeof DEFAULT_LAYERS

interface State {
  dataset: Dataset | null; datasetStatus: Status; datasetError: string | null
  scenario: Scenario; presetId: string
  result: SimulationResponse | null; runStatus: 'idle' | 'running'; runError: string | null; stale: boolean
  mode: ViewMode; stageIndex: number | null; playing: boolean
  plan: Plan | null; optimizing: boolean; strategy: Strategy
  brief: Brief | null; briefStatus: 'idle' | 'loading' | 'error'; briefError: string | null
  comparison: CompareResponse | null; comparing: boolean
  selection: Selection; layers: Record<LayerKey, boolean>
  bottomOpen: boolean; bottomTab: BottomTab
  notice: { kind: 'error' | 'info'; text: string } | null

  loadDataset: () => Promise<void>
  setScenario: (patch: Partial<Scenario>, opts?: { keepResponse?: boolean }) => void
  applyPreset: (id: string) => Promise<void>
  toggleRoadClosure: (id: string) => void
  toggleListItem: (key: 'affected_power_nodes' | 'failed_drainage_ids' | 'failed_facility_ids', id: string) => void
  run: () => Promise<void>
  optimize: (strategy?: Strategy) => Promise<void>
  clearResponse: () => void
  reset: () => Promise<void>
  setMode: (m: ViewMode) => void
  setStage: (i: number | null) => void
  stepStage: (d: 1 | -1) => void
  replay: () => void
  stopPlayback: () => void
  jumpToRecovery: () => void
  resetToBaseline: () => void
  select: (s: Selection) => void
  toggleLayer: (k: LayerKey) => void
  setBottom: (open: boolean, tab?: BottomTab) => void
  generateBrief: () => Promise<void>
  exportReport: (fmt: 'json' | 'csv' | 'html') => Promise<void>
  exportScenario: () => void
  importScenario: (text: string) => void
  compareAll: () => Promise<void>
  setStrategy: (s: Strategy) => void
  dismissNotice: () => void
}

let runCtrl: AbortController | null = null
let runSeq = 0
let timer: ReturnType<typeof setInterval> | null = null

const errText = (e: unknown) => (e instanceof ApiError ? (e.details?.length ? `${e.message}: ${e.details.map((d) => `${d.field} ${d.message}`).join('; ')}` : e.message) : 'Unexpected error')

export const BASE_SCENARIO: Scenario = {
  id: 'baseline', name: 'Baseline neighborhood', rainfall_mm: 0, duration_hours: 6, drainage_effectiveness: 0.5, susceptibility_preset: 'moderate',
  closed_road_ids: [], affected_power_nodes: [], failed_drainage_ids: [], failed_facility_ids: [], resource_budget: 30, resource_availability: 1,
  strategy: null, deployed_resources: [],
  thresholds: { watch: 0.25, flood_risk: 0.5, impassable: 0.75, degraded_penalty: 1.3, restricted_penalty: 2.5, delay_ratio: 1.25 },
  simulation_version: '1.0.0',
}

const HAZARD_KEYS: (keyof Scenario)[] = ['rainfall_mm', 'duration_hours', 'drainage_effectiveness', 'susceptibility_preset', 'closed_road_ids',
  'affected_power_nodes', 'failed_drainage_ids', 'failed_facility_ids', 'resource_budget', 'resource_availability']

export const useScenarioStore = create<State>((set, get) => ({
  dataset: null, datasetStatus: 'idle', datasetError: null,
  scenario: BASE_SCENARIO, presetId: 'baseline',
  result: null, runStatus: 'idle', runError: null, stale: false,
  mode: 'baseline', stageIndex: null, playing: false,
  plan: null, optimizing: false, strategy: 'balanced',
  brief: null, briefStatus: 'idle', briefError: null,
  comparison: null, comparing: false,
  selection: null, layers: { ...DEFAULT_LAYERS },
  bottomOpen: true, bottomTab: 'timeline', notice: null,

  loadDataset: async () => {
    set({ datasetStatus: 'loading', datasetError: null })
    try {
      const dataset = await api.dataset()
      const base = dataset.presets.find((p) => p.id === 'baseline')?.scenario ?? BASE_SCENARIO
      set({ dataset, datasetStatus: 'ready', scenario: base, presetId: 'baseline' })
      await get().run()
    } catch (e) {
      set({ datasetStatus: 'error', datasetError: errText(e) })
    }
  },

  setScenario: (patch, opts) => {
    const cur = get().scenario
    const touchesHazard = HAZARD_KEYS.some((k) => k in patch && JSON.stringify(patch[k]) !== JSON.stringify(cur[k]))
    const next: Scenario = { ...cur, ...patch }
    if (touchesHazard && !opts?.keepResponse) { next.deployed_resources = []; next.strategy = null }
    set({ scenario: next, presetId: 'custom', stale: true, ...(touchesHazard && !opts?.keepResponse ? { plan: null, brief: null } : {}) })
  },

  applyPreset: async (id) => {
    const p = get().dataset?.presets.find((x) => x.id === id)
    if (!p) return
    get().stopPlayback()
    set({ scenario: p.scenario, presetId: id, plan: null, brief: null, selection: null, stageIndex: null, stale: false })
    if (p.response_strategy) await get().optimize(p.response_strategy)
    else await get().run()
  },

  toggleRoadClosure: (id) => {
    const closed = get().scenario.closed_road_ids
    const next = closed.includes(id) ? closed.filter((r) => r !== id) : [...closed, id]
    get().setScenario({ closed_road_ids: next })
    if (get().result) void get().run()
  },

  toggleListItem: (key, id) => {
    const cur = get().scenario[key]
    get().setScenario({ [key]: cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id] } as Partial<Scenario>)
  },

  run: async () => {
    runCtrl?.abort()
    const ctrl = (runCtrl = new AbortController())
    const seq = ++runSeq
    get().stopPlayback()
    set({ runStatus: 'running', runError: null })
    try {
      const scenario = get().scenario
      const result = await api.simulate(scenario, { signal: ctrl.signal })
      if (seq !== runSeq) return
      const mode: ViewMode = result.recovery ? 'recovery' : hasHazard(scenario) ? 'scenario' : 'baseline'
      set({ result, runStatus: 'idle', stale: false, mode, stageIndex: null, brief: null, briefStatus: 'idle' })
      if (hasHazard(scenario) && result.timeline.length) get().replay()
    } catch (e) {
      if (seq !== runSeq || (e instanceof ApiError && e.code === 'cancelled')) return
      set({ runStatus: 'idle', runError: errText(e) })
    }
  },

  optimize: async (strategy) => {
    const strat = strategy ?? get().strategy
    runCtrl?.abort()
    const ctrl = (runCtrl = new AbortController())
    const seq = ++runSeq
    get().stopPlayback()
    set({ optimizing: true, runStatus: 'running', runError: null, strategy: strat })
    try {
      const base = { ...get().scenario, deployed_resources: [] }
      const out: OptimizeResponse = await api.optimize(base, strat, { signal: ctrl.signal })
      if (seq !== runSeq) return
      set({ result: out.simulation, plan: out.plan, scenario: out.plan.scenario, optimizing: false, runStatus: 'idle', stale: false,
        mode: out.simulation.recovery ? 'recovery' : 'scenario', stageIndex: null, brief: null, briefStatus: 'idle',
        bottomOpen: true, bottomTab: 'response' })
      if (out.simulation.timeline.length) set({ stageIndex: out.simulation.timeline.length - 1 })
    } catch (e) {
      if (seq !== runSeq || (e instanceof ApiError && e.code === 'cancelled')) return
      set({ optimizing: false, runStatus: 'idle', runError: errText(e) })
    }
  },

  clearResponse: () => {
    get().setScenario({ deployed_resources: [], strategy: null }, { keepResponse: true })
    set({ plan: null })
    void get().run()
  },

  reset: async () => {
    get().stopPlayback()
    const base = get().dataset?.presets.find((p) => p.id === 'baseline')
    set({ scenario: base?.scenario ?? BASE_SCENARIO, presetId: 'baseline', plan: null, brief: null, briefStatus: 'idle', selection: null,
      stageIndex: null, notice: null, comparison: null })
    await get().run()
  },

  setMode: (mode) => { get().stopPlayback(); set({ mode, stageIndex: null }) },
  setStage: (i) => { get().stopPlayback(); set({ stageIndex: i }) },
  stepStage: (d) => {
    const n = get().result?.timeline.length ?? 0
    if (!n) return
    get().stopPlayback()
    const cur = get().stageIndex ?? (get().mode === 'baseline' ? 0 : n - 1)
    set({ stageIndex: Math.max(0, Math.min(n - 1, cur + d)) })
  },
  replay: () => {
    const n = get().result?.timeline.length ?? 0
    if (!n) return
    get().stopPlayback()
    const last = get().result?.recovery ? n - 1 : n - 2
    let i = 0
    set({ stageIndex: 0, playing: true })
    timer = setInterval(() => {
      i += 1
      if (i > last) { get().stopPlayback(); set({ stageIndex: null }); return }
      set({ stageIndex: i })
    }, 650)
  },
  stopPlayback: () => { if (timer) { clearInterval(timer); timer = null } if (get().playing) set({ playing: false }) },
  jumpToRecovery: () => {
    const r = get().result
    if (!r) return
    get().stopPlayback()
    set({ mode: r.recovery ? 'recovery' : 'scenario', stageIndex: r.timeline.length ? r.timeline.length - 1 : null })
  },
  resetToBaseline: () => { get().stopPlayback(); set({ mode: 'baseline', stageIndex: 0 }) },

  select: (selection) => set({ selection }),
  toggleLayer: (k) => set({ layers: { ...get().layers, [k]: !get().layers[k] } }),
  setBottom: (bottomOpen, tab) => set({ bottomOpen, ...(tab ? { bottomTab: tab } : {}) }),
  setStrategy: (strategy) => set({ strategy }),
  dismissNotice: () => set({ notice: null }),

  generateBrief: async () => {
    set({ briefStatus: 'loading', briefError: null })
    try {
      const brief = await api.brief(get().scenario)
      set({ brief, briefStatus: 'idle' })
    } catch (e) {
      set({ briefStatus: 'error', briefError: errText(e) })
    }
  },

  exportReport: async (fmt) => {
    try {
      const text = await api.exportReport(get().scenario, fmt)
      const types = { json: 'application/json', csv: 'text/csv', html: 'text/html' }
      download(`resilience-report.${fmt}`, text, types[fmt])
      set({ notice: { kind: 'info', text: `Exported resilience-report.${fmt}` } })
    } catch (e) {
      set({ notice: { kind: 'error', text: `Export failed: ${errText(e)}` } })
    }
  },

  exportScenario: () => {
    const s = { ...get().scenario, created_at: new Date().toISOString() }
    download(`scenario-${s.id}.json`, JSON.stringify(s, null, 2), 'application/json')
  },

  importScenario: (text) => {
    try {
      const parsed = parseScenario(JSON.parse(text))
      if (!parsed.ok) { set({ notice: { kind: 'error', text: `Invalid scenario file - ${parsed.message}` } }); return }
      get().stopPlayback()
      set({ scenario: parsed.scenario, presetId: 'custom', plan: null, brief: null, notice: { kind: 'info', text: 'Scenario imported. Running simulation.' } })
      void get().run()
    } catch {
      set({ notice: { kind: 'error', text: 'Invalid scenario file - not valid JSON' } })
    }
  },

  compareAll: async () => {
    const d = get().dataset
    if (!d) return
    set({ comparing: true })
    try {
      const comparison = await api.compare(d.presets.filter((p) => !p.response_strategy).map((p) => p.scenario))
      set({ comparison, comparing: false })
    } catch (e) {
      set({ comparing: false, notice: { kind: 'error', text: `Comparison failed: ${errText(e)}` } })
    }
  },
}))

