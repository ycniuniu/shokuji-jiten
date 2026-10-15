import type { VercelRequest, VercelResponse } from '@vercel/node'
import { RATE_LIMIT, RATE_MSG, RATE_WINDOW_MS } from './constants.js'

type Bucket = { count: number; resetAt: number }

/** Per-isolate memory store (best-effort on serverless). */
const buckets = new Map<string, Bucket>()

function clientKey(req: VercelRequest): string {
  const xf = req.headers['x-forwarded-for']
  const realIp = req.headers['x-real-ip']
  const fromXf = Array.isArray(xf) ? xf[0] : xf?.split(',')[0]?.trim()
  const fromReal = Array.isArray(realIp) ? realIp[0] : realIp
  return fromXf || fromReal || 'anonymous'
}

export function checkRateLimit(req: VercelRequest): { ok: true } | { ok: false; retryAfter: number } {
  const key = clientKey(req)
  const now = Date.now()
  let bucket = buckets.get(key)
  if (!bucket || now >= bucket.resetAt) {
    bucket = { count: 0, resetAt: now + RATE_WINDOW_MS }
    buckets.set(key, bucket)
  }
  bucket.count += 1
  if (bucket.count > RATE_LIMIT) {
    return { ok: false, retryAfter: Math.max(1, Math.ceil((bucket.resetAt - now) / 1000)) }
  }
  return { ok: true }
}

export function rejectRateLimit(res: VercelResponse, retryAfter: number) {
  res.setHeader('Retry-After', String(retryAfter))
  res.status(429).json({ error: RATE_MSG, message: RATE_MSG })
}

export function withRateLimit(
  req: VercelRequest,
  res: VercelResponse,
): boolean {
  const result = checkRateLimit(req)
  if (!result.ok) {
    rejectRateLimit(res, result.retryAfter)
    return false
  }
  return true
}
