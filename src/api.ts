import type { FoodDetail, FoodsResponse } from './types'

const RATE_MSG = '每分钟只能使用五次，超出了五次，等下一分钟再开始'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (res.status === 429) {
    let msg = RATE_MSG
    try {
      const body = await res.json()
      msg = body.message || body.error || RATE_MSG
    } catch {
      /* use default */
    }
    throw new ApiError(msg, 429)
  }
  if (!res.ok) {
    throw new ApiError(`请求失败 (${res.status})`, res.status)
  }
  return res.json() as Promise<T>
}

export function searchFoods(q: string, offset = 0, limit = 24) {
  const params = new URLSearchParams({
    q,
    offset: String(offset),
    limit: String(limit),
  })
  return request<FoodsResponse>(`/api/foods?${params}`)
}

export function getFood(id: number) {
  return request<FoodDetail>(`/api/foods/${id}`)
}
