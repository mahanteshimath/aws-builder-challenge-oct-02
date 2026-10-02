import { useScenarioStore } from '@/store/scenarioStore'
import { blockFor, mapStateFor } from '@/utils/view'

export function useView() {
  const result = useScenarioStore((s) => s.result)
  const mode = useScenarioStore((s) => s.mode)
  const stageIndex = useScenarioStore((s) => s.stageIndex)
  const block = blockFor(result, mode)
  return { result, mode, stageIndex, block, baseline: result?.baseline ?? null, mapState: mapStateFor(result, mode, stageIndex),
    stage: stageIndex != null ? result?.timeline[stageIndex] ?? null : null }
}
