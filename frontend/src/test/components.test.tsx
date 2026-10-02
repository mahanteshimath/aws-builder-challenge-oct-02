import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import { makeDataset, makeResult } from '@/test/fixtures'
import { BASE_SCENARIO, useScenarioStore } from '@/store/scenarioStore'
import { ScenarioControls } from '@/components/layout/ScenarioControls'
import { CommandBar } from '@/components/layout/CommandBar'
import { MetricsPanel } from '@/components/layout/MetricsPanel'
import { SituationBrief } from '@/components/ai/SituationBrief'
import { ResponseStrategySelector } from '@/components/response/ResponseStrategySelector'
import { RecoverySummary } from '@/components/response/RecoverySummary'
import { ErrorState } from '@/components/shared/ErrorState'
import { ScenarioGallery } from '@/components/scenarios/ScenarioGallery'
import { FeatureInspector } from '@/components/map/FeatureInspector'
import { highlightFor } from '@/components/map/highlight'
import { parseScenario } from '@/utils/schema'
import { block } from '@/test/fixtures'

const wrap = (ui: React.ReactElement) => render(<TooltipProvider>{ui}</TooltipProvider>)
const run = vi.fn(async () => undefined)
const base = (over = {}) => useScenarioStore.setState({ dataset: makeDataset(), datasetStatus: 'ready', scenario: BASE_SCENARIO, presetId: 'baseline', result: makeResult(), mode: 'scenario', stageIndex: null,
  runStatus: 'idle', runError: null, stale: false, selection: null, brief: null, briefStatus: 'idle', plan: null, run, ...over } as never)

beforeEach(() => { vi.clearAllMocks(); base() })

describe('ScenarioControls', () => {
  it('rainfall numeric input updates the scenario and marks results stale', async () => {
    wrap(<ScenarioControls />)
    const input = screen.getByLabelText('Rainfall intensity')
    fireEvent.change(input, { target: { value: '135' } })
    expect(useScenarioStore.getState().scenario.rainfall_mm).toBe(135)
    expect(useScenarioStore.getState().stale).toBe(true)
    expect(screen.getByTestId('run-sim-left')).toHaveTextContent(/inputs changed/i)
  })

  it('rejects out-of-range rainfall with an accessible error and does not update state', () => {
    wrap(<ScenarioControls />)
    const input = screen.getByLabelText('Rainfall intensity')
    fireEvent.change(input, { target: { value: '450' } })
    expect(input).toHaveAttribute('aria-invalid', 'true'); expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(useScenarioStore.getState().scenario.rainfall_mm).toBe(0)
  })

  it('duration, susceptibility preset and power toggles write to state', async () => {
    const user = userEvent.setup()
    wrap(<ScenarioControls />)
    fireEvent.change(screen.getByLabelText('Time window'), { target: { value: '24' } })
    await user.click(screen.getByRole('radio', { name: 'high' }))
    await user.click(screen.getByRole('switch', { name: /Power outage at Riverside Substation/ }))
    const s = useScenarioStore.getState().scenario
    expect(s.duration_hours).toBe(24); expect(s.susceptibility_preset).toBe('high'); expect(s.affected_power_nodes).toEqual(['P-02'])
  })

  it('run button triggers the simulation', async () => {
    wrap(<ScenarioControls />)
    await userEvent.setup().click(screen.getByTestId('run-sim-left'))
    expect(run).toHaveBeenCalledTimes(1)
  })

  it('run button is disabled while a simulation is running (duplicate prevention)', () => {
    base({ runStatus: 'running' })
    wrap(<ScenarioControls />)
    expect(screen.getByTestId('run-sim-left')).toBeDisabled(); expect(screen.getByTestId('run-sim-left')).toHaveTextContent(/Simulating/)
  })

  it('budget field accepts valid values', () => {
    wrap(<ScenarioControls />)
    fireEvent.change(screen.getByLabelText('Response budget', { selector: 'input' }), { target: { value: '45' } })
    expect(useScenarioStore.getState().scenario.resource_budget).toBe(45)
  })
})

describe('ScenarioGallery', () => {
  it('selecting a preset marks it active and calls applyPreset', async () => {
    const applyPreset = vi.fn(async () => undefined); base({ applyPreset })
    wrap(<ScenarioGallery />)
    await userEvent.setup().click(screen.getByRole('radio', { name: /Extreme rainfall/ }))
    expect(applyPreset).toHaveBeenCalledWith('extreme_rain')
    expect(screen.getByRole('radio', { name: /Baseline neighborhood/ })).toHaveAttribute('aria-checked', 'true')
  })
})

describe('CommandBar', () => {
  it('shows status, sim time and runs the simulation', async () => {
    wrap(<CommandBar />)
    expect(screen.getByTestId('scenario-status')).toHaveTextContent(/Up to date/i)
    expect(screen.getByTestId('sim-time')).toHaveTextContent(/T\+60/)
    await userEvent.setup().click(screen.getByTestId('run-sim'))
    expect(run).toHaveBeenCalled()
  })

  it('recovery mode is disabled without a recovery result and enabled with one', async () => {
    const { unmount } = wrap(<CommandBar />)
    expect(screen.getByRole('radio', { name: 'Recovery' })).toBeDisabled(); unmount()
    base({ result: makeResult(true) }); wrap(<CommandBar />)
    expect(screen.getByRole('radio', { name: 'Recovery' })).toBeEnabled()
  })

  it('export menu offers report formats and calls exportReport', async () => {
    const exportReport = vi.fn(async () => undefined); base({ exportReport })
    const user = userEvent.setup(); wrap(<CommandBar />)
    await user.click(screen.getByTestId('export-menu'))
    await user.click(screen.getByRole('menuitem', { name: /CSV/ }))
    expect(exportReport).toHaveBeenCalledWith('csv')
  })

  it('reset button is wired', async () => {
    const reset = vi.fn(async () => undefined); base({ reset })
    wrap(<CommandBar />); await userEvent.setup().click(screen.getByTestId('reset-sim')); expect(reset).toHaveBeenCalled()
  })
})

describe('MetricsPanel', () => {
  it('renders modeled metrics with definitions and estimate labelling', () => {
    wrap(<MetricsPanel />)
    expect(screen.getByTestId('m-exposed')).toHaveTextContent('20,426')
    expect(screen.getByTestId('m-hospitals')).toHaveTextContent('3/4')
    expect(screen.getByLabelText('Definition: People potentially exposed')).toBeInTheDocument()
    expect(screen.getByText('estimates')).toBeInTheDocument()
  })

  it('shows an empty state before any result exists', () => {
    base({ result: null }); wrap(<MetricsPanel />)
    expect(screen.getByText(/No results yet/)).toBeInTheDocument()
  })

  it('shows recovery comparison callout in recovery mode', () => {
    base({ result: makeResult(true), mode: 'recovery' }); wrap(<MetricsPanel />)
    expect(screen.getByTestId('restored-callout')).toHaveTextContent('22,300')
    expect(screen.getByTestId('m-reduced-hospital')).toHaveTextContent('9,800')
  })
})

describe('Response strategy and recovery', () => {
  it('selecting a strategy updates the store', async () => {
    wrap(<ResponseStrategySelector />)
    await userEvent.setup().click(screen.getByRole('radio', { name: /Protect critical services/ }))
    expect(useScenarioStore.getState().strategy).toBe('protect_critical')
    expect(screen.getByRole('radio', { name: /Protect critical services/ })).toHaveAttribute('aria-checked', 'true')
  })

  it('recovery summary compares disaster vs recovery results', () => {
    base({ result: makeResult(true), mode: 'recovery' }); wrap(<RecoverySummary />)
    const el = screen.getByTestId('recovery-summary')
    expect(within(el).getByText('22,300')).toBeInTheDocument(); expect(el).toHaveTextContent(/re-running the simulation/)
    expect(el).toHaveTextContent('was 0 in disaster')
  })

  it('renders nothing when there is no recovery', () => {
    wrap(<RecoverySummary />); expect(screen.queryByTestId('recovery-summary')).toBeNull()
  })
})

describe('SituationBrief', () => {
  const sections = { situation_summary: 'Road R-019 is closed in this scenario.', top_impacts: ['a'], critical_bottlenecks: ['b'], services_requiring_attention: ['c'], immediate_actions: ['d'], followup_actions: ['e'], resource_tradeoffs: ['f'], uncertainties: ['g'] }
  it('labels Amazon Bedrock output', () => {
    base({ brief: { provider: 'bedrock', provider_label: 'Amazon Bedrock (AI-generated)', model_id: 'us.amazon.nova-lite-v1:0', sections, fallback_reason: null, simulation_version: '1.0.0', dataset_version: 't', synthetic_data: true, brief_type: 'situation' } })
    wrap(<SituationBrief />)
    expect(screen.getByTestId('brief-provider')).toHaveTextContent('Amazon Bedrock'); expect(screen.getByText(/Road R-019 is closed/)).toBeInTheDocument()
  })
  it('clearly labels the rule-based fallback and explains why', () => {
    base({ brief: { provider: 'rule_based', provider_label: 'Rule-based situation brief (deterministic; not AI-generated)', model_id: null, sections, fallback_reason: 'throttled', simulation_version: '1.0.0', dataset_version: 't', synthetic_data: true, brief_type: 'situation' } })
    wrap(<SituationBrief />)
    expect(screen.getByTestId('brief-provider')).toHaveTextContent('Rule-based (not AI)'); expect(screen.getByTestId('brief-provider')).toHaveTextContent(/throttled/)
  })
  it('generate button calls the store action and errors offer retry', async () => {
    const generateBrief = vi.fn(async () => undefined); base({ generateBrief })
    const { rerender } = wrap(<SituationBrief />)
    await userEvent.setup().click(screen.getByTestId('generate-brief')); expect(generateBrief).toHaveBeenCalledTimes(1)
    base({ generateBrief, briefStatus: 'error', briefError: 'timed out' }); rerender(<TooltipProvider><SituationBrief /></TooltipProvider>)
    await userEvent.setup().click(screen.getByRole('button', { name: /Retry/ })); expect(generateBrief).toHaveBeenCalledTimes(2)
  })
})

describe('shared states', () => {
  it('ErrorState shows message and retry action', async () => {
    const retry = vi.fn(); render(<ErrorState message="Cannot reach API" onRetry={retry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Cannot reach API'); await userEvent.setup().click(screen.getByRole('button', { name: /Retry/ })); expect(retry).toHaveBeenCalled()
  })
})

describe('FeatureInspector road closure interaction', () => {
  it('shows closure control for a selected road and toggles closure', async () => {
    const toggleRoadClosure = vi.fn(); const ds = makeDataset()
    ;(ds.layers.roads as unknown as { features: unknown[] }).features = [{ type: 'Feature', id: 'R-019', properties: { id: 'R-019', name: 'Bridge R-019' }, geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] } }]
    base({ dataset: ds, selection: { kind: 'road', id: 'R-019' }, toggleRoadClosure })
    wrap(<FeatureInspector />)
    expect(screen.getByText('Bridge R-019')).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: /Close this road/ }))
    expect(toggleRoadClosure).toHaveBeenCalledWith('R-019')
    await waitFor(() => expect(screen.getByText(/Critical bottleneck/)).toBeInTheDocument())
  })
})

describe('highlightFor', () => {
  it('highlights bottleneck road with affected facilities and zones', () => {
    const h = highlightFor({ kind: 'road', id: 'R-019' }, block(), block(), [{ road_id: 'R-019', affected_zone_ids: ['Z-01'], affected_facility_ids: ['H-02'] }])
    expect(h.roads).toEqual(['R-019']); expect(h.facilities).toEqual(['H-02']); expect(h.zones).toEqual(['Z-01'])
  })
  it('returns no highlight without selection', () => { expect(highlightFor(null, block(), block(), []).roads).toEqual([]) })
})

describe('scenario file validation', () => {
  it('accepts a valid scenario and rejects invalid shapes', () => {
    expect(parseScenario(BASE_SCENARIO).ok).toBe(true)
    expect(parseScenario({ ...BASE_SCENARIO, rainfall_mm: -5 }).ok).toBe(false)
    expect(parseScenario({ ...BASE_SCENARIO, deployed_resources: [{ resource_id: 'x', resource_type: 'bogus', target_id: 'y' }] }).ok).toBe(false)
    expect(parseScenario('nope').ok).toBe(false)
  })
})

