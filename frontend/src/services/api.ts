import type { ApiErrorBody, Brief, CompareResponse, Dataset, OptimizeResponse, Scenario, SimulationResponse, Strategy } from '@/types'

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const PREFIX = '/api/v1'

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: { field: string; message: string }[]) {
    super(message)
  }
  get retryable() { return this.status === 0 || this.status >= 500 || this.status === 429 }
}

interface Opts { signal?: AbortSignal; timeoutMs?: number; retries?: number }

async function request<T>(path: string, init: RequestInit, { signal, timeoutMs = 30000, retries = 1 }: Opts = {}): Promise<T> {
  let lastErr: unknown
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort('timeout'), timeoutMs)
    const onAbort = () => ctrl.abort('cancelled')
    signal?.addEventListener('abort', onAbort)
    try {
      const res = await fetch(`${API_BASE}${PREFIX}${path}`, { ...init, signal: ctrl.signal, headers: { 'content-type': 'application/json', ...(init.headers ?? {}) } })
      const text = await res.text()
      if (!res.ok) {
        let body: ApiErrorBody | null = null
        try { body = JSON.parse(text) } catch { /* non-JSON error */ }
        throw new ApiError(res.status, body?.error?.code ?? 'http_error', body?.error?.message ?? `Request failed (${res.status})`, body?.error?.details)
      }
      return (init.headers as Record<string, string> | undefined)?.accept === 'text' ? (text as unknown as T) : (JSON.parse(text) as T)
    } catch (e) {
      if (signal?.aborted) throw new ApiError(0, 'cancelled', 'Request cancelled')
      lastErr = e instanceof ApiError ? e
        : ctrl.signal.aborted ? new ApiError(0, 'timeout', 'The request timed out. The server may be busy; please retry.')
        : new ApiError(0, 'network_error', 'Cannot reach the simulation API. Check your connection and retry.')
      if (!(lastErr as ApiError).retryable || attempt === retries) throw lastErr
      await new Promise((r) => setTimeout(r, 400 * (attempt + 1)))
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', onAbort)
    }
  }
  throw lastErr
}

const post = (body: unknown) => ({ method: 'POST', body: JSON.stringify(body) })

export const api = {
  health: (o?: Opts) => request<{ status: string; ai_provider: { bedrock_enabled: boolean; model_id: string | null } }>('/health', { method: 'GET' }, o),
  dataset: (o?: Opts) => request<Dataset>('/dataset', { method: 'GET' }, { timeoutMs: 40000, ...o }),
  simulate: (scenario: Scenario, o?: Opts) => request<SimulationResponse>('/simulate', post({ scenario, include_timeline: true }), o),
  optimize: (scenario: Scenario, strategy: Strategy, o?: Opts) => request<OptimizeResponse>('/optimize', post({ scenario, strategy }), { timeoutMs: 45000, ...o }),
  brief: (scenario: Scenario, o?: Opts) => request<Brief>('/brief', post({ scenario, brief_type: 'situation', allow_ai: true }), { timeoutMs: 40000, retries: 0, ...o }),
  compare: (scenarios: Scenario[], o?: Opts) => request<CompareResponse>('/scenario/compare', post({ scenarios }), o),
  exportReport: async (scenario: Scenario, format: 'json' | 'csv' | 'html', o?: Opts) =>
    request<string>('/export', { ...post({ scenario, format }), headers: { accept: 'text' } }, o),
}
