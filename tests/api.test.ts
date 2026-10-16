import assert from 'node:assert/strict'

let calls = 0
let mode: 'ok' | '429-once' | '429-always' = 'ok'
globalThis.fetch = (async () => {
  calls++
  if (mode === '429-always' || (mode === '429-once' && calls === 1)) {
    return new Response('{}', { status: 429, headers: { 'Retry-After': '0.01' } })
  }
  return new Response(JSON.stringify({ total: 1, items: [] }), { status: 200 })
}) as typeof fetch

const { searchFoods, ApiError } = await import('../src/api.ts')

// same keyword is served from cache
await searchFoods('apple', 0, 36)
await searchFoods('apple', 0, 36)
assert.equal(calls, 1)

// one automatic retry after 429
calls = 0; mode = '429-once'
let retried = false
await searchFoods('pear', 0, 36, { onRetry: () => { retried = true } })
assert.equal(calls, 2)
assert.ok(retried)

// gives up after the single retry with a Chinese message
calls = 0; mode = '429-always'
await assert.rejects(searchFoods('plum', 0, 36), (e: unknown) => e instanceof ApiError && e.status === 429 && /频繁/.test(e.message))
assert.equal(calls, 2)

// aborted requests reject with AbortError
mode = 'ok'
const c = new AbortController(); c.abort()
globalThis.fetch = (async (_u: unknown, init?: RequestInit) => {
  if (init?.signal?.aborted) throw new DOMException('Aborted', 'AbortError')
  return new Response('{}')
}) as typeof fetch
await assert.rejects(searchFoods('kiwi', 0, 36, { signal: c.signal }), { name: 'AbortError' })
console.log('api tests passed')
