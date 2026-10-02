import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import { makeDataset, makeResult } from '@/test/fixtures'

vi.mock('@/services/api', async (orig) => {
  const actual = await orig<typeof import('@/services/api')>()
  return { ...actual, api: { dataset: vi.fn(), simulate: vi.fn(), optimize: vi.fn(), brief: vi.fn(), compare: vi.fn(), exportReport: vi.fn(), health: vi.fn() } }
})
import { api } from '@/services/api'
import { BASE_SCENARIO, useScenarioStore } from '@/store/scenarioStore'

const m = api as unknown as Record<string, ReturnType<typeof vi.fn>>
const reset = () => useScenarioStore.setState({ dataset: makeDataset(), datasetStatus: 'ready', scenario: BASE_SCENARIO, presetId: 'baseline', result: makeResult(), plan: null, brief: null, mode: 'baseline', stageIndex: null, runError: null, runStatus: 'idle', notice: null, selection: null, stale: false })

beforeEach(() => { vi.clearAllMocks(); vi.useRealTimers(); reset() })

describe('scenario store', () => {
  it('loads dataset then runs baseline simulation', async () => {
    useScenarioStore.setState({ dataset: null, datasetStatus: 'idle', result: null })
    m.dataset.mockResolvedValue(makeDataset()); m.simulate.mockResolvedValue(makeResult())
    await useScenarioStore.getState().loadDataset()
    const s = useScenarioStore.getState()
    expect(s.datasetStatus).toBe('ready'); expect(m.simulate).toHaveBeenCalledTimes(1); expect(s.result).not.toBeNull(); expect(s.mode).toBe('baseline')
  })

  it('surfaces dataset load errors with retry possible', async () => {
    useScenarioStore.setState({ dataset: null, datasetStatus: 'idle' })
    m.dataset.mockRejectedValue(new ApiError(0, 'network_error', 'Cannot reach the simulation API.'))
    await useScenarioStore.getState().loadDataset()
    expect(useScenarioStore.getState().datasetStatus).toBe('error'); expect(useScenarioStore.getState().datasetError).toMatch(/Cannot reach/)
  })

  it('rainfall control updates scenario state immediately without calling the API', () => {
    useScenarioStore.getState().setScenario({ rainfall_mm: 120 })
    const s = useScenarioStore.getState()
    expect(s.scenario.rainfall_mm).toBe(120); expect(s.stale).toBe(true); expect(s.presetId).toBe('custom'); expect(m.simulate).not.toHaveBeenCalled()
  })

  it('selecting a scenario preset applies its settings and runs', async () => {
    m.simulate.mockResolvedValue(makeResult(false))
    await useScenarioStore.getState().applyPreset('extreme_rain')
    const s = useScenarioStore.getState()
    expect(s.scenario.rainfall_mm).toBe(160); expect(s.presetId).toBe('extreme_rain'); expect(m.simulate).toHaveBeenCalledWith(expect.objectContaining({ rainfall_mm: 160 }), expect.anything())
    expect(s.mode).toBe('scenario')
  })

  it('coordinated-response preset calls the optimizer and shows recovery', async () => {
    const res = makeResult(true)
    m.optimize.mockResolvedValue({ plan: { strategy: 'balanced', interventions: [], scenario: { ...BASE_SCENARIO, deployed_resources: [] } }, simulation: res })
    await useScenarioStore.getState().applyPreset('coordinated_response')
    expect(m.optimize).toHaveBeenCalledWith(expect.objectContaining({ deployed_resources: [] }), 'balanced', expect.anything())
    expect(useScenarioStore.getState().mode).toBe('recovery'); expect(useScenarioStore.getState().plan).not.toBeNull()
  })

  it('road closure toggles scenario state and re-simulates with the closed road', async () => {
    m.simulate.mockResolvedValue(makeResult())
    useScenarioStore.getState().toggleRoadClosure('R-019')
    expect(useScenarioStore.getState().scenario.closed_road_ids).toEqual(['R-019'])
    await vi.waitFor(() => expect(m.simulate).toHaveBeenCalled())
    expect(m.simulate.mock.calls[0][0].closed_road_ids).toEqual(['R-019'])
    useScenarioStore.getState().toggleRoadClosure('R-019')
    expect(useScenarioStore.getState().scenario.closed_road_ids).toEqual([])
  })

  it('changing hazard inputs discards a stale response plan', () => {
    useScenarioStore.setState({ scenario: { ...BASE_SCENARIO, deployed_resources: [{ resource_id: 'RES-GEN1', resource_type: 'portable_generator', target_id: 'H-03' }] }, plan: {} as never })
    useScenarioStore.getState().setScenario({ rainfall_mm: 90 })
    expect(useScenarioStore.getState().scenario.deployed_resources).toEqual([]); expect(useScenarioStore.getState().plan).toBeNull()
  })

  it('shows API errors and recovers on retry', async () => {
    m.simulate.mockRejectedValueOnce(new ApiError(500, 'internal_error', 'Unexpected server error'))
    await useScenarioStore.getState().run()
    expect(useScenarioStore.getState().runError).toMatch(/Unexpected server error/); expect(useScenarioStore.getState().runStatus).toBe('idle')
    m.simulate.mockResolvedValueOnce(makeResult())
    await useScenarioStore.getState().run()
    expect(useScenarioStore.getState().runError).toBeNull()
  })

  it('includes validation details from the API in the error text', async () => {
    m.simulate.mockRejectedValueOnce(new ApiError(422, 'validation_error', 'Request validation failed', [{ field: 'scenario.rainfall_mm', message: 'too large' }]))
    await useScenarioStore.getState().run()
    expect(useScenarioStore.getState().runError).toMatch(/rainfall_mm too large/)
  })

  it('ignores a superseded simulation response (duplicate request prevention)', async () => {
    let resolveFirst!: (v: unknown) => void
    m.simulate.mockImplementationOnce(() => new Promise((r) => { resolveFirst = r }))
    m.simulate.mockResolvedValueOnce(makeResult(false, { ...BASE_SCENARIO, name: 'second' }))
    const first = useScenarioStore.getState().run()
    await useScenarioStore.getState().run()
    resolveFirst(makeResult(false, { ...BASE_SCENARIO, name: 'first' }))
    await first
    expect(useScenarioStore.getState().result?.scenario.name).toBe('second')
  })

  it('optimizer selection stores plan, switches to recovery and uses the chosen strategy', async () => {
    m.optimize.mockResolvedValue({ plan: { strategy: 'protect_critical', interventions: [{}], scenario: BASE_SCENARIO }, simulation: makeResult(true) })
    await useScenarioStore.getState().optimize('protect_critical')
    const s = useScenarioStore.getState()
    expect(m.optimize.mock.calls[0][1]).toBe('protect_critical'); expect(s.strategy).toBe('protect_critical'); expect(s.mode).toBe('recovery'); expect(s.result?.recovery).not.toBeNull()
  })

  it('timeline stepping is bounded and reset returns to baseline', () => {
    useScenarioStore.setState({ result: makeResult(), mode: 'scenario', stageIndex: 5 })
    useScenarioStore.getState().stepStage(1); expect(useScenarioStore.getState().stageIndex).toBe(5)
    useScenarioStore.getState().stepStage(-1); expect(useScenarioStore.getState().stageIndex).toBe(4)
    useScenarioStore.getState().resetToBaseline(); expect(useScenarioStore.getState().mode).toBe('baseline'); expect(useScenarioStore.getState().stageIndex).toBe(0)
    useScenarioStore.getState().jumpToRecovery(); expect(useScenarioStore.getState().stageIndex).toBe(5)
  })

  it('brief: records provider indicator for Bedrock and fallback', async () => {
    const sections = { situation_summary: 's', top_impacts: [], critical_bottlenecks: [], services_requiring_attention: [], immediate_actions: [], followup_actions: [], resource_tradeoffs: [], uncertainties: [] }
    m.brief.mockResolvedValueOnce({ provider: 'bedrock', provider_label: 'Amazon Bedrock', model_id: 'x', sections, fallback_reason: null })
    await useScenarioStore.getState().generateBrief(); expect(useScenarioStore.getState().brief?.provider).toBe('bedrock')
    m.brief.mockResolvedValueOnce({ provider: 'rule_based', provider_label: 'Rule-based', model_id: null, sections, fallback_reason: 'disabled' })
    await useScenarioStore.getState().generateBrief(); expect(useScenarioStore.getState().brief?.provider).toBe('rule_based')
    m.brief.mockRejectedValueOnce(new ApiError(0, 'timeout', 'timed out'))
    await useScenarioStore.getState().generateBrief(); expect(useScenarioStore.getState().briefStatus).toBe('error')
  })

  it('export: calls the API and reports failures', async () => {
    const createUrl = vi.fn(() => 'blob:x'); Object.assign(URL, { createObjectURL: createUrl, revokeObjectURL: vi.fn() })
    m.exportReport.mockResolvedValueOnce('{"synthetic_data":true}')
    await useScenarioStore.getState().exportReport('json')
    expect(createUrl).toHaveBeenCalled(); expect(useScenarioStore.getState().notice?.kind).toBe('info')
    m.exportReport.mockRejectedValueOnce(new ApiError(500, 'internal_error', 'boom'))
    await useScenarioStore.getState().exportReport('csv')
    expect(useScenarioStore.getState().notice?.kind).toBe('error')
  })

  it('import: accepts a valid shareable scenario and rejects invalid files', async () => {
    m.simulate.mockResolvedValue(makeResult())
    useScenarioStore.getState().importScenario(JSON.stringify({ ...BASE_SCENARIO, rainfall_mm: 77 }))
    expect(useScenarioStore.getState().scenario.rainfall_mm).toBe(77)
    useScenarioStore.getState().importScenario(JSON.stringify({ ...BASE_SCENARIO, rainfall_mm: 999 }))
    expect(useScenarioStore.getState().notice?.kind).toBe('error'); expect(useScenarioStore.getState().scenario.rainfall_mm).toBe(77)
    useScenarioStore.getState().importScenario('not json')
    expect(useScenarioStore.getState().notice?.text).toMatch(/not valid JSON/)
  })
})
