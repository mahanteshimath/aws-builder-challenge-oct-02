import { z } from 'zod'
import type { Scenario } from '@/types'

const id = z.string().min(1).max(64)
export const scenarioSchema = z.object({
  id: z.string().max(64).default('custom'),
  name: z.string().max(120).default('Custom scenario'),
  rainfall_mm: z.number().min(0).max(200),
  duration_hours: z.number().min(1).max(72),
  drainage_effectiveness: z.number().min(0).max(1),
  susceptibility_preset: z.enum(['low', 'moderate', 'high']).default('moderate'),
  closed_road_ids: z.array(id).max(60).default([]),
  affected_power_nodes: z.array(id).max(20).default([]),
  failed_drainage_ids: z.array(id).max(20).default([]),
  failed_facility_ids: z.array(id).max(40).default([]),
  resource_budget: z.number().min(0).max(1000),
  resource_availability: z.number().min(0).max(1).default(1),
  strategy: z.enum(['protect_critical', 'maximize_access', 'balanced']).nullable().default(null),
  deployed_resources: z.array(z.object({
    resource_id: id,
    resource_type: z.enum(['road_clearance_team', 'portable_generator', 'temporary_medical_unit', 'water_distribution_unit', 'temporary_shelter_kit']),
    target_id: id,
  })).max(40).default([]),
  thresholds: z.object({
    watch: z.number(), flood_risk: z.number(), impassable: z.number(),
    degraded_penalty: z.number(), restricted_penalty: z.number(), delay_ratio: z.number(),
  }),
  created_at: z.string().nullable().optional(),
  simulation_version: z.string().default('1.0.0'),
})

export function parseScenario(input: unknown): { ok: true; scenario: Scenario } | { ok: false; message: string } {
  const r = scenarioSchema.safeParse(input)
  if (!r.success) {
    const first = r.error.issues[0]
    return { ok: false, message: `${first.path.join('.') || 'scenario'}: ${first.message}` }
  }
  return { ok: true, scenario: r.data as Scenario }
}

export const rainfallSchema = z.number().min(0).max(200)
export const budgetSchema = z.number().min(0).max(1000)
