import type { FoodDetail, FoodsResponse } from './types'

export const RATE_MSG = '请求有点频繁，正在稍后自动重试…'

export class ApiError extends Error {
  status: number
  retryAfter: number | null
  constructor(message: string, status: number, retryAfter: number | null = null) {
    super(message)
    this.status = status
    this.retryAfter = retryAfter
  }
}

const sleep = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const t = setTimeout(resolve, ms)
    signal?.addEventListener('abort', () => {
      clearTimeout(t)
      reject(new DOMException('Aborted', 'AbortError'))
    })
  })

/** One automatic retry after a 429, waiting for Retry-After (capped at 8 s). */
async function request<T>(url: string, signal?: AbortSignal, onRetry?: () => void): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    const res = await fetch(url, { signal })
    if (res.status === 429) {
      const ra = Number(res.headers.get('Retry-After'))
      const wait = Math.min(Number.isFinite(ra) && ra > 0 ? ra : 3, 8) * 1000
      if (attempt === 0) {
        onRetry?.()
        await sleep(wait, signal)
        continue
      }
      throw new ApiError('请求太频繁了，请过几秒再试一次。', 429, ra || null)
    }
    if (!res.ok) {
      throw new ApiError(`请求失败 (${res.status})`, res.status)
    }
    return res.json() as Promise<T>
  }
}

const searchCache = new Map<string, FoodsResponse>()
const SEARCH_CACHE_MAX = 100

export function cachedSearch(q: string, offset = 0, limit = 24): FoodsResponse | undefined {
  return searchCache.get(`${q}\u0000${offset}\u0000${limit}`)
}

export async function searchFoods(
  q: string,
  offset = 0,
  limit = 24,
  opts: { signal?: AbortSignal; onRetry?: () => void } = {},
) {
  const key = `${q}\u0000${offset}\u0000${limit}`
  const hit = searchCache.get(key)
  if (hit) return hit
  const params = new URLSearchParams({ q, offset: String(offset), limit: String(limit) })
  const data = await request<FoodsResponse>(`/api/foods?${params}`, opts.signal, opts.onRetry)
  if (searchCache.size >= SEARCH_CACHE_MAX) {
    const first = searchCache.keys().next().value
    if (first !== undefined) searchCache.delete(first)
  }
  searchCache.set(key, data)
  return data
}

const detailCache = new Map<number, FoodDetail>()

export async function getFood(id: number, onRetry?: () => void) {
  const hit = detailCache.get(id)
  if (hit) return hit
  const data = await request<FoodDetail>(`/api/foods/${id}`, undefined, onRetry)
  detailCache.set(id, data)
  return data
}
