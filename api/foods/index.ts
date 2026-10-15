import type { VercelRequest, VercelResponse } from '@vercel/node'
import { searchFoods } from '../_lib/db.js'
import { withRateLimit } from '../_lib/rateLimit.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }
  if (!withRateLimit(req, res)) return
  try {
    const q = String(req.query.q || '').trim()
    const limit = Math.min(Number(req.query.limit) || 24, 100)
    const offset = Math.max(Number(req.query.offset) || 0, 0)
    const data = await searchFoods(q, limit, offset)
    res.status(200).json(data)
  } catch (err) {
    res.status(500).json({ error: String(err) })
  }
}
