import type { VercelRequest, VercelResponse } from '@vercel/node'
import { getDb, rowsFrom } from './_lib/db'
import { withRateLimit } from './_lib/rateLimit'

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' })
    return
  }
  if (!withRateLimit(req, res)) return
  try {
    const db = await getDb()
    const byCountry = rowsFrom(
      db.exec(
        `SELECT source_country AS country, COUNT(*) AS count
         FROM foods GROUP BY source_country ORDER BY count DESC`,
      ),
    )
    res.status(200).json({ byCountry })
  } catch (err) {
    res.status(500).json({ error: String(err) })
  }
}
