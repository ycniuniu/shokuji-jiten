import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getFoodById } from '../_lib/db.js'
import { withRateLimit } from '../_lib/rateLimit.js'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }
  if (!withRateLimit(req, res)) return
  try {
    const id = Number(req.query.id)
    if (!Number.isFinite(id)) {
      res.status(400).json({ error: 'Invalid id' })
      return
    }
    const row = await getFoodById(id)
    if (!row) {
      res.status(404).json({ error: 'Not found' })
      return
    }
    res.status(200).json(row)
  } catch (err) {
    res.status(500).json({ error: String(err) })
  }
}
