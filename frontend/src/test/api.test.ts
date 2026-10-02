import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from '@/services/api'

afterEach(() => vi.restoreAllMocks())
const ok = (body: unknown, status = 200) => Promise.resolve(new Response(typeof body === 'string' ? body : JSON.stringify(body), { status }))

describe('api client', () => {
  it('parses structured API errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok({ error: { code: 'validation_error', message: 'Request validation failed', details: [{ field: 'a', message: 'b' }] } }, 422))
    await expect(api.simulate({} as never)).rejects.toMatchObject({ status: 422, code: 'validation_error', details: [{ field: 'a', message: 'b' }] })
  })
  it('retries once on 5xx then succeeds', async () => {
    const f = vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() => ok({ error: { code: 'internal_error', message: 'x' } }, 500)).mockImplementationOnce(() => ok({ status: 'ok' }))
    await expect(api.health()).resolves.toMatchObject({ status: 'ok' }); expect(f).toHaveBeenCalledTimes(2)
  })
  it('does not retry client errors', async () => {
    const f = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok({ error: { code: 'x', message: 'bad' } }, 400))
    await expect(api.health()).rejects.toBeInstanceOf(ApiError); expect(f).toHaveBeenCalledTimes(1)
  })
  it('maps network failures to a friendly error', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('fail'))
    await expect(api.dataset()).rejects.toMatchObject({ code: 'network_error' })
  })
  it('times out slow requests', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((_u, init) => new Promise((_r, rej) => { init?.signal?.addEventListener('abort', () => rej(new DOMException('aborted', 'AbortError'))) }))
    await expect(api.simulate({} as never, { timeoutMs: 20, retries: 0 })).rejects.toMatchObject({ code: 'timeout' })
  })
  it('honours caller cancellation', async () => {
    const ctrl = new AbortController()
    vi.spyOn(globalThis, 'fetch').mockImplementation((_u, init) => new Promise((_r, rej) => { init?.signal?.addEventListener('abort', () => rej(new DOMException('aborted', 'AbortError'))) }))
    const p = api.simulate({} as never, { signal: ctrl.signal, timeoutMs: 5000, retries: 0 }); ctrl.abort()
    await expect(p).rejects.toMatchObject({ code: 'cancelled' })
  })
  it('returns raw text for exports', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok('a,b\n1,2', 200))
    await expect(api.exportReport({} as never, 'csv')).resolves.toBe('a,b\n1,2')
  })
})
